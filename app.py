import streamlit as st
import pandas as pd
from io import BytesIO
from sentence_transformers import SentenceTransformer, util
import torch

# Configuración de la página
st.set_page_config(
    page_title="Homologador Inteligente",
    page_icon="🤖",
    layout="wide"
)

# Cargar datos con caché
@st.cache_data
def load_ramedicas_data():
    url = "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    df = pd.read_excel(url)
    df['nomart_processed'] = df['nomart'].apply(preprocess_name)
    return df[['codart', 'nomart', 'nomart_processed']]

# Cargar modelo con caché
@st.cache_resource
def load_model(model_name='all-MiniLM-L6-v2'):
    return SentenceTransformer(model_name)

# Preprocesar nombres
def preprocess_name(name):
    name = str(name).lower()
    replacements = {
        "+": " ",
        "/": " ",
        "-": " ",
        ",": "",
        ".": "",
        "x": " x ",
        "medicamento": "",
        "generico": ""
    }
    for key, val in replacements.items():
        name = name.replace(key, val)
    return " ".join(name.split())

# Convertir DataFrame a archivo Excel para descarga
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Homologación")
    return output.getvalue()

# Buscar mejores coincidencias usando procesamiento por lotes
def find_best_matches_batch(client_names, ramedicas_df, ramedicas_embeddings, model, top_n=3):
    client_names_processed = [preprocess_name(name) for name in client_names]
    client_embeddings = model.encode(client_names_processed, convert_to_tensor=True)
    scores = util.pytorch_cos_sim(client_embeddings, ramedicas_embeddings)  # Matriz de similitudes
    top_indices = torch.topk(scores, k=top_n, dim=1).indices.tolist()

    all_matches = []
    for i, name in enumerate(client_names):
        for idx in top_indices[i]:
            all_matches.append({
                'nombre_cliente': name,
                'nombre_ramedicas': ramedicas_df.iloc[idx]['nomart'],
                'codart': ramedicas_df.iloc[idx]['codart'],
                'score': scores[i, idx].item()
            })
    return all_matches

# Cargar datos y modelo
ramedicas_df = load_ramedicas_data()
model_name = st.selectbox("Selecciona el modelo:", ["all-MiniLM-L6-v2", "all-mpnet-base-v2"])
model = load_model(model_name)

# Precalcular embeddings de RAMEDICAS
ramedicas_embeddings = model.encode(ramedicas_df['nomart_processed'].tolist(), convert_to_tensor=True)

# Interfaz de usuario
st.markdown(
    """
    <h1 style="text-align: center; color: #FF5800;">RAMEDICAS S.A.S.</h1>
    <h3 style="text-align: center; color: #3A86FF;">Homologador Inteligente</h3>
    <p style="text-align: center; color: #6B6B6B;">Resultados más precisos con tecnología avanzada.</p>
    """,
    unsafe_allow_html=True
)

# Entrada de datos
uploaded_file = st.file_uploader("Sube tu archivo Excel con la columna 'nombre':", type="xlsx")
client_names_manual = st.text_area("Ingresa los nombres manualmente, separados por saltos de línea:")

if uploaded_file or client_names_manual:
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

    st.info("Procesando... Por favor, espera.")
    all_matches = find_best_matches_batch(client_names, ramedicas_df, ramedicas_embeddings, model)

    results_df = pd.DataFrame(all_matches)
    st.dataframe(results_df)

    if not results_df.empty:
        excel_data = to_excel(results_df)
        st.download_button(
            label="📥 Descargar resultados en Excel",
            data=excel_data,
            file_name="homologacion_resultados_inteligente.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
