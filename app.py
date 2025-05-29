import streamlit as st
import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
import unicodedata
import tempfile
import requests
from io import BytesIO
from PIL import Image

st.set_page_config(
    page_title="Catálogo Millex con Carrito y Cantidad",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    img_map = {}
    for img in ws._images:
        if hasattr(img.anchor, '_from'):
            fila = img.anchor._from.row + 1
            try:
                img_bytes = img._data()
                img_map[fila] = img_bytes
            except Exception:
                pass
    rows = []
    for idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
        if not row[1]:
            break
        codigo = str(row[1]).strip()
        detalle = str(row[2]).strip()
        precio_raw = row[3]
        try:
            precio = float(str(precio_raw).replace("$", "").replace(",", "").strip())
        except Exception:
            precio = 0.0
        rows.append({
            "fila_excel": idx,
            "codigo": codigo,
            "detalle": detalle,
            "precio": precio,
            "img_bytes": img_map.get(idx, None),
        })
    df = pd.DataFrame(rows)
    df["codigo_norm"] = df["codigo"].apply(quitar_acentos)
    df["detalle_norm"] = df["detalle"].apply(quitar_acentos)
    return df

FILE_IDS = {
    "Línea Perros": "1EK_NlWT-eS5_7P2kWwBHsui2tKu5t26U",
    "Línea Pájaros y Roedores": "1n10EZZvZq-3M2t3rrtmvW7gfeB40VJ7F",
    "Línea Gatos": "1vSWXZKsIOqpy2wNhWsKH3Lp77JnRNKbA",
    "Línea Bombas de Acuario": "1DiXE5InuxMjZio6HD1nkwtQZe8vaGcSh",
}

if "carrito" not in st.session_state:
    st.session_state["carrito"] = {}

st.sidebar.title("🛒 Carrito de Compras")
carrito = st.session_state["carrito"]

if carrito:
    total = 0
    for cod, item in carrito.items():
        st.sidebar.write(f"{item['detalle']} x {item['cantidad']} = ${item['precio']*item['cantidad']:.2f}")
        total += item['precio'] * item['cantidad']
    st.sidebar.markdown(f"**Total: ${total:,.2f}**")
    if st.sidebar.button("Vaciar carrito"):
        st.session_state["carrito"] = {}
        st.experimental_rerun()
else:
    st.sidebar.write("El carrito está vacío")

col_linea, col_search = st.columns([2.2, 3])
with col_linea:
    linea = st.selectbox(
        "Elegí la línea de productos:",
        list(FILE_IDS.keys()),
        index=0,
    )
with col_search:
    search_term = st.text_input(
        "🔍 Buscar (código o descripción)…",
        placeholder="Buscar productos...",
    ).strip().lower()

search_norm = quitar_acentos(search_term)

df_base = load_products(str(fetch_excel(FILE_IDS[linea])))

if search_term:
    df = df_base[
        df_base["codigo_norm"].str.contains(search_norm, na=False) |
        df_base["detalle_norm"].str.contains(search_norm, na=False)
    ]
else:
    df = df_base.copy()

items_por_pagina = 20
total_items = len(df)
total_paginas = (total_items // items_por_pagina) + (1 if total_items % items_por_pagina > 0 else 0)
pagina_actual = st.session_state.get("pagina_actual", 1)
if pagina_actual < 1:
    pagina_actual = 1
elif pagina_actual > total_paginas and total_paginas > 0:
    pagina_actual = total_paginas

start_idx = (pagina_actual - 1) * items_por_pagina
end_idx = start_idx + items_por_pagina
df_pagina = df.iloc[start_idx:end_idx]

def cambiar_pagina(nueva_pagina):
    st.session_state["pagina_actual"] = nueva_pagina
    st.experimental_rerun()

# Productos con formulario para cantidad y agregar
for idx, row in df_pagina.iterrows():
    cols = st.columns([1, 5, 2, 2])
    with cols[0]:
        if row["img_bytes"]:
            try:
                img = Image.open(BytesIO(row["img_bytes"]))
                st.image(img, width=60)
            except Exception:
                st.write("🖼️")
        else:
            st.write("🖼️")
    with cols[1]:
        st.markdown(f"**{row['codigo']}**")
        st.write(row["detalle"])
    with cols[2]:
        st.markdown(f"${row['precio']:,.2f}")
    with cols[3]:
        form_key = f"form_{row['codigo']}"
        with st.form(form_key, clear_on_submit=True):
            cantidad = st.number_input("Cantidad", min_value=1, step=1, key=f"cant_{row['codigo']}")
            agregar = st.form_submit_button("Agregar al carrito")
            if agregar:
                cod = row['codigo']
                if cod in carrito:
                    carrito[cod]["cantidad"] += cantidad
                else:
                    carrito[cod] = {
                        "detalle": row["detalle"],
                        "precio": row["precio"],
                        "cantidad": cantidad,
                    }
                st.session_state["carrito"] = carrito
                st.success(f"Agregaste {cantidad} x {row['detalle']} al carrito")
                st.experimental_rerun()

col_ant, col_info, col_sig = st.columns([1, 3, 1])
with col_ant:
    if st.button("⬅️ Anterior") and pagina_actual > 1:
        cambiar_pagina(pagina_actual - 1)
with col_info:
    st.write(f"Página {pagina_actual} de {total_paginas} — Total: {total_items} productos")
with col_sig:
    if st.button("Siguiente ➡️") and pagina_actual < total_paginas:
        cambiar_pagina(pagina_actual + 1)

st.session_state["pagina_actual"] = pagina_actual


