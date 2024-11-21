import streamlit as st
import pandas as pd
from io import BytesIO
from rapidfuzz import fuzz, process

# Cargar datos de Ramedicas desde Google Drive
@st.cache_data
def load_ramedicas_data():
    ramedicas_url = (
        "https://docs.google.com/spreadsheets/d/19myWtMrvsor2P_XHiifPgn8YKdTWE39O/export?format=xlsx&sheet=Hoja1"
    )
    ramedicas_df = pd.read_excel(ramedicas_url, sheet_name="Hoja1")
    return ramedicas_df[['codart', 'nombre']]  # Cambié 'nomart' a 'nombre'

# Preprocesar nombres
def preprocess_name(name): 
    replacements = {
        "(": "", ")": "", "+": " ", "/": " ", "-": " ", ",": "", ";": "", ".": "",
        "mg": " mg", "ml": " ml", "capsula": " capsulas", "tablet": " tableta",
    }
    for old, new in replacements.items():
        name = name.lower().replace(old, new)
    stopwords = {"de", "el", "la", "los", "las", "un", "una", "y", "en", "por"}
    words = [word for word in name.split() if word not in stopwords]
    return " ".join(sorted(words))

def find_best_match(client_name, ramedicas_df, similarity_threshold=80):
    client_name_processed = preprocess_name(client_name)
    ramedicas_df['processed_nombre'] = ramedicas_df['nombre'].apply(preprocess_name)  # Cambié 'nomart' a 'nombre'

    # Intentar encontrar una coincidencia exacta
    if client_name_processed in ramedicas_df['processed_nombre'].values:
        exact_match = ramedicas_df[ramedicas_df['processed_nombre'] == client_name_processed].iloc[0]
        return {'nombre_cliente': client_name, 'nombre_ramedicas': exact_match['nombre'], 'codart': exact_match['codart'], 'score': 100}

    # Si no hay coincidencia exacta, buscar la mejor coincidencia aproximada
    matches = process.extract(client_name_processed, ramedicas_df['processed_nombre'], scorer=fuzz.token_sort_ratio, limit=10)
    
    # Filtrar solo las coincidencias que tienen un puntaje por encima del umbral de similitud
    best_match = None
    for match, score, idx in matches:
        if score >= similarity_threshold:  # Filtrar por un puntaje mínimo de similitud
            candidate_row = ramedicas_df.iloc[idx]
            best_match = {'nombre_cliente': client_name, 'nombre_ramedicas': candidate_row['nombre'], 'codart': candidate_row['codart'], 'score': score}
            break  # Detenerse después de encontrar la mejor coincidencia dentro del umbral

    # Si no se encuentra una coincidencia que cumpla el umbral, no mostrar ningún resultado
    if not best_match:
        return {'nombre_cliente': client_name, 'nombre_ramedicas': "Sin coincidencias precisas", 'codart': "", 'score': 0}

    return best_match

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Homologación")
    return output.getvalue()

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
        margin-bottom: 40px;
        color: #34495E;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Título
st.markdown('<div class="title">RAMÉDICAS SAS</div>', unsafe_allow_html=True)

# Subtitulo
st.markdown('<div class="subtitle">Codigo Ramedicas - Homologador de Productos</div>', unsafe_allow_html=True)

# Botón para actualizar la base de datos
if st.button("Actualizar base de datos"):
    st.cache_data.clear()

# Input de nombres o archivo subido
client_names_manual = st.text_area("Ingresa los nombres de los productos que envio el cliente, separados por comas o saltos de línea:")
uploaded_file = st.file_uploader("O sube tu archivo de excel con la columna nombres que contenga productos aquí:", type="xlsx")

# Procesar manualmente
if client_names_manual:
    client_names_list = [name.strip() for name in client_names_manual.splitlines()]
    ramedicas_df = load_ramedicas_data()
    results = [find_best_match(name, ramedicas_df) for name in client_names_list]
    results_df = pd.DataFrame(results)
    st.dataframe(results_df)
    st.download_button("Descargar resultados", data=to_excel(results_df), file_name="homologacion.xlsx")

if uploaded_file:
    client_names_df = pd.read_excel(uploaded_file)
    if 'nombre' not in client_names_df.columns:
        st.error("El archivo debe tener una columna llamada 'nombre'.")
    else:
        ramedicas_df = load_ramedicas_data()
        results = [find_best_match(name, ramedicas_df) for name in client_names_df['nombre']]
        results_df = pd.DataFrame(results)
        st.dataframe(results_df)
        st.download_button("Descargar resultados", data=to_excel(results_df), file_name="homologacion.xlsx")
