import streamlit as st
import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
from PIL import Image
import io, urllib.parse, requests, tempfile, math, unicodedata

# ------------------------------------------------------------------ #
#  Configuración general
# ------------------------------------------------------------------ #
st.set_page_config(
    page_title="Catálogo Millex",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# ------------------------------------------------------------------ #
#  CSS global (oculta logos, estilos, FAB, botón cerrar carrito)
# ------------------------------------------------------------------ #
st.markdown(
    """
<style>
/* --- Ocultar menús / logos --- */
#MainMenu, footer, header {visibility: hidden;}
.viewerBadge_container__1QSob,
.viewerBadge_container__rGiy7,
a[href="https://streamlit.io"],
div[class^="viewerBadge_container"],
.stDeployButton {display:none!important;}

/* Ajuste top padding */
.block-container {padding-top:1rem;}

/* --- Nuevas reglas para móvil --- */
@media(max-width:768px){
  /* Paginación móvil - flechas juntas */
  .pagination-mobile{display:flex;justify-content:center;gap:16px;margin:20px 0;}
  .pagination-mobile button{background:#f0f2f6;border:none;border-radius:6px;
    padding:8px 16px;cursor:pointer;transition:.3s;font-size:18px;}
  .pagination-mobile button:hover{background:#e0e2e6;}
  .pagination-mobile button:disabled{opacity:.5;cursor:not-allowed;}
  
  /* Ocultar paginación normal en móvil */
  .pagination{display:none;}
  
  /* Mostrar paginación móvil */
  .mobile-pager{display:block!important;}
  
  /* Reducir productos por página en móvil */
  .mobile-items-per-page{display:block!important;}
}

/* Ocultar paginación móvil en desktop */
.mobile-pager{display:none;}
.mobile-items-per-page{display:none;}

/* --- FAB carrito (solo mobile) --- */
.carrito-fab{
  position:fixed;bottom:16px;right:16px;
  background:#f63366;color:#fff;
  padding:14px 20px;font-size:18px;font-weight:700;
  border-radius:32px;box-shadow:0 4px 12px rgba(0,0,0,.35);
  z-index:99999;cursor:pointer;transition:transform .15s;
  display:flex;align-items:center;justify-content:center;gap:8px;
}
.carrito-fab:hover{transform:scale(1.06);}
@media(min-width:769px){.carrito-fab{display:none;}}/* solo cel/tablet */

/* --- Productos --- */
.product-card{border:1px solid #e0e0e0;border-radius:12px;
  padding:16px;height:100%;transition:box-shadow .3s;
  display:flex;flex-direction:column;}
.product-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.1);}
.product-image{width:100%;height:180px;object-fit:contain;
  margin-bottom:12px;border-radius:8px;background:#f9f9f9;}
.product-title{font-size:16px;font-weight:600;margin-bottom:8px;color:#333;flex-grow:1;}
.product-code{font-size:14px;color:#666;margin-bottom:4px;}
.product-price{font-size:18px;font-weight:700;color:#f63366;margin-bottom:12px;}
.stNumberInput>div,.stNumberInput input{width:100%;}

/* --- Paginación --- */
.pagination{display:flex;justify-content:center;margin:20px 0;gap:8px;}
.pagination button{background:#f0f2f6;border:none;border-radius:6px;
  padding:8px 12px;cursor:pointer;transition:.3s;}
.pagination button:hover{background:#e0e2e6;}
.pagination button.active{background:#f63366;color:#fff;}
.pagination button:disabled{opacity:.5;cursor:not-allowed;}

/* --- Sidebar (carrito) --- */
[data-testid="stSidebar"]{background:#f8f9fa;padding:16px;position:relative;}
.sidebar-title{display:flex;align-items:center;gap:8px;margin-bottom:16px;}
.cart-item{padding:12px 0;border-bottom:1px solid #e0e0e0;color:#333;}
.cart-item:last-child{border-bottom:none;}
.cart-total{font-weight:700;font-size:18px;margin:16px 0;color:#f63366;}
.close-sidebar{position:absolute;top:10px;right:14px;font-size:22px;
  cursor:pointer;color:#666;user-select:none;}
.close-sidebar:hover{color:#000;}
.whatsapp-btn{background:#25D366!important;color:#fff!important;width:100%;margin:8px 0;}
.clear-btn{background:#f8f9fa!important;color:#f63366!important;
  border:1px solid #f63366!important;width:100%;margin:8px 0;}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ #
#  Utilidades
# ------------------------------------------------------------------ #
def quitar_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(texto))
        if not unicodedata.combining(c)
    ).lower()

# ------------------------------------------------------------------ #
#  Descarga del Excel (cacheado)
# ------------------------------------------------------------------ #
@st.cache_data(show_spinner=False)
def fetch_excel(file_id: str) -> Path:
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    tmp = Path(tempfile.gettempdir()) / f"{file_id}.xlsx"
    tmp.write_bytes(r.content)
    return tmp

# ------------------------------------------------------------------ #
#  Lectura de productos + imágenes (cacheado)
# ------------------------------------------------------------------ #
@st.cache_data(show_spinner=False)
def load_products(xls_path: str) -> pd.DataFrame:
    wb = load_workbook(xls_path, data_only=True)
    ws = wb.active
    img_map = {img.anchor._from.row + 1: img._data() for img in ws._images if hasattr(img, "_data")}
    rows = []
    for idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
        if not row[1]:   # columna B vacía => fin
            break
        codigo, detalle, precio = row[1], row[2], row[3]
        precio = 0 if precio is None else float(str(precio).replace("$", "").replace(",", ""))
        rows.append({"fila_excel": idx, "codigo": str(codigo), "detalle": str(detalle), "precio": precio})
    df = pd.DataFrame(rows)
    df["img_bytes"] = df["fila_excel"].map(img_map)
    # Columnas normalizadas para búsqueda
    df["codigo_norm"]  = df["codigo"].apply(quitar_acentos)
    df["detalle_norm"] = df["detalle"].apply(quitar_acentos)
    return df

# ------------------------------------------------------------------ #
#  IDs de hojas (líneas de productos)
# ------------------------------------------------------------------ #
FILE_IDS = {
    "Línea Perros": "1EK_NlWT-eS5_7P2kWwBHsui2tKu5t26U",
    "Línea Pájaros y Roedores": "1n10EZZvZq-3M2t3rrtmvW7gfeB40VJ7F",
    "Línea Gatos": "1vSWXZKsIOqpy2wNhWsKH3Lp77JnRNKbA",
    "Línea Bombas de Acuario": "1DiXE5InuxMjZio6HD1nkwtQZe8vaGcSh",
}

# ------------------------------------------------------------------ #
#  UI: selector de línea + buscador + botón carrito desplegable
# ------------------------------------------------------------------ #
col_carrito, col_linea, col_search = st.columns([1, 1.5, 2.5])

with col_carrito:
    # Botón para abrir/cerrar el sidebar como carrito
    if st.button("🛒 Ver carrito"):
        st.session_state.sidebar_state = "expanded" if st.session_state.get("sidebar_state", "collapsed") == "collapsed" else "collapsed"
        st.experimental_rerun()

with col_linea:
    linea = st.selectbox("Elegí la línea de productos:", list(FILE_IDS.keys()))

with col_search:
    search_term = st.text_input("🔍 Buscar (código o descripción)…").strip().lower()
search_norm = quitar_acentos(search_term)

# ------------------------------------------------------------------ #
#  Carga y filtrado del catálogo
# ------------------------------------------------------------------ #
df_base = load_products(str(fetch_excel(FILE_IDS[linea])))

if search_term:
    df = df_base[
        df_base["codigo_norm"].str.contains(search_norm, na=False)
        | df_base["detalle_norm"].str.contains(search_norm, na=False)
    ]
else:
    df = df_base.copy()

# ------------------------------------------------------------------ #
#  Paginación
# ------------------------------------------------------------------ #
# Configuración
items_per_page = 20
total_items = len(df)
total_pages = math.ceil(total_items / items_per_page)
if "page" not in st.session_state:
    st.session_state.page = 1

# Navegación página
def set_page(p):
    st.session_state.page = max(1, min(total_pages, p))

col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 3])
with col1:
    if st.button("⏮ Primero"):
        set_page(1)
        st.experimental_rerun()
with col2:
    if st.button("◀ Anterior"):
        set_page(st.session_state.page - 1)
        st.experimental_rerun()
with col3:
    st.markdown(f"Página **{st.session_state.page}** de **{total_pages}**")
with col4:
    if st.button("Siguiente ▶"):
        set_page(st.session_state.page + 1)
        st.experimental_rerun()
with col5:
    if st.button("Último ⏭"):
        set_page(total_pages)
        st.experimental_rerun()

start_idx = (st.session_state.page - 1) * items_per_page
end_idx = start_idx + items_per_page
df_page = df.iloc[start_idx:end_idx]

# ------------------------------------------------------------------ #
#  Mostrar productos paginados en grilla
# ------------------------------------------------------------------ #
cols = st.columns(4)
for idx, (_, prod) in enumerate(df_page.iterrows()):
    with cols[idx % 4]:
        # Mostrar imagen si existe
        if prod.img_bytes:
            img = Image.open(io.BytesIO(prod.img_bytes))
            st.image(img, use_column_width=True)
        else:
            st.image("https://via.placeholder.com/200x180?text=Sin+imagen", use_column_width=True)
        st.markdown(f"**{prod.codigo}**")
        st.markdown(prod.detalle)
        st.markdown(f"**${prod.precio:,.0f}**")

# ------------------------------------------------------------------ #
#  Sidebar carrito (vacío por ahora)
# ------------------------------------------------------------------ #
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-title">
            <h3>🛒 Carrito de compras</h3>
            <span class="close-sidebar" onclick="window.parent.postMessage({type:'st:toggleSidebar'}, '*')">&times;</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("Tu carrito está vacío.")
    # Aquí luego se puede agregar lógica para mostrar productos agregados al carrito

# ------------------------------------------------------------------ #
#  Fab carrito (solo para móvil)
# ------------------------------------------------------------------ #
st.markdown(
    """
    <div class="carrito-fab" onclick="window.parent.postMessage({type:'st:toggleSidebar'}, '*')">
        🛒 Ver carrito
    </div>
    """,
    unsafe_allow_html=True,
)

