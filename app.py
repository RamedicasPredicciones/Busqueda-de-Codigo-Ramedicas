# Revised code to optimize matching precision and flexibility.
import streamlit as st
import pandas as pd
from io import BytesIO
from sentence_transformers import SentenceTransformer, util
import torch
import unidecode

# Streamlit Page Configuration
st.set_page_config(
    page_title="Homologador Preciso",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Function to load data
@st.cache_data
def load_ramedicas_data():
    url = "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    try:
        df = pd.read_excel(url, sheet_name="Hoja1")
        return df[['codart', 'nomart']]
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Load the SentenceTransformer model
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

# Advanced text preprocessing function
def preprocess_name(name):
    """
    Preprocesses a name by converting to lowercase, removing accents, and normalizing spaces.
    """
    name = unidecode.unidecode(str(name).lower())  # Remove accents
    replacements = {
        "+": " ",
        "/": " ",
        "-": " ",
        ",": "",
        ".": "",
        "x": " x ",  # Separate 'x' for unit compatibility
    }
    for key, val in replacements.items():
        name = name.replace(key, val)
    return " ".join(name.split())  # Remove extra spaces

# Convert DataFrame to Excel for download
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Homologación")
    return output.getvalue()

# Optimized matching function with top-N results
def find_best_match(client_name, ramedicas_df, ramedicas_embeddings, model, threshold=0.7, top_n=3):
    """
    Finds the best matches for a client name in the Ramedicas dataset.
    Returns the top-N results if above threshold.
    """
    client_name_processed = preprocess_name(client_name)
    client_embedding = model.encode(client_name_processed, convert_to_tensor=True)
    scores = util.pytorch_cos_sim(client_embedding, ramedicas_embeddings)[0]
    top_results = torch.topk(scores, top_n)

    matches = []
    for idx, score in zip(top_results.indices, top_results.values):
        idx = idx.item()
        score = score.item()
        if score >= threshold:
            matches.append({
                'nombre_cliente': client_name,
                'nombre_ramedicas': ramedicas_df.iloc[idx]['nomart'],
                'codart': ramedicas_df.iloc[idx]['codart'],
                'score': score
            })

    # If no matches above threshold, return 'No encontrado'
    if not matches:
        return {
            'nombre_cliente': client_name,
            'nombre_ramedicas': "No encontrado",
            'codart': None,
            'score': max(scores).item()
        }

    return matches[0]  # Return the best match (can modify to return all matches)

# Main Application Code
st.markdown(
    """
    <h1 style="text-align: center; color: #FF5800; font-family: Arial, sans-serif;">
        RAMEDICAS S.A.S.
    </h1>
    <h3 style="text-align: center; font-family: Arial, sans-serif; color: #3A86FF;">
        Homologador Preciso y Flexible
    </h3>
    <p style="text-align: center; font-family: Arial, sans-serif; color: #6B6B6B;">
        Ahora con resultados aún más precisos y personalizables.
    </p>
    """,
    unsafe_allow_html=True
)

# Load data and model
ramedicas_df = load_ramedicas_data()
model = load_model()

if not ramedicas_df.empty:
    ramedicas_df['nomart_processed'] = ramedicas_df['nomart'].apply(preprocess_name)
    ramedicas_embeddings = model.encode(ramedicas_df['nomart_processed'].tolist(), convert_to_tensor=True)
else:
    st.error("No se pudieron cargar los datos de RAMEDICAS. Por favor, verifica la conexión.")

# Sidebar and file upload
st.sidebar.header("Opciones")
threshold = st.sidebar.slider("Umbral de similitud", min_value=0.5, max_value=1.0, value=0.7, step=0.05)
uploaded_file = st.file_uploader("Sube tu archivo de Excel con la columna 'nombre':", type="xlsx")
client_names_manual = st.text_area("Ingresa los nombres de los productos, separados por saltos de línea:")

if uploaded_file or client_names_manual:
    st.info("Procesando los datos, por favor espera...")
    client_names = []

    if uploaded_file:
        client_names_df = pd.read_excel(uploaded_file)
        if 'nombre' not in client_names_df.columns:
            st.error("El archivo debe tener una columna llamada 'nombre'.")
        else:
            client_names = client_names_df['nombre'].tolist()

    if client_names_manual:
        client_names.extend(client_names_manual.split("\n"))

    client_names = [name.strip() for name in client_names if name.strip()]

    matches = [
        find_best_match(name, ramedicas_df, ramedicas_embeddings, model, threshold)
        for name in client_names
    ]

    results_df = pd.DataFrame(matches)
    st.dataframe(results_df)

    if not results_df.empty:
        excel_data = to_excel(results_df)
        st.download_button(
            label="📥 Descargar resultados en Excel",
            data=excel_data,
            file_name="homologacion_resultados_precisos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.warning("Por favor sube un archivo o ingresa nombres manualmente.")
