# Estilo de la página
st.markdown(
    """
    <style>
    .title {
        font-size: 40px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 10px;
        color: #FF5733;
    }
    .subtitle {
        font-size: 25px;
        font-weight: normal;
        text-align: center;
        margin-bottom: 10px;
        color: #34495E;
    }
    .description {
        font-size: 18px;
        text-align: center;
        margin-bottom: 40px;
        color: #7F8C8D;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Título y subtítulo
st.markdown('<div class="title">RAMÉDICAS SAS</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Código Ramédicas - Homologador de Productos</div>', unsafe_allow_html=True)

# Descripción
st.markdown(
    '<div class="description">Esta página permite homologar los nombres de productos ingresados por el cliente con los registros oficiales de RAMÉDICAS SAS, utilizando un proceso automatizado de comparación inteligente. Simplifica la gestión y asegura la precisión en la identificación de productos.</div>',
    unsafe_allow_html=True
)

# Mostrar el logo
st.image("Logo Ramedicas.png", use_column_width=False, width=200)
