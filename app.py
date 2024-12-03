import streamlit as st
import pandas as pd
from io import BytesIO
from sentence_transformers import SentenceTransformer, util
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Cargar datos de Ramedicas desde Google Drive
@st.cache_data
def load_ramedicas_data():
    ramedicas_url = (
        "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    )
    ramedicas_df = pd.read_excel(ramedicas_url, sheet_name="Hoja1")
    return ramedicas_df[['codart', 'nomart']]

# Inicializar el modelo de Sentence Transformers
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

# Preprocesar nombres
def preprocess_name(name):
    name = str(name).lower()
    return name.replace("+", " ").replace("/", " ").replace("-", " ").replace(",", "")

# Convertir DataFrame a archivo Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Homologación")
    return output.getvalue()

# Función para buscar coincidencias
def find_matches(client_name, ramedicas_df, ramedicas_embeddings, model, top_n=3):
    client_name_processed = preprocess_name(client_name)
    client_embedding = model.encode(client_name_processed, convert_to_tensor=True)
    
    scores = util.pytorch_cos_sim(client_embedding, ramedicas_embeddings)[0]
    best_indices = scores.argsort(descending=True)[:top_n].tolist()
    
    matches = []
    for idx in best_indices:
        matches.append({
            'nombre_cliente': client_name,
            'nombre_ramedicas': ramedicas_df.iloc[idx]['nomart'],
            'codart': ramedicas_df.iloc[idx]['codart'],
            'score': scores[idx].item()
        })
    return matches

# Homologar nombres usando TF-IDF como modelo complementario
def tfidf_match(client_names, ramedicas_df):
    vectorizer = TfidfVectorizer(analyzer='word')
    tfidf_matrix = vectorizer.fit_transform(ramedicas_df['nomart'])
    client_matrix = vectorizer.transform(client_names)

    cosine_similarities = cosine_similarity(client_matrix, tfidf_matrix)
    matches = []

    for idx, name in enumerate(client_names):
        best_idx = np.argmax(cosine_similarities[idx])
        matches.append({
            'nombre_cliente': name,
            'nombre_ramedicas': ramedicas_df.iloc[best_idx]['nomart'],
            'codart': ramedicas_df.iloc[best_idx]['codart'],
            'score': cosine_similarities[idx, best_idx]
        })
    return matches

# Interfaz de Streamlit
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

# Actualizar la base de datos
if st.button("Actualizar base de datos"):
    st.cache_data.clear()

# Subir archivo
uploaded_file = st.file_uploader("Sube tu archivo de Excel con la columna 'nombre':", type="xlsx")

# Procesar texto manual
client_names_manual = st.text_area("Ingresa nombres de productos separados por saltos de línea:")

ramedicas_df = load_ramedicas_data()
model = load_model()

# Generar embeddings para los datos de RAMEDICAS
ramedicas_df['nomart_processed'] = ramedicas_df['nomart'].apply(preprocess_name)
ramedicas_embeddings = model.encode(ramedicas_df['nomart_processed'].tolist(), convert_to_tensor=True)

if uploaded_file or client_names_manual:
    st.info("Procesando los datos, por favor espera...")
    
    if uploaded_file:
        client_names_df = pd.read_excel(uploaded_file)
        if 'nombre' not in client_names_df.columns:
            st.error("El archivo debe tener una columna llamada 'nombre'.")
        else:
            client_names = client_names_df['nombre'].dropna().tolist()
    else:
        client_names = client_names_manual.split("\n")

    # Homologar nombres usando Sentence Transformers
    all_matches = []
    for name in client_names:
        matches = find_matches(name, ramedicas_df, ramedicas_embeddings, model, top_n=3)
        all_matches.extend(matches)

    results_df = pd.DataFrame(all_matches)
    st.dataframe(results_df)

    excel_data = to_excel(results_df)
    st.download_button(
        label="📥 Descargar resultados en Excel",
        data=excel_data,
        file_name="homologacion_resultados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
