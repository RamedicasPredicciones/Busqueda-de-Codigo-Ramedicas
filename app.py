import streamlit as st
import pandas as pd
import openai
from sklearn.metrics.pairwise import cosine_similarity

# Cargar el DataFrame de Ramedicas (esto es solo un ejemplo)
def load_ramedicas_df():
    # Aquí cargarías tu DataFrame desde un archivo Excel, CSV o cualquier otro formato
    df = pd.read_csv('ramedicas_data.csv')  # Ajusta a la ubicación de tu archivo
    return df

# Función para crear los embeddings
def create_ramedicas_embeddings(df, model):
    # Genera los embeddings a partir de la columna que desees, ajusta según sea necesario
    embeddings = model.encode(df['nombre_producto'].tolist())
    return embeddings

# Cargar o crear embeddings (función cacheada)
@st.cache_data
def load_or_create_ramedicas_embeddings(df, model):
    return create_ramedicas_embeddings(df, model)

# Función para buscar coincidencias
def search_similar_products(query, df, model, embeddings):
    query_embedding = model.encode([query])
    similarities = cosine_similarity(query_embedding, embeddings)
    top_match_idx = similarities.argmax()
    return df.iloc[top_match_idx]

# Inicialización del modelo OpenAI o cualquier otro modelo de embeddings
# Si estás utilizando OpenAI o cualquier otro modelo, asegúrate de haber configurado la clave API
openai.api_key = 'tu_clave_api_aqui'

# Aquí usaremos el modelo de OpenAI o cualquier modelo que utilices para generar los embeddings
class EmbeddingModel:
    def encode(self, text_list):
        # Aquí deberías llamar a la API de OpenAI u otro modelo
        # Este es solo un ejemplo de cómo deberías estructurarlo
        return [openai.Embedding.create(input=text)['data'][0]['embedding'] for text in text_list]

# Cargar el modelo de embeddings (puedes usar otro si lo prefieres)
model = EmbeddingModel()

# Cargar el DataFrame
ramedicas_df = load_ramedicas_df()

# Crear o cargar los embeddings
ramedicas_embeddings = load_or_create_ramedicas_embeddings(ramedicas_df, model)

# Interfaz de Streamlit para la búsqueda de productos
st.title('Búsqueda de productos similares')

# Ingresar el producto de búsqueda
query = st.text_input('Ingresa el nombre del producto')

if query:
    similar_product = search_similar_products(query, ramedicas_df, model, ramedicas_embeddings)
    st.write(f"Producto más similar: {similar_product['nombre_producto']}")
    st.write(f"Descripción: {similar_product['descripcion']}")
