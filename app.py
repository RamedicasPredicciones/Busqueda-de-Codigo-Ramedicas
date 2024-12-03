# Código optimizado con precálculo de embeddings de RAMEDICAS

import streamlit as st
import pandas as pd
from io import BytesIO
from sentence_transformers import SentenceTransformer, util
import pickle
import os

# Configuración general de la página de Streamlit
st.set_page_config(
    page_title="Homologador Inteligente",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Preprocesar nombres para embeddings
def preprocess_name(name):
    name = str(name).lower()
    return name.replace("+", " ").replace("/", " ").replace("-", " ").replace(",", "")

# Convertir DataFrame a archivo Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Homologación")
    return output.getvalue()

# Función para cargar los datos desde Google Drive
@st.cache_data
def load_ramedicas_data():
    ramedicas_url = (
        "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    )
    try:
        ramedicas_df = pd.read_excel(ramedicas_url, sheet_name="Hoja1")
        return ramedicas_df[['codart', 'nomart']]
    except Exception as e:
        st.error(f"Error al cargar datos desde Google Drive: {e}")
        return pd.DataFrame()

# Inicializar el modelo de Sentence Transformers
@st.cache_resource
def load_model():
    return SentenceTransformer('paraphrase-MiniLM-L3-v2')

# Cargar o calcular embeddings de RAMEDICAS
@st.cache_data
def load_or_create_ramedicas_embeddings(ramedicas_df, model, filename="ramedicas_embeddings.pkl"):
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            embeddings = pickle.load(f)
    else:
        ramedicas_df['nomart_processed'] = ramedicas_df['nomart'].apply(preprocess_name)
        embeddings = model.encode(ramedicas_df['nomart_processed'].tolist(), convert_to_tensor=True)
        with open(filename, 'wb') as f:
            pickle.dump(embeddings, f)
    return embeddings

# Generar coincidencias
def find_best_matches(client_names, ramedicas_df, ramedicas_embeddings, model, threshold=0.5):
    client_names_processed = [preprocess_name(name) for name in client_names]
    client_embeddings = model.encode(client_names_processed, convert_to_tensor=True)

    # Calcular similitudes por lotes
    similarity_scores = util.pytorch_cos_sim(client_embeddings, ramedicas_embeddings)

    matches = []
    for i, scores in enumerate(similarity_scores):
        best_idx = scores.argmax().item()
        best_score = scores[best_idx].item()

        if best_score >= threshold:
            matches.append({
                'nombre_cliente': client_names[i],
                'nombre_ramedicas': ramedicas_df.iloc[best_idx]['nomart'],
                'codart': ramedicas_df.iloc[best_idx]['codart'],
                'score': best_score
            })
        else:
            matches.append({
                'nombre_cliente': client_names[i],
                'nombre_ramedicas': "No encontrado",
                'codart': None,
                'score': best_score
            })

    return matches

# Encabezado
st.markdown(
    """
    <h1 style="text-align: center; color: #FF5800; font-family: Arial, sans-serif;">
        RAMEDICAS S.A.S.
    </h1>
    <h3 style="text-align: center; font-family: Arial, sans-serif; color: #3A86FF;">
        Homologador Inteligente de Productos
    </h3>
    <p style="text-align: center; font-family: Arial, sans-serif; color: #6B6B6B;">
        Busca coincidencias de manera más eficiente utilizando tecnología avanzada.
    </p>
    """,
    unsafe_allow_html=True
)

# Variables globales
ramedicas_df = load_ramedicas_data()
model = load_model()

if not ramedicas_df.empty:
    ramedicas_embeddings = load_or_create_ramedicas_embeddings(ramedicas_df, model)
else:
    st.error("No se pudieron cargar los datos de RAMEDICAS. Por favor, verifica la conexión.")

# Barra lateral
st.sidebar.header("Opciones")
threshold = st.sidebar.slider(
    "Umbral de similitud (0.0 - 1.0)", min_value=0.0, max_value=1.0, value=0.5, step=0.01
)

# Procesar archivo subido
uploaded_file = st.file_uploader("Sube tu archivo de Excel con la columna 'nombre':", type="xlsx")

# Procesar nombres manualmente
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

    # Filtrar nombres válidos
    client_names = [name.strip() for name in client_names if name.strip()]

    # Calcular coincidencias
    matches = find_best_matches(client_names, ramedicas_df, ramedicas_embeddings, model, threshold)
    results_df = pd.DataFrame(matches)
    st.dataframe(results_df)

    # Descargar resultados
    if not results_df.empty:
        excel_data = to_excel(results_df)
        st.download_button(
            label="📥 Descargar resultados en Excel",
            data=excel_data,
            file_name="homologacion_resultados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.warning("Por favor sube un archivo o ingresa nombres manualmente.")
