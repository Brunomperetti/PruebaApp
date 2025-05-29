import streamlit as st
import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
from PIL import Image
import io, requests, tempfile, math, unicodedata

st.set_page_config(
    page_title="Catálogo Millex",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Helpers ---
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
    rows = []
    for idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
        if not row[1]:
            break
        codigo, detalle, precio = row[1], row[2], row[3]
        precio = 0 if precio is None else float(str(precio).replace("$", "").replace(",", ""))
        rows.append({"fila_excel": idx, "codigo": str(codigo), "detalle": str(detalle), "precio": precio})
    df = pd.DataFrame(rows)
    df["codigo_norm"]  = df["codigo"].apply(quitar_acentos)
    df["detalle_norm"] = df["detalle"].apply(quitar_acentos)
    return df

FILE_IDS = {
    "Línea Perros": "1EK_NlWT-eS5_7P2kWwBHsui2tKu5t26U",
    "Línea Pájaros y Roedores": "1n10EZZvZq-3M2t3rrtmvW7gfeB40VJ7F",
    "Línea Gatos": "1vSWXZKsIOqpy2wNhWsKH3Lp77JnRNKbA",
    "Línea Bombas de Acuario": "1DiXE5InuxMjZio6HD1nkwtQZe8vaGcSh",
}

# --- Inicializar estado ---
if "mostrar_carrito" not in st.session_state:
    st.session_state.mostrar_carrito = False
if "page" not in st.session_state:
    st.session_state.page = 1

# --- UI principal ---
col1, col2, col3 = st.columns([1, 2, 4])
with col1:
    if st.button("🛒 Ver carrito"):
        st.session_state.mostrar_carrito = not st.session_state.mostrar_carrito

with col2:
    linea = st.selectbox("Elegí la línea de productos:", list(FILE_IDS.keys()))

with col3:
    search_term = st.text_input("🔍 Buscar (código o descripción)…").strip().lower()
search_norm = quitar_acentos(search_term)

# --- Carga productos ---
df_base = load_products(str(fetch_excel(FILE_IDS[linea])))

if search_term:
    df = df_base[
        df_base["codigo_norm"].str.contains(search_norm, na=False)
        | df_base["detalle_norm"].str.contains(search_norm, na=False)
    ]
else:
    df = df_base.copy()

# --- Paginación ---
items_per_page = 20
total_items = len(df)
total_pages = max(1, math.ceil(total_items / items_per_page))

def set_page(n):
    if 1 <= n <= total_pages:
        st.session_state.page = n

colp1, colp2, colp3, colp4, colp5 = st.columns([1,1,2,1,1])
with colp1:
    if st.button("⏮ Primero"):
        set_page(1)
with colp2:
    if st.button("◀ Anterior"):
        set_page(st.session_state.page - 1)
with colp3:
    st.markdown(f"Página **{st.session_state.page}** de **{total_pages}**")
with colp4:
    if st.button("Siguiente ▶"):
        set_page(st.session_state.page + 1)
with colp5:
    if st.button("Último ⏭"):
        set_page(total_pages)

start_idx = (st.session_state.page - 1) * items_per_page
df_page = df.iloc[start_idx:start_idx + items_per_page]

# --- Mostrar productos ---
cols = st.columns(4)
for idx, (_, prod) in enumerate(df_page.iterrows()):
    with cols[idx % 4]:
        st.markdown(f"**{prod.codigo}**")
        st.markdown(prod.detalle)
        st.markdown(f"**${prod.precio:,.0f}**")

# --- Sidebar carrito ---
if st.session_state.mostrar_carrito:
    with st.sidebar:
        st.header("🛒 Carrito de compras")
        st.write("Tu carrito está vacío por ahora.")
        if st.button("Cerrar carrito"):
            st.session_state.mostrar_carrito = False

# --- Fin ---

