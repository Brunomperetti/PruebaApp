import streamlit as st
import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
from PIL import Image
import io, unicodedata, tempfile, requests, math

# Configuración general
st.set_page_config(
    page_title="Catálogo Millex",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# CSS para ocultar menús y estilos botón carrito
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

def quitar_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(texto))
        if not unicodedata.combining(c)
    ).lower()

@st.cache_data(show_spinner=False)
def fetch_excel(file_id: str) -> Path:
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    tmp = Path(tempfile.gettempdir()) / f"{file_id}.xlsx"
    tmp.write_bytes(r.content)
    return tmp

@st.cache_data(show_spinner=False)
def load_products(xls_path: str) -> pd.DataFrame:
    wb = load_workbook(xls_path, data_only=True)
    ws = wb.active
    img_map = {img.anchor._from.row + 1: img._data() for img in ws._images if hasattr(img, "_data")}
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

FILE_IDS = {
    "Línea Perros": "1EK_NlWT-eS5_7P2kWwBHsui2tKu5t26U",
    "Línea Pájaros y Roedores": "1n10EZZvZq-3M2t3rrtmvW7gfeB40VJ7F",
    "Línea Gatos": "1vSWXZKsIOqpy2wNhWsKH3Lp77JnRNKbA",
    "Línea Bombas de Acuario": "1DiXE5InuxMjZio6HD1nkwtQZe8vaGcSh",
}

col_linea, col_search = st.columns([2.2, 3])
with col_linea:
    linea = st.selectbox("Elegí la línea de productos:", list(FILE_IDS.keys()), label_visibility="collapsed", placeholder="Elegí la línea de productos:")
with col_search:
    search_term = st.text_input("🔍 Buscar (código o descripción)…", placeholder="🔍 Buscar (código o descripción)…", label_visibility="collapsed").strip().lower()
search_norm = quitar_acentos(search_term)

df_base = load_products(str(fetch_excel(FILE_IDS[linea])))

if search_term:
    df = df_base[
        df_base["codigo_norm"].str.contains(search_norm, na=False)
        | df_base["detalle_norm"].str.contains(search_norm, na=False)
    ]
else:
    df = df_base.copy()

ITEMS_PER_PAGE = 45
total_pages = max(1, math.ceil(len(df) / ITEMS_PER_PAGE))
page_key = f"current_page_{linea}_{search_term}"
if page_key not in st.session_state:
    st.session_state[page_key] = 1
current_page = min(st.session_state.get(page_key, 1), total_pages)

def change_page(new_page_val: int):
    st.session_state[page_key] = new_page_val

# Paginación simple con botones Streamlit (sin JS)
cols_pager = st.columns([1, 1, 1])
with cols_pager[0]:
    if st.button("◀ Anterior", key="prev_page", disabled=current_page == 1):
        change_page(current_page - 1)
        st.experimental_rerun()
with cols_pager[1]:
    st.markdown(f"<center>Página {current_page} de {total_pages}</center>", unsafe_allow_html=True)
with cols_pager[2]:
    if st.button("Siguiente ▶", key="next_page", disabled=current_page == total_pages):
        change_page(current_page + 1)
        st.experimental_rerun()

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
        if i + j >= len(paginated_df):
            with cols[j]:
                st.container()
            continue
        prod = paginated_df.iloc[i + j]
        with cols[j]:
            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            if pd.notna(prod.img_bytes) and len(prod.img_bytes) > 0:
                try:
                    st.image(Image.open(io.BytesIO(prod.img_bytes)), use_container_width=True, output_format='PNG')
                except Exception:
                    st.image("https://via.placeholder.com/200x150?text=Error+Img", use_container_width=True)
            else:
                st.image("https://via.placeholder.com/200x150?text=Sin+imagen", use_container_width=True)

            st.markdown(f'<div class="product-title">{prod.detalle}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="product-code">Código: {prod.codigo}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="product-price">${prod.precio:,.2f}</div>', unsafe_allow_html=True)

            qty_key = f"qty_{linea}_{prod.codigo}"
            cart = st.session_state.setdefault("cart", {})
            current_qty_in_cart = cart.get(str(prod.codigo), {}).get("qty", 0)

            qty = st.number_input("Cantidad", min_value=0, step=1,
                                  key=qty_key,
                                  value=current_qty_in_cart)

            if qty != current_qty_in_cart:
                if qty > 0:
                    cart[str(prod.codigo)] = {"detalle": prod.detalle, "precio": prod.precio, "qty": qty, "linea": linea}
                elif str(prod.codigo) in cart:
                    del cart[str(prod.codigo)]
                st.experimental_rerun()

            st.markdown("</div>", unsafe_allow_html=True)

# Botón carrito (streamlit button que controla mostrar sidebar)
if "show_cart" not in st.session_state:
    st.session_state["show_cart"] = False

def toggle_cart():
    st.session_state["show_cart"] = not st.session_state["show_cart"]

qty_total_fab = sum(it["qty"] for it in st.session_state.get("cart", {}).values())

st.markdown(f'''
<button class="carrito-top-right" onclick="window.parent.postMessage({{func:'streamlit:setComponentValue', args: ['toggle_cart'] }}, '*')">
    🛒 {qty_total_fab}
</button>
''', unsafe_allow_html=True)

if st.session_state["show_cart"]:
    with st.sidebar:
        st.title("🛒 Carrito de Compras")
        if not st.session_state.get("cart"):
            st.info("Tu carrito está vacío.")
        else:
            total = 0
            for code, item in st.session_state["cart"].items():
                st.write(f"{item['detalle']} x {item['qty']} — ${item['precio']*item['qty']:.2f}")
                total += item['precio'] * item['qty']
            st.markdown(f"### Total: ${total:,.2f}")

        if st.button("Vaciar carrito"):
            st.session_state["cart"] = {}
            st.experimental_rerun()

