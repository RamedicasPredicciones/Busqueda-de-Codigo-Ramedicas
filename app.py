import streamlit as st
import pandas as pd
from io import BytesIO
from rapidfuzz import fuzz, process
import re

# Cargar datos de Ramedicas desde Google Drive
@st.cache_data
def load_ramedicas_data():
    # URL del archivo Excel en Google Drive
    ramedicas_url = (
        "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    )
    # Leer el archivo Excel desde la URL
    ramedicas_df = pd.read_excel(ramedicas_url, sheet_name="Hoja1")
    return ramedicas_df[['codart', 'nomart']]

# Preprocesar nombres para una mejor comparación
def preprocess_name(name):
    replacements = {
        "(": "", ")": "", "+": " ", "/": " ", "-": " ", ",": "", ";": "",
        ".": "", "mg": " mg", "ml": " ml", "capsula": " capsulas",
        "tablet": " tableta", "tableta": " tableta", "parches": " parche", "parche": " parche"
    }
    for old, new in replacements.items():
        name = name.lower().replace(old, new)
    stopwords = {"de", "el", "la", "los", "las", "un", "una", "y", "en", "por"}
    words = [word for word in name.split() if word not in stopwords]
    return " ".join(sorted(words))

# Dividir nombre por '+' cuando sea necesario
def split_plus_terms(name):
    if "+" in name:
        parts = name.split("+")
        return [preprocess_name(part.strip()) for part in parts]
    return [preprocess_name(name)]

# Buscar la mejor coincidencia entre el nombre del cliente y los productos de Ramedicas
def find_best_match(client_name, ramedicas_df):
    client_name_processed = preprocess_name(client_name)
    ramedicas_df['processed_nomart'] = ramedicas_df['nomart'].apply(preprocess_name)

    # Desglosar los términos cuando se usan '+'
    client_terms = split_plus_terms(client_name_processed)

    matches = []
    for client_term in client_terms:
        # Buscar coincidencias exactas primero
        exact_matches = ramedicas_df[ramedicas_df['processed_nomart'] == client_term]
        if not exact_matches.empty:
            exact_match = exact_matches.iloc[0]
            return {
                'nombre_cliente': client_name,
                'nombre_ramedicas': exact_match['nomart'],
                'codart': exact_match['codart'],
                'score': 100
            }

        # Si no hay coincidencia exacta, buscar por similitud usando fuzzy matching
        matches += process.extract(client_term, ramedicas_df['processed_nomart'], scorer=fuzz.token_set_ratio, limit=10)

    # Filtrar para evitar coincidencias incorrectas que tengan componentes adicionales
    filtered_matches = []
    for match, score, idx in matches:
        candidate_row = ramedicas_df.iloc[idx]
        # Asegurarse de que el producto encontrado no tenga componentes adicionales no mencionados
        if fuzz.ratio(client_name_processed, candidate_row['processed_nomart']) > 85:
            filtered_matches.append((match, score, idx))

    # Obtener la mejor coincidencia
    best_match = None
    highest_score = 0

    for match, score, idx in filtered_matches:
        candidate_row = ramedicas_df.iloc[idx]
        if score > highest_score:
            highest_score = score
            best_match = {
                'nombre_cliente': client_name,
                'nombre_ramedicas': candidate_row['nomart'],
                'codart': candidate_row['codart'],
                'score': score
            }

    # Si no se encuentra mejor coincidencia, devuelve la primera que se encuentre
    if not best_match and filtered_matches:
        best_match = {
            'nombre_cliente': client_name,
            'nombre_ramedicas': filtered_matches[0][0],
            'codart': ramedicas_df.iloc[filtered_matches[0][2]]['codart'],
            'score': filtered_matches[0][1]
        }

    return best_match

# Convertir DataFrame a archivo Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Homologación")
    return output.getvalue()

# Interfaz de Streamlit
st.markdown(
    """
    <h1 style="text-align: center; color: #FF5800; font-family: Arial, sans-serif;">
        RAMEDICAS S.A.S.
    </h1>
    <h3 style="text-align: center; font-family: Arial, sans-serif; color: #3A86FF;">
        Homologador de Productos por Nombre
    </h3>
    <p style="text-align: center; font-family: Arial, sans-serif; color: #6B6B6B;">
        Esta herramienta te permite buscar y consultar los códigos de productos de manera eficiente y rápida.
    </p>
    """,
    unsafe_allow_html=True
)

if st.button("Actualizar base de datos"):
    st.cache_data.clear()

# Subir archivo
uploaded_file = st.file_uploader("O sube tu archivo de excel con la columna nombres que contenga productos aquí:", type="xlsx")

# Procesar manualmente
client_names_manual = st.text_area("Ingresa los nombres de los productos que envió el cliente, separados por saltos de línea:")

ramedicas_df = load_ramedicas_data()

if uploaded_file:
    client_names_df = pd.read_excel(uploaded_file)
    if 'nombre' not in client_names_df.columns:
        st.error("El archivo debe tener una columna llamada 'nombre'.")
    else:
        client_names = client_names_df['nombre'].tolist()
        matches = []

        for client_name in client_names:
            if client_name.strip():
                match = find_best_match(client_name, ramedicas_df)
                matches.append(match)

        results_df = pd.DataFrame(matches)
        st.dataframe(results_df)

        excel_data = to_excel(results_df)
        st.download_button(
            label="📥 Descargar resultados en Excel",
            data=excel_data,
            file_name="homologacion_resultados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Procesar texto manual
if client_names_manual:
    client_names = client_names_manual.split("\n")
    matches = []

    for client_name in client_names:
        if client_name.strip():
            match = find_best_match(client_name, ramedicas_df)
            matches.append(match)

    results_df = pd.DataFrame(matches)
    st.dataframe(results_df)

    excel_data = to_excel(results_df)
    st.download_button(
        label="📥 Descargar resultados en Excel",
        data=excel_data,
        file_name="homologacion_resultados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
