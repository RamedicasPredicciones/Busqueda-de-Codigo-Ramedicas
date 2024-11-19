import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st

# Función para preprocesar texto
def preprocess_text(text):
    text = text.lower()
    text = text.replace("+", " ")
    return text

# Función para buscar coincidencias
def find_best_match(client_name, ramedicas_df, vectorizer):
    client_name_vector = vectorizer.transform([client_name])
    ramedicas_vectors = vectorizer.transform(ramedicas_df['nomart'])
    
    similarities = cosine_similarity(client_name_vector, ramedicas_vectors).flatten()
    best_index = similarities.argmax()
    best_score = similarities[best_index]
    return ramedicas_df.iloc[best_index], best_score

# Función para homologar nombres
def homologar_nombres_advanced(client_names_df, ramedicas_df):
    ramedicas_df['nomart_processed'] = ramedicas_df['nomart'].apply(preprocess_text)
    client_names_df['nombre_processed'] = client_names_df['nombre'].apply(preprocess_text)
    
    vectorizer = TfidfVectorizer(analyzer='word')
    vectorizer.fit(pd.concat([ramedicas_df['nomart_processed'], client_names_df['nombre_processed']]))
    
    feedback = pd.DataFrame(columns=[
        'nombre_cliente', 'nombre_ramedicas', 'codart', 'score',
        'coincidencias_clave', 'terminos_faltantes'
    ])
    
    for index, row in client_names_df.iterrows():
        client_name = row['nombre_processed']
        client_numbers = set(filter(str.isdigit, client_name.split()))
        
        match_row, score = find_best_match(client_name, ramedicas_df, vectorizer)
        match_numbers = set(filter(str.isdigit, match_row['nomart_processed'].split()))
        equivalent_count = len(client_numbers.intersection(match_numbers))
        
        new_row = pd.DataFrame([{
            'nombre_cliente': row['nombre'],
            'nombre_ramedicas': match_row['nomart'],
            'codart': match_row['codart'],
            'score': score,
            'coincidencias_clave': ", ".join(client_numbers.intersection(match_numbers)),
            'terminos_faltantes': None if equivalent_count > 0 else "Términos principales no coinciden"
        }])
        
        feedback = pd.concat([feedback, new_row], ignore_index=True)
    
    return feedback

# App Streamlit
st.title("Búsqueda de códigos Ramedicas")

uploaded_client_file = st.file_uploader("Sube el archivo de nombres del cliente (CSV)", type=["csv"])
uploaded_ramedicas_file = st.file_uploader("Sube la base de datos Ramedicas (CSV)", type=["csv"])

if uploaded_client_file and uploaded_ramedicas_file:
    client_names_df = pd.read_csv(uploaded_client_file)
    ramedicas_df = pd.read_csv(uploaded_ramedicas_file)
    
    if 'nombre' not in client_names_df.columns or 'nomart' not in ramedicas_df.columns:
        st.error("Archivos incorrectos. Asegúrate de incluir las columnas 'nombre' en el archivo del cliente y 'nomart' en la base de datos.")
    else:
        feedback = homologar_nombres_advanced(client_names_df, ramedicas_df)
        st.write("Resultados de la homologación:")
        st.dataframe(feedback)
        
        # Descarga de resultados
        csv = feedback.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar resultados",
            data=csv,
            file_name="homologacion_resultados.csv",
            mime="text/csv",
        )
