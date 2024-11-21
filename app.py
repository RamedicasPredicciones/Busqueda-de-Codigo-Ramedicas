import unicodedata
import streamlit as st
import pandas as pd
from io import BytesIO
from rapidfuzz import fuzz, process

# Función para normalizar tildes (eliminar acentos)
def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

# Cargar datos de Ramedicas desde Google Drive
@st.cache_data
def load_ramedicas_data():
    ramedicas_url = (
        "https://docs.google.com/spreadsheets/d/19myWtMrvsor2P_XHiifPgn8YKdTWE39O/export?format=xlsx&sheet=Hoja1"
    )
    ramedicas_df = pd.read_excel(ramedicas_url, sheet_name="Hoja1")
    return ramedicas_df[['codart', 'nomart', 'presentación']]  # Usamos 'presentación' con tilde

# Preprocesar nombres
def preprocess_name(name): 
    name = remove_accents(name)  # Eliminar tildes
    replacements = {
        "(": "", ")": "", "+": " ", "/": " ", "-": " ", ",": "", ";": "", ".": "",
        "mg": " mg", "ml": " ml", "capsula": " capsulas", "tablet": " tableta",
    }
    for old, new in replacements.items():
        name = name.lower().replace(old, new)
    stopwords = {"de", "el", "la", "los", "las", "un", "una", "y", "en", "por"}
    words = [word for word in name.split() if word not in stopwords]
    return " ".join(sorted(words))

def find_best_match(client_name, ramedicas_df):
    client_name_processed = preprocess_name(client_name)
    ramedicas_df['processed_nombre'] = ramedicas_df['nomart'].apply(preprocess_name)  # Usamos 'nomart'

    # Lista para almacenar todas las coincidencias
    matches_list = []
    client_terms = set(client_name_processed.split())
    
    # Obtenemos las mejores coincidencias
    matches = process.extract(client_name_processed, ramedicas_df['processed_nombre'], scorer=fuzz.token_set_ratio, limit=10)

    for match, score, idx in matches:
        candidate_row = ramedicas_df.iloc[idx]
        candidate_terms = set(match.split())
        if client_terms.issubset(candidate_terms):
            # Verificamos si coincide la presentación
            coincide_presentacion = 'Sí' if client_name_processed == preprocess_name(candidate_row['presentación']) else 'No'
            matches_list.append({
                'nombre_cliente': client_name,
                'nombre_ramedicas': candidate_row['nomart'],
                'codart': candidate_row['codart'],
                'presentación': candidate_row['presentación'],
                'score': score,
                'coincide_presentacion': coincide_presentacion
            })

    if not matches_list and matches:
        # Si no se encontró una coincidencia perfecta, se devuelve el primer resultado
        candidate_row = ramedicas_df.iloc[matches[0][2]]
        matches_list.append({
            'nombre_cliente': client_name,
            'nombre_ramedicas': matches[0][0],
            'codart': candidate_row['codart'],
            'presentación': candidate_row['presentación'],
            'score': matches[0][1],
            'coincide_presentacion': 'No'
        })

    return matches_list

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
    all_results = []

    for name in client_names_list:
        results = find_best_match(name, ramedicas_df)
        all_results.extend(results)  # Agregar todas las coincidencias a la lista general

    results_df = pd.DataFrame(all_results)
    st.dataframe(results_df)
    st.download_button("Descargar resultados", data=to_excel(results_df), file_name="homologacion.xlsx")

if uploaded_file:
    client_names_df = pd.read_excel(uploaded_file)
    if 'nombre' not in client_names_df.columns:
        st.error("El archivo debe tener una columna llamada 'nombre'.")
    else:
        ramedicas_df = load_ramedicas_data()
        all_results = []

        for name in client_names_df['nombre']:
            results = find_best_match(name, ramedicas_df)
            all_results.extend(results)

        results_df = pd.DataFrame(all_results)
        st.dataframe(results_df)
        st.download_button("Descargar resultados", data=to_excel(results_df), file_name="homologacion.xlsx")
