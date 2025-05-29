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
#  CSS global
# ------------------------------------------------------------------ #
st.markdown(
    """
<style>
#MainMenu, footer, header {visibility: hidden;}
.viewerBadge_container__1QSob,
.viewerBadge_container__rGiy7,
a[href="https://streamlit.io"],
div[class^="viewerBadge_container"],
.stDeployButton {display:none!important;}

.block-container {padding-top:1rem;}

@media(max-width:768px){
  .pagination-mobile{display:flex;justify-content:center;gap:16px;margin:20px 0;}
  .pagination-mobile button{background:#f0f2f6;border:none;border-radius:6px;
    padding:8px 16px;cursor:pointer;transition:.3s;font-size:18px;}
  .pagination-mobile button:hover{background:#e0e2e6;}
  .pagination-mobile button:disabled{opacity:.5;cursor:not-allowed;}
  .pagination{display:none;}
  .mobile-pager{display:block!important;}
  .mobile-items-per-page{display:block!important;}
}
.mobile-pager{display:none;}
.mobile-items-per-page{display:none;}

.carrito-fab{
  position:fixed;bottom:16px;right:16px;
  background:#f63366;color:#fff;
  padding:14px 20px;font-size:18px;font-weight:700;
  border-radius:32px;box-shadow:0 4px 12px rgba(0,0,0,.35);
  z-index:99999;cursor:pointer;transition:transform .15s;
  display:flex;align-items:center;justify-content:center;gap:8px;
}
.carrito-fab:hover{transform:scale(1.06);} 

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

.pagination{display:flex;justify-content:center;margin:20px 0;gap:8px;}
.pagination button{background:#f0f2f6;border:none;border-radius:6px;
  padding:8px 12px;cursor:pointer;transition:.3s;}
.pagination button:hover{background:#e0e2e6;}
.pagination button.active{background:#f63366;color:#fff;}
.pagination button:disabled{opacity:.5;cursor:not-allowed;}

[data-testid="stSidebar"]{background:#f8f9fa;padding:16px;position:relative;}
.sidebar-title{display:flex;align-items:center;gap:8px;margin-bottom:16px;font-size:20px;font-weight:700;}
.cart-item{padding:12px 0;border-bottom:1px solid #e0e0e0;color:#333;}
.cart-item:last-child{border-bottom:none;}
.cart-total{font-weight:700;font-size:18px;margin:16px 0;color:#f63366;}
.whatsapp-btn{background:#25D366!important;color:#fff!important;width:100%;margin:8px 0;}
.clear-btn{background:#f8f9fa!important;color:#f63366!important;
  border:1px solid #f63366!important;width:100%;margin:8px 0;}

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

# Carrito (dict con código y cantidad)
if "carrito" not in st.session_state:
    st.session_state["carrito"] = {}

def agregar_al_carrito(codigo):
    carrito = st.session_state["carrito"]
    carrito[codigo] = carrito.get(codigo, 0) + 1
    st.session_state["carrito"] = carrito

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
        if not row[1]: break
        codigo, detalle, precio = row[1], row[2], row[3]
        precio = 0 if precio is None else float(str(precio).replace("$", "").replace(",", ""))
        rows.append({"fila_excel": idx, "codigo": str(codigo), "detalle": str(detalle), "precio": precio})
    df = pd.DataFrame(rows)
    df["img_bytes"] = df["fila_excel"].map(img_map)
    df["codigo_norm"] = df["codigo"].apply(quitar_acentos)
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
#  Paginación (versión simplificada)
# ------------------------------------------------------------------ #
ITEMS_PER_PAGE = 10 if st.runtime.scriptrunner.is_running_with_streamlit and st.runtime.scriptrunner.script_run_context.get_script_run_ctx().client.is_mobile else 45
total_pages = max(1, math.ceil(len(df) / ITEMS_PER_PAGE))
page_key = f"current_page_{linea}"
current_page = min(st.session_state.get(page_key, 1), total_pages)

def change_page(n: int):
    st.session_state[page_key] = n

col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    st.button("◀", on_click=change_page, args=(max(1, current_page - 1),), disabled=(current_page <= 1))
with col3:
    st.button("▶", on_click=change_page, args=(min(total_pages, current_page + 1),), disabled=(current_page >= total_pages))

# Mostrar productos actuales
start = (current_page - 1) * ITEMS_PER_PAGE
end = start + ITEMS_PER_PAGE
for _, row in df.iloc[start:end].iterrows():
    st.markdown(f"**{row['codigo']}** — {row['detalle']} — ${row['precio']:.2f}")
    if st.button(f"Agregar al carrito: {row['codigo']}", key=row['codigo']):
        agregar_al_carrito(row['codigo'])

# Botón flotante
st.markdown("""
<div class="carrito-fab" onclick="window.parent.document.querySelector('button[title^=\"Expand\"],button[aria-label^=\"Toggle\"]').click()">
  🛒 Carrito ({})
</div>
""".format(sum(st.session_state['carrito'].values())), unsafe_allow_html=True)

# Sidebar del carrito
with st.sidebar:
    st.markdown("<div class='sidebar-title'>🛒 Tu Carrito</div>", unsafe_allow_html=True)
    total = 0
    for codigo, cantidad in st.session_state['carrito'].items():
        producto = df_base[df_base['codigo'] == codigo].iloc[0]
        subtotal = producto['precio'] * cantidad
        total += subtotal
        st.markdown(f"<div class='cart-item'><strong>{codigo}</strong><br>{producto['detalle']}<br>Cant: {cantidad} — <strong>${subtotal:.2f}</strong></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='cart-total'>Total: ${total:.2f}</div>", unsafe_allow_html=True)
    if total > 0:
        st.link_button("📞 Pedir por WhatsApp", f"https://wa.me/?text={urllib.parse.quote('Hola, quiero pedir estos productos: ' + ', '.join(f'{k} x{v}' for k,v in st.session_state['carrito'].items()))}", type="primary", use_container_width=True)
        if st.button("Vaciar carrito"):
            st.session_state['carrito'].clear()

