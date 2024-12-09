import streamlit as st
import pandas as pd
from io import BytesIO
from sentence_transformers import SentenceTransformer, util
import torch

# Configuración de la página
st.set_page_config(
    page_title="Homologador Inteligente",
    page_icon="⚡",
    layout="wide"
)

@st.cache_data
def load_ramedicas_data():
    url = "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    df = pd.read_excel(url)
    df['nomart_processed'] = df['nomart'].apply(preprocess_name)
    return df[['codart', 'nomart', 'nomart_processed', 'nomb_fami']]

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

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

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Homologación")
    return output.getvalue()

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

ramedicas_df = load_ramedicas_data()
model = load_model()
ramedicas_embeddings = model.encode(ramedicas_df['nomart_processed'].tolist(), convert_to_tensor=True)

st.markdown(
    """
    <h1 style="text-align: center; color: #FF5800;">RAMEDICAS S.A.S.</h1>
    <h3 style="text-align: center; color: #3A86FF;">Homologador Inteligente</h3>
    """,
    unsafe_allow_html=True
)

option = st.radio("Selecciona la opción que deseas usar:", ["Opción 1: Solo nombre", "Opción 2: Nombre y laboratorio"])

if option == "Opción 1: Solo nombre":
    client_name = st.text_input("Ingresa el nombre del producto:")
    
    if client_name:
        match = find_best_match(client_name, ramedicas_df, ramedicas_embeddings, model)
        results_df = pd.DataFrame([match])
        st.dataframe(results_df)

        excel_data = to_excel(results_df)
        st.download_button(
            label="📥 Descargar resultados en Excel",
            data=excel_data,
            file_name="homologacion_resultados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

elif option == "Opción 2: Nombre y laboratorio":
    client_name = st.text_input("Ingresa el nombre del producto:")
    lab_name = st.text_input("Ingresa el laboratorio:")

    if client_name and lab_name:
        filtered_df = ramedicas_df[ramedicas_df['nomb_fami'].str.contains(lab_name, case=False, na=False)]
        if not filtered_df.empty:
            filtered_embeddings = model.encode(filtered_df['nomart_processed'].tolist(), convert_to_tensor=True)
            match = find_best_match(client_name, filtered_df, filtered_embeddings, model)
            results_df = pd.DataFrame([match])
            st.dataframe(results_df)

            excel_data = to_excel(results_df)
            st.download_button(
                label="📥 Descargar resultados en Excel",
                data=excel_data,
                file_name="homologacion_resultados_filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No se encontraron productos para el laboratorio ingresado.")
