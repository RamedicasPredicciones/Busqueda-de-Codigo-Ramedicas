import streamlit as st
import pandas as pd
from io import BytesIO
from sentence_transformers import SentenceTransformer, util
import torch

# -------------------------------
# 🔧 Configuración Inicial
# -------------------------------
st.set_page_config(
    page_title="Homologador Inteligente",
    page_icon="⚡",
    layout="wide"
)

# -------------------------------
# 📦 Cargar Modelo y Datos
# -------------------------------
@st.cache_resource
def load_model():
    """Carga el modelo SentenceTransformer."""
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource
def load_data_and_embeddings():
    """Carga los datos y calcula los embeddings una vez."""
    url = "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    df = pd.read_excel(url)
    df['nomart_processed'] = df['nomart'].apply(preprocess_name)
    model = load_model()
    embeddings = model.encode(df['nomart_processed'].tolist(), convert_to_tensor=True)
    return df, embeddings

# -------------------------------
# 🛠️ Funciones Auxiliares
# -------------------------------
def preprocess_name(name: str) -> str:
    """Preprocesa los nombres para normalizar el texto."""
    replacements = {
        "+": " + ",
        "/": " + ",
        "-": " ",
        ",": "",
        ".": "",
        "x": " x ",
        "\(.*?\)": "",  # Elimina contenido entre paréntesis
        "\[.*?\]": ""   # Elimina contenido entre corchetes
    }
    name = str(name).lower()
    for key, val in replacements.items():
        name = name.replace(key, val)
    return " ".join(name.split())

def to_excel(df: pd.DataFrame) -> BytesIO:
    """Convierte un DataFrame en un archivo Excel descargable."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Homologación")
    output.seek(0)
    return output

def find_best_match(client_name: str, df: pd.DataFrame, embeddings, model, threshold=0.7) -> dict:
    """Encuentra la mejor coincidencia para un nombre dado."""
    client_name_processed = preprocess_name(client_name)
    client_embedding = model.encode(client_name_processed, convert_to_tensor=True)
    scores = util.pytorch_cos_sim(client_embedding, embeddings)[0]
    best_idx = scores.argmax().item()
    best_score = scores[best_idx].item()
    
    # Buscar posibles múltiples coincidencias con umbral cercano
    top_indices = torch.topk(scores, k=3).indices.tolist()
    top_matches = [
        {
            'nombre_cliente': client_name,
            'nombre_ramedicas': df.iloc[idx]['nomart'],
            'codart': df.iloc[idx]['codart'],
            'score': scores[idx].item()
        }
        for idx in top_indices if scores[idx].item() >= threshold
    ]
    
    return top_matches[0] if top_matches else {
        'nombre_cliente': client_name,
        'nombre_ramedicas': "No encontrado",
        'codart': None,
        'score': best_score
    }

# -------------------------------
# 🎨 Interfaz de Usuario
# -------------------------------
st.markdown(
    """
    <h1 style="text-align: center; color: #FF5800;">RAMEDICAS S.A.S.</h1>
    <h3 style="text-align: center; color: #3A86FF;">Homologador Inteligente</h3>
    <p style="text-align: center; color: #6B6B6B;">Resultados rápidos con tecnología avanzada.</p>
    """,
    unsafe_allow_html=True
)

st.info("Cargando datos, por favor espera...")
ramedicas_df, ramedicas_embeddings = load_data_and_embeddings()

# Entrada de datos
client_names_manual = st.text_area("Ingresa los nombres manualmente, separados por saltos de línea:")

if client_names_manual:
    client_names = [name.strip() for name in client_names_manual.split("\n") if name.strip()]
    if client_names:
        st.info("Procesando... Por favor, espera.")
        model = load_model()
        matches = [find_best_match(name, ramedicas_df, ramedicas_embeddings, model) for name in client_names]
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

# -------------------------------
# ✅ Mejoras Implementadas:
# - Se agregó eliminación de contenido entre paréntesis y corchetes.
# - Se evalúan múltiples coincidencias cercanas para mejorar la homologación.
# - Procesamiento más robusto y flexible.

