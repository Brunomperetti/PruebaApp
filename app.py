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

/* Botón "Ver carrito" al lado del desplegable */
#ver_carrito_btn {
    background-color: #f63366;
    color: white;
    border: none;
    padding: 8px 16px;
    font-weight: 700;
    border-radius: 8px;
    cursor: pointer;
    height: 38px;
    margin-left: 12px;
    align-self: center;
    transition: background-color 0.3s;
}
#ver_carrito_btn:hover {
    background-color: #d12b56;
}
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
#  UI: selector de línea + botón "Ver carrito"
# ------------------------------------------------------------------ #
col_linea, col_ver_carrito, col_search = st.columns([2, 1, 5])
with col_linea:
    linea = st.selectbox("Elegí la línea de productos:", list(FILE_IDS.keys()))

with col_ver_carrito:
    if st.button("Ver carrito", key="ver_carrito_btn"):
        st.sidebar.expander("Carrito").button("Cerrar carrito")  # Para forzar abrir sidebar
        # Si usás st.sidebar, lo podés abrir con el sidebar_state en set_page_config o controlar acá.

with col_search:
    buscar = st.text_input("Buscar en productos:")

# ------------------------------------------------------------------ #
#  Carga y filtrado productos
# ------------------------------------------------------------------ #
df = load_products(fetch_excel(FILE_IDS[linea]))

df_filtrado = df[
    (df["codigo_norm"].str.contains(quitar_acentos(buscar))) |
    (df["detalle_norm"].str.contains(quitar_acentos(buscar)))
]

# ------------------------------------------------------------------ #
#  Mostrar productos (simplificado)
# ------------------------------------------------------------------ #
for _, row in df_filtrado.iterrows():
    st.write(f"**{row['codigo']}** - {row['detalle']} - ${row['precio']}")

# ------------------------------------------------------------------ #
#  Sidebar: carrito (simplificado)
# ------------------------------------------------------------------ #
with st.sidebar:
    st.title("🛒 Carrito de compras")
    st.write("Aquí se mostrarán los productos agregados al carrito.")
    # Código para mostrar carrito real

# ------------------------------------------------------------------ #
#  FAB móvil (botón flotante) ya lo tenés definido en CSS y HTML
# ------------------------------------------------------------------ #
st.markdown(
    """
<div class="carrito-fab" onclick="window.scrollTo({top: 0, behavior: 'smooth'});">
  🛒 Carrito
</div>
""",
    unsafe_allow_html=True,
)


