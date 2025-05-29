import streamlit as st
import pandas as pd
from openpyxl import load_workbook
from pathlib import Path
from PIL import Image
import io, urllib.parse, requests, tempfile, math, unicodedata

# Configuración general
st.set_page_config(
    page_title="Catálogo Millex",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# CSS global para personalizar el botón de la barra lateral
st.markdown(
    """
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

/* Personalizar el botón de la barra lateral */
button[data-testid="stSidebarNavToggler"] {
    position: relative;
    background: transparent;
    border: none;
    height: auto;
    width: auto;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 100;
    padding-left: 40px; /* Espacio para el texto */
    color: #f63366 !important;
    font-weight: 600;
    font-size: 1rem;
}

/* Eliminar la flecha del botón */
button[data-testid="stSidebarNavToggler"] > div {
    display: none !important;
}

/* Nuevas reglas para móvil */
@media(max-width:768px){
  .pagination-mobile{display:flex;justify-content:center;gap:16px;margin:20px 0;}
  .pagination-mobile button{background:#f0f2f6;border:none;border-radius:6px;
    padding:8px 16px;cursor:pointer;transition:.3s;font-size:18px;}
  .pagination-mobile button:hover{background:#e0e2e6;}
  .pagination-mobile button:disabled{opacity:.5;cursor:not-allowed;}
  .pagination{display:none;}
  .mobile-pager{display:block!important;}
  .mobile-items-per-page{display:block!important;}
  .desktop-cart-button-container {display:none!important;}
}

/* Resto del CSS permanece igual... */
</style>
""",
    unsafe_allow_html=True,
)

# JavaScript para cambiar el texto del botón
st.markdown(
    """
<script>
// Esperar a que el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Seleccionar el botón del sidebar
    const sidebarBtn = window.parent.document.querySelector('button[data-testid="stSidebarNavToggler"]');
    
    if(sidebarBtn) {
        // Eliminar el contenido existente (flecha)
        sidebarBtn.innerHTML = '';
        
        // Crear nuevo contenido
        const btnContent = document.createElement('div');
        btnContent.style.display = 'flex';
        btnContent.style.alignItems = 'center';
        btnContent.style.gap = '8px';
        
        // Agregar texto "Ver Carrito"
        const textSpan = document.createElement('span');
        textSpan.textContent = 'Ver Carrito';
        btnContent.appendChild(textSpan);
        
        // Agregar icono de carrito opcional
        const cartIcon = document.createElement('span');
        cartIcon.textContent = '🛒';
        btnContent.insertBefore(cartIcon, textSpan);
        
        // Aplicar los cambios
        sidebarBtn.appendChild(btnContent);
    }
});
</script>
""",
    unsafe_allow_html=True,
)





