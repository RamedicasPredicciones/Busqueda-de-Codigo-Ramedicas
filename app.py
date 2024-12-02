import streamlit as st
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from io import BytesIO

@st.cache_data
def load_ramedicas_data():
    ramedicas_url = (
        "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    )
    return pd.read_excel(ramedicas_url, sheet_name="Hoja1")[['codart', 'nomart']]

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

def preprocess_name(name):
    replacements = {"(": "", ")": "", "+": " ", "/": " ", "-": " ", ",": ""}
    for old, new in replacements.items():
        name = name.lower().replace(old, new)
    return name.strip()

def find_best_match(client_name, ramedicas_df, model):
    client_name_processed = preprocess_name(client_name)
    ramedicas_df['processed_nomart'] = ramedicas_df['nomart'].apply(preprocess_name)
    
    client_embedding = model.encode([client_name_processed])
    ramedicas_embeddings = model.encode(ramedicas_df['processed_nomart'].tolist())
    
    similarities = cosine_similarity(client_embedding, ramedicas_embeddings).flatten()
    best_idx = similarities.argmax()
    best_score = similarities[best_idx]
    
    return {
        'nombre_cliente': client_name,
        'nombre_ramedicas': ramedicas_df.iloc[best_idx]['nomart'],
        'codart': ramedicas_df.iloc[best_idx]['codart'],
        'score': round(best_score * 100, 2)
    }

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Homologación")
    return output.getvalue()

# Streamlit Interface
st.title("Homologador de Productos Inteligente")
st.write("Utiliza tecnología avanzada para encontrar los códigos de productos de manera eficiente.")

model = load_model()
ramedicas_df = load_ramedicas_data()

uploaded_file = st.file_uploader("Sube un archivo con la columna 'nombre':", type="xlsx")

if uploaded_file:
    client_names_df = pd.read_excel(uploaded_file)
    if 'nombre' not in client_names_df.columns:
        st.error("El archivo debe tener una columna llamada 'nombre'.")
    else:
        client_names = client_names_df['nombre'].tolist()
        matches = [find_best_match(name, ramedicas_df, model) for name in client_names]
        results_df = pd.DataFrame(matches)
        st.dataframe(results_df)
        
        excel_data = to_excel(results_df)
        st.download_button(
            label="📥 Descargar resultados en Excel",
            data=excel_data,
            file_name="homologacion_resultados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
