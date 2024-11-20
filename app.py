import streamlit as st
import pandas as pd
from io import BytesIO
from rapidfuzz import fuzz, process

# Cargar datos de Ramedicas desde Google Drive
@st.cache_data
def load_ramedicas_data():
    ramedicas_url = (
        "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    )
    ramedicas_df = pd.read_excel(ramedicas_url, sheet_name="Hoja1")
    return ramedicas_df[['codart', 'nomart']]

# Preprocesar nombres
def preprocess_name(name):
    replacements = {
        "(": "",
        ")": "",
        "+": " ",
        "/": " ",
        "-": " ",
        ",": "",
        ";": "",
        ".": "",
        "mg": " mg",
        "ml": " ml",
        "capsula": " tableta",  # Unificar terminología
        "tablet": " tableta",
        "tableta": " tableta",
        "parches": " parche",
        "parche": " parche"
    }
    for old, new in replacements.items():
        name = name.lower().replace(old, new)
    stopwords = {"de", "el", "la", "los", "las", "un", "una", "y", "en", "por"}
    words = [word for word in name.split() if word not in stopwords]
    return " ".join(sorted(words))  # Ordenar alfabéticamente para mejorar la comparación

# Buscar la mejor coincidencia
def find_best_match(client_name, ramedicas_df):
    client_name_processed = preprocess_name(client_name)
    ramedicas_df['processed_nomart'] = ramedicas_df['nomart'].apply(preprocess_name)

    # Buscar coincidencia exacta primero
    if client_name_processed in ramedicas_df['processed_nomart'].values:
        exact_match = ramedicas_df[ramedicas_df['processed_nomart'] == client_name_processed].iloc[0]
        return {
            'nombre_cliente': client_name,
            'nombre_ramedicas': exact_match['nomart'],
            'codart': exact_match['codart'],
            'score': 100
        }

    # Separar palabras del nombre del cliente para buscar todos los términos
    client_terms = set(client_name_processed.split())

    # Buscar mejores coincidencias con `process.extract`
    matches = process.extract(
        client_name_processed,
        ramedicas_df['processed_nomart'],
        scorer=fuzz.token_set_ratio,
        limit=10  # Expandir el número de posibles coincidencias
    )

    best_match = None
    highest_score = 0

    for match, score, idx in matches:
        candidate_row = ramedicas_df.iloc[idx]
        candidate_terms = set(match.split())

        # Verificar que todos los términos del cliente estén en el candidato
        if client_terms.issubset(candidate_terms):
            if score > highest_score:
                highest_score = score
                best_match = {
                    'nombre_cliente': client_name,
                    'nombre_ramedicas': candidate_row['nomart'],
                    'codart': candidate_row['codart'],
                    'score': score
                }

    # Si no hay coincidencias completas, devolver la mejor aproximación
    if not best_match and matches:
        best_match = {
            'nombre_cliente': client_name,
            'nombre_ramedicas': matches[0][0],
            'codart': ramedicas_df.iloc[matches[0][2]]['codart'],
            'score': matches[0][1]
        }

    return best_match

# Interfaz de Streamlit
st.title("Homologador de Productos - Ramedicas")

if st.button("Actualizar base de datos"):
    st.cache_data.clear()

uploaded_file = st.file_uploader("Sube tu archivo con los nombres de los clientes", type="xlsx")

if uploaded_file:
    client_names_df = pd.read_excel(uploaded_file)
    if 'nombre' not in client_names_df.columns:
        st.error("El archivo debe contener una columna llamada 'nombre'.")
    else:
        ramedicas_df = load_ramedicas_data()
        results = []
        for client_name in client_names_df['nombre']:
            match = find_best_match(client_name, ramedicas_df)
            if match:
                results.append(match)
            else:
                results.append({
                    'nombre_cliente': client_name,
                    'nombre_ramedicas': None,
                    'codart': None,
                    'score': 0
                })

        results_df = pd.DataFrame(results)
        st.write("Resultados de homologación:")
        st.dataframe(results_df)

        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Homologación")
            return output.getvalue()

        st.download_button(
            label="Descargar archivo con resultados",
            data=to_excel(results_df),
            file_name="homologacion_productos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
