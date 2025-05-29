import streamlit as st
import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
from PIL import Image
import io, requests, tempfile, math, unicodedata

# Configuración general
st.set_page_config(
    page_title="Catálogo Millex",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# CSS para botón carrito
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.carrito-top-right {
    position: fixed;
    top: 10px;
    right: 10px;
    background: #f63366;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 8px 12px;
    font-size: 1rem;
    font-weight: bold;
    cursor: pointer;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
}
</style>
""", unsafe_allow_html=True)

# Función para quitar acentos
def quitar_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(texto))
        if not unicodedata.combining(c)
    ).lower()

# Descargar Excel (cache)
@st.cache_data(show_spinner=False)
def fetch_excel(file_id: str) -> Path:
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    tmp = Path(tempfile.gettempdir()) / f"{file_id}.xlsx"
    tmp.write_bytes(r.content)
    return tmp

# Leer productos e imágenes (cache)
@st.cache_data(show_spinner=False)
def load_products(xls_path: str) -> pd.DataFrame:
    wb = load_workbook(xls_path, data_only=True)
    ws = wb.active
    # Mapeo fila -> imagen en bytes
    img_map = {}
    for img in ws._images:
        if hasattr(img, "_data"):
            row = img.anchor._from.row + 1  # +1 porque openpyxl es 0-index
            img_map[row] = img._data()
    rows = []
    for idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
        if not row[1]:
            break
        codigo, detalle, precio = row[1], row[2], row[3]
        precio = 0 if precio is None else float(str(precio).replace("$", "").replace(",", ""))
        rows.append({"fila_excel": idx, "codigo": str(codigo), "detalle": str(detalle), "precio": precio})
    df = pd.DataFrame(rows)
    df["img_bytes"] = df["fila_excel"].map(img_map)
    df["codigo_norm"] = df["codigo"].apply(quitar_acentos)
    df["detalle_norm"] = df["detalle"].apply(quitar_acentos)
    return df

# IDs hojas
FILE_IDS = {
    "Línea Perros": "1EK_NlWT-eS5_7P2kWwBHsui2tKu5t26U",
    "Línea Pájaros y Roedores": "1n10EZZvZq-3M2t3rrtmvW7gfeB40VJ7F",
    "Línea Gatos": "1vSWXZKsIOqpy2wNhWsKH3Lp77JnRNKbA",
    "Línea Bombas de Acuario": "1DiXE5InuxMjZio6HD1nkwtQZe8vaGcSh",
}

# Selector línea + búsqueda
col_linea, col_search = st.columns([2.2, 3])
with col_linea:
    linea = st.selectbox("Elegí la línea de productos:", list(FILE_IDS.keys()), label_visibility="collapsed")
with col_search:
    search_term = st.text_input("🔍 Buscar (código o descripción)…", label_visibility="collapsed").strip().lower()

search_norm = quitar_acentos(search_term)

# Cargar catálogo
df_base = load_products(str(fetch_excel(FILE_IDS[linea])))

if search_term:
    df = df_base[
        df_base["codigo_norm"].str.contains(search_norm, na=False) |
        df_base["detalle_norm"].str.contains(search_norm, na=False)
    ]
else:
    df = df_base.copy()

# Paginación
ITEMS_PER_PAGE = 45
total_pages = max(1, math.ceil(len(df) / ITEMS_PER_PAGE))
page_key = f"current_page_{linea}_{search_term}"
if page_key not in st.session_state:
    st.session_state[page_key] = 1
current_page = min(st.session_state[page_key], total_pages)

def change_page(new_page):
    st.session_state[page_key] = new_page

# Mostrar productos paginados
start_idx = (current_page - 1) * ITEMS_PER_PAGE
end_idx = current_page * ITEMS_PER_PAGE
paginated_df = df.iloc[start_idx:end_idx]

if paginated_df.empty and len(df) > 0:
    st.session_state[page_key] = 1
    st.experimental_rerun()
elif paginated_df.empty and search_term:
    st.info("No se encontraron productos que coincidan con tu búsqueda.")
elif paginated_df.empty:
    st.info("No hay productos para mostrar en esta línea.")

for i in range(0, len(paginated_df), 3):
    cols = st.columns(3)
    for j in range(3):
        idx = i + j
        if idx >= len(paginated_df):
            with cols[j]:
                st.empty()
            continue
        prod = paginated_df.iloc[idx]
        with cols[j]:
            if pd.notna(prod.img_bytes) and len(prod.img_bytes) > 0:
                try:
                    img = Image.open(io.BytesIO(prod.img_bytes))
                    st.image(img, use_container_width=True)
                except Exception:
                    st.image("https://via.placeholder.com/200x150?text=Sin+imagen", use_container_width=True)
            else:
                st.image("https://via.placeholder.com/200x150?text=Sin+imagen", use_container_width=True)

            st.markdown(f"**{prod.detalle}**")
            st.markdown(f"Código: {prod.codigo}")
            st.markdown(f"Precio: ${prod.precio:,.2f}")

            qty_key = f"qty_{linea}_{prod.codigo}"
            cart = st.session_state.setdefault("cart", {})
            current_qty = cart.get(prod.codigo, {}).get("qty", 0)

            qty = st.number_input("Cantidad", min_value=0, step=1, key=qty_key, value=current_qty)

            if qty != current_qty:
                if qty > 0:
                    cart[prod.codigo] = {"detalle": prod.detalle, "precio": prod.precio, "qty": qty, "linea": linea}
                elif prod.codigo in cart:
                    del cart[prod.codigo]
                st.experimental_rerun()

# Botón carrito (fixed top-right)
qty_total = sum(item["qty"] for item in st.session_state.get("cart", {}).values())
fab_label = f"🛒 Carrito ({qty_total})" if qty_total else "🛒 Carrito"

if "show_cart" not in st.session_state:
    st.session_state["show_cart"] = False

if st.button(fab_label, key="toggle_cart"):
    st.session_state["show_cart"] = not st.session_state["show_cart"]

# Sidebar carrito
if st.session_state["show_cart"]:
    with st.sidebar:
        st.header("🛒 Carrito")
        cart = st.session_state.get("cart", {})
        if not cart:
            st.info("El carrito está vacío.")
        else:
            total = 0
            for cod, item in cart.items():
                st.markdown(f"**{item['detalle']}**")
                st.markdown(f"Código: {cod}")
                st.markdown(f"Cantidad: {item['qty']}")
                st.markdown(f"Subtotal: ${item['precio']*item['qty']:,.2f}")
                st.markdown("---")
                total += item['precio'] * item['qty']
            st.markdown(f"### Total: ${total:,.2f}")

