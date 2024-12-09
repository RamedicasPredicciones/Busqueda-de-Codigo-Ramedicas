import streamlit as st
import pandas as pd
from io import BytesIO
from sentence_transformers import SentenceTransformer, util
import torch
import os

# Configuración de la página
st.set_page_config(
    page_title="Homologador Inteligente",
    page_icon="⚡",
    layout="wide"
)

# Cargar modelo con caché (esto no se modifica)
@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

# Cargar datos y embeddings precalculados
@st.cache_resource
def load_data_and_embeddings():
    url = "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    df = pd.read_excel(url)
    df['nomart_processed'] = df['nomart'].apply(preprocess_name)
    
    # Cargar modelo
    model = load_model()
    
    # Calcular embeddings una vez
    embeddings = model.encode(df['nomart_processed'].tolist(), convert_to_tensor=True)
    return df, embeddings

# Preprocesar nombres
def preprocess_name(name):
    name = str(name).lower()
    replacements = {
        "+": " + ",
        "/": " + ",
        "-": " ",
        ",": "",
        ".": "",
        "x": " x "
    }
    for key, val in replacements.items():
        name = name.replace(key, val)
    return " ".join(name.split())

# Convertir DataFrame a archivo Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Homologación")
    return output.getvalue()

# Buscar la mejor coincidencia
def find_best_match(client_name, ramedicas_df, ramedicas_embeddings, model, threshold=0.7):
    client_name_processed = preprocess_name(client_name)
    client_embedding = model.encode(client_name_processed, convert_to_tensor=True)

    scores = util.pytorch_cos_sim(client_embedding, ramedicas_embeddings)[0]
    best_idx = scores.argmax().item()
    best_score = scores[best_idx].item()

    if best_score >= threshold:
        return {
            'nombre_cliente': client_name,
            'nombre_ramedicas': ramedicas_df.iloc[best_idx]['nomart'],
            'codart': ramedicas_df.iloc[best_idx]['codart'],
            'score': best_score
        }
    else:
        return {
            'nombre_cliente': client_name,
            'nombre_ramedicas': "No encontrado",
            'codart': None,
            'score': best_score
        }

# Cargar datos y modelo
st.info("Cargando datos, por favor espera...")
ramedicas_df, ramedicas_embeddings = load_data_and_embeddings()

# Interfaz de usuario
st.markdown(
    """
    <h1 style="text-align: center; color: #FF5800;">RAMEDICAS S.A.S.</h1>
    <h3 style="text-align: center; color: #3A86FF;">Homologador Inteligente</h3>
    <p style="text-align: center; color: #6B6B6B;">Resultados rápidos con tecnología avanzada.</p>
    """,
    unsafe_allow_html=True
)

# Entrada de datos
client_names_manual = st.text_area("Ingresa los nombres manualmente, separados por saltos de línea:")

if client_names_manual:
    client_names = [name.strip() for name in client_names_manual.split("\n") if name.strip()]
    
    if client_names:
        st.info("Procesando... Por favor, espera.")
        
        matches = [
            find_best_match(name, ramedicas_df, ramedicas_embeddings, load_model())
            for name in client_names
        ]

        results_df = pd.DataFrame(matches)
        st.dataframe(results_df)

        if not results_df.empty:
            excel_data = to_excel(results_df)
            st.download_button(
                label="📥 Descargar resultados en Excel",
                data=excel_data,
                file_name="homologacion_resultados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
