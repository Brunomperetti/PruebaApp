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
    padding: 8px 12px;
    color: #f63366 !important;
    font-weight: 600;
    font-size: 1rem;
}

/* Estilo para la flecha más grande */
button[data-testid="stSidebarNavToggler"]::after {
    content: "▶";
    font-size: 1.5rem;
    margin-left: 8px;
}

/* Posicionamiento del texto "Carrito" */
.sidebar-toggle-text {
    margin-left: 8px;
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
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<script>
// Función para añadir el texto al botón
function addCartText() {
    const sidebarBtn = window.parent.document.querySelector('button[data-testid="stSidebarNavToggler"]');

    if(sidebarBtn && !sidebarBtn.querySelector('.sidebar-toggle-text')) {
        const textSpan = document.createElement('span');
        textSpan.className = 'sidebar-toggle-text';
        textSpan.textContent = 'Carrito';
        sidebarBtn.appendChild(textSpan);
    }
}

// Ejecutar al cargar y con retardo por si Streamlit tarda en renderizar
document.addEventListener('DOMContentLoaded', addCartText);
setTimeout(addCartText, 1000);

// Observar cambios en el DOM por si Streamlit redibuja
const observer = new MutationObserver(addCartText);
observer.observe(document.body, { childList: true, subtree: true });
</script>
""",
    unsafe_allow_html=True,
)

