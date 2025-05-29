import streamlit as st
import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
from PIL import Image
import io, urllib.parse, requests, tempfile, math, unicodedata

# -------------------- Configuración general --------------------
st.set_page_config(
    page_title="Catálogo Millex",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# -------------------- CSS global --------------------
st.markdown("""
<style>
/* Ocultar menús / logos */
#MainMenu, footer, header {visibility: hidden;}
.viewerBadge_container__1QSob,
.viewerBadge_container__rGiy7,
a[href="https://streamlit.io"],
div[class^="viewerBadge_container"],
.stDeployButton {display:none!important;}

/* Ajuste top padding */
.block-container {padding-top:1rem;}

/* Aumentar tamaño de la flecha del selectbox */
div[data-baseweb="select"] svg {
    width: 2rem;
    height: 2rem;
}
div[data-baseweb="select"] > div {
    font-size: 1.1rem;
}

/* Reglas para móvil (paginación) */
@media(max-width:768px){
  .pagination-mobile{display:flex;justify-content:center;gap:16px;margin:20px 0;}
  .pagination-mobile button{background:#f0f2f6;border:none;border-radius:6px;
    padding:8px 16px;cursor:pointer;transition:.3s;font-size:18px;}
  .pagination-mobile button:hover{background:#e0e2e6;}
  .pagination-mobile button:disabled{opacity:.5;cursor:not-allowed;}
  .pagination{display:none;}
  .mobile-pager{display:block!important;}
}
</style>
""", unsafe_allow_html=True)

# -------------------- Utilidades --------------------
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

# -------------------- IDs de hojas --------------------
FILE_IDS = {
    "Línea Perros": "1EK_NlWT-eS5_7P2kWwBHsui2tKu5t26U",
    "Línea Pájaros y Roedores": "1n10EZZvZq-3M2t3rrtmvW7gfeB40VJ7F",
    "Línea Gatos": "1vSWXZKsIOqpy2wNhWsKH3Lp77JnRNKbA",
    "Línea Bombas de Acuario": "1DiXE5InuxMjZio6HD1nkwtQZe8vaGcSh",
}

# -------------------- Barra superior: selector + “Ver carrito” + buscador --------------------
col_linea, col_carrito, col_search = st.columns([2.2, 1.4, 3])

with col_linea:
    linea = st.selectbox(
        "Elegí la línea de productos:",
        list(FILE_IDS.keys()),
        label_visibility="collapsed",
        placeholder="Elegí la línea de productos:"
    )

with col_carrito:
    if st.button("🛒 Ver carrito", key="btn_carrito", use_container_width=True):
        st.info("Aquí mostrarías el contenido del carrito 😉")

with col_search:
    search_term = st.text_input(
        "🔍 Buscar (código o descripción)…",
        placeholder="🔍 Buscar (código o descripción)…",
        label_visibility="collapsed"
    ).strip().lower()

search_norm = quitar_acentos(search_term)

# -------------------- Carga y filtrado --------------------
df_base = load_products(str(fetch_excel(FILE_IDS[linea])))

if search_term:
    df = df_base[
        df_base["codigo_norm"].str.contains(search_norm, na=False)
        | df_base["detalle_norm"].str.contains(search_norm, na=False)
    ]
else:
    df = df_base.copy()

# -------------------- Paginación --------------------
ITEMS_PER_PAGE = 45
total_pages = max(1, math.ceil(len(df) / ITEMS_PER_PAGE))
page_key = f"current_page_{linea}_{search_term}"
if page_key not in st.session_state:
    st.session_state[page_key] = 1
current_page = min(st.session_state.get(page_key, 1), total_pages)

def change_page(new_page_val: int):
    st.session_state[page_key] = new_page_val

def pager(position: str):
    cols_pager = st.columns([1, 1, 1])
    with cols_pager[0]:
        if st.button("◀ Anterior", key=f"{position}_prev", disabled=current_page == 1):
            change_page(current_page - 1)
            st.rerun()
    with cols_pager[1]:
        st.markdown(f"<div style='text-align:center;'>Página {current_page} de {total_pages}</div>", unsafe_allow_html=True)
    with cols_pager[2]:
        if st.button("Siguiente ▶", key=f"{position}_next", disabled=current_page == total_pages):
            change_page(current_page + 1)
            st.rerun()

if total_pages > 1:
    pager("top")

# -------------------- Productos --------------------
start_idx = (current_page - 1) * ITEMS_PER_PAGE
end_idx = current_page * ITEMS_PER_PAGE
paginated_df = df.iloc[start_idx:end_idx]

if paginated_df.empty and len(df) > 0:
    st.session_state[page_key] = 1
    st.rerun()
elif paginated_df.empty and search_term:
    st.info("No se encontraron productos que coincidan con tu búsqueda.")
elif paginated_df.empty:
    st.info("No hay productos para mostrar en esta línea.")

for i in range(0, len(paginated_df), 3):
    cols = st.columns(3)
    for j in range(3):
        if i + j >= len(paginated_df):
            continue
        prod = paginated_df.iloc[i + j]
        with cols[j]:
            # Mostrá la imagen si la hay
            if pd.notna(prod["img_bytes"]):
                try:
                    st.image(Image.open(io.BytesIO(prod["img_bytes"])), use_container_width=True)
                except Exception:
                    st.image("https://via.placeholder.com/200x150?text=Imagen%20no%20disponible", use_container_width=True)
            else:
                st.image("https://via.placeholder.com/200x150?text=Sin%20imagen", use_container_width=True)

            st.markdown(f"**{prod['detalle']}**  \nCódigo: {prod['codigo']}  \nPrecio: ${prod['precio']:.2f}")

