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

/* --- FAB carrito (visible en todas las resoluciones) --- */
.carrito-fab{
  position:fixed;bottom:16px;right:16px;
  background:#f63366;color:#fff;
  padding:14px 20px;font-size:18px;font-weight:700;
  border-radius:32px;box-shadow:0 4px 12px rgba(0,0,0,.35);
  z-index:99999;cursor:pointer;transition:transform .15s;
  display:flex;align-items:center;justify-content:center;gap:8px;
}
.carrito-fab:hover{transform:scale(1.06);} 
/* quitamos la regla que ocultaba en desktop */

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
.sidebar-title{display:flex;align-items:center;gap:8px;margin-bottom:16px;font-size:20px;font-weight:700;}
.cart-item{padding:12px 0;border-bottom:1px solid #e0e0e0;color:#333;}
.cart-item:last-child{border-bottom:none;}
.cart-total{font-weight:700;font-size:18px;margin:16px 0;color:#f63366;}
.whatsapp-btn{background:#25D366!important;color:#fff!important;width:100%;margin:8px 0;}
.clear-btn{background:#f8f9fa!important;color:#f63366!important;
  border:1px solid #f63366!important;width:100%;margin:8px 0;}

/* --- Botón default de Streamlit para abrir/cerrar sidebar --- */
button[aria-label^="Toggle sidebar"],
button[title^="Expand sidebar"],
button[title^="Collapse sidebar"]{
  font-size:16px!important;
}
button[aria-label^="Toggle sidebar"]::after,
button[title^="Expand sidebar"]::after,
button[title^="Collapse sidebar"]::after{
  content:"  🛒 Carrito";
  font-weight:700;
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
#  UI: selector de línea + buscador
# ------------------------------------------------------------------ #
col_linea, col_search = st.columns([1, 2])
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
# Detectar si es móvil
st.markdown(
    """
<script>
const isMobile = window.matchMedia('(max-width: 768px)').matches;
window.parent.document.getElementById('is_mobile_detector').value = isMobile;
</script>
<input type="hidden" id="is_mobile_detector">
""",
    unsafe_allow_html=True,
)

# Items por página diferente en móvil
ITEMS_PER_PAGE = 10 if st.session_state.get("is_mobile_detector", False) else 45
total_pages = max(1, math.ceil(len(df) / ITEMS_PER_PAGE))
page_key = f"current_page_{linea}"
current_page = min(st.session_state.get(page_key, 1), total_pages)

def change_page(n: int):
    st.session_state[page_key] = n

def pager(position: str):
    # Versión móvil (flechas juntas)
    st.markdown(
        f"""
<div class="mobile-pager">
  <div class="pagination-mobile">
    <button onclick="window.dispatchEvent(new Event('prev_page_{position}'))" 
            {'disabled' if current_page == 1 else ''}>◀</button>
    <span style="padding:8px 12px;font-weight:bold;">Pág. {current_page}/{total_pages}</span>
    <button onclick="window.dispatchEvent(new Event('next_page_{position}'))" 
            {'disabled' if current_page == total_pages else ''}>▶</button>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    
    # Versión desktop (original)
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        st.button("◀", on_click=change_page, args=(current_page - 1,), 
                disabled=current_page == 1, key=f"{position}_prev")
    with col2:
        st.write(f"Página {current_page} de {total_pages}")
    with col3:
        st.button("▶", on_click=change_page, args=(current_page + 1,),
                disabled=current_page == total_pages, key=f"{position}_next")

# Manejar eventos de paginación móvil
st.markdown(
    """
<script>
// Manejar eventos de los botones móviles
document.addEventListener('prev_page_top', () => {
  const current = parseInt(window.parent.document.querySelector('[data-testid="stMarkdownContainer"]:has(> div > div > div > div > div > button[aria-label="◀"]) + div > div').textContent.split(' ')[1]);
  if(current > 1) {
    window.parent.document.querySelector('button[data-testid="baseButton-secondary"][aria-label="◀"]').click();
  }
});
document.addEventListener('next_page_top', () => {
  const current = parseInt(window.parent.document.querySelector('[data-testid="stMarkdownContainer"]:has(> div > div > div > div > div > button[aria-label="◀"]) + div > div').textContent.split(' ')[1]);
  const total = parseInt(window.parent.document.querySelector('[data-testid="stMarkdownContainer"]:has(> div > div > div > div > div > button[aria-label="◀"]) + div > div').textContent.split(' ')[3]);
  if(current < total) {
    window.parent.document.querySelector('button[data-testid="baseButton-secondary"][aria-label="▶"]').click();
  }
});
// Para el paginador inferior
document.addEventListener('prev_page_bottom', () => {
  const current = parseInt(window.parent.document.querySelectorAll('[data-testid="stMarkdownContainer"]:has(> div > div > div > div > div > button[aria-label="◀"]) + div > div')[1].textContent.split(' ')[1]);
  if(current > 1) {
    window.parent.document.querySelectorAll('button[data-testid="baseButton-secondary"][aria-label="◀"]')[1].click();
  }
});
document.addEventListener('next_page_bottom', () => {
  const current = parseInt(window.parent.document.querySelectorAll('[data-testid="stMarkdownContainer"]:has(> div > div > div > div > div > button[aria-label="◀"]) + div > div')[1].textContent.split(' ')[1]);
  const total = parseInt(window.parent.document.querySelectorAll('[data-testid="stMarkdownContainer"]:has(
