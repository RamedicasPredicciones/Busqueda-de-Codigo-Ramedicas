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
    return ramedicas_df[['codart', 'nomart', 'n_comercial']]

# Función para buscar el mejor nombre
def find_best_match(client_name, ramedicas_df):
    # Intentar encontrar una coincidencia exacta en 'nomart'
    exact_match = ramedicas_df[ramedicas_df['nomart'].str.contains(client_name, case=False, na=False)]
    
    if not exact_match.empty:
        exact_match = exact_match.iloc[0]  # Tomar el primer resultado que coincida
        return {
            'nombre_cliente': client_name,
            'nombre_ramedicas': exact_match['nomart'],
            'codart': exact_match['codart'],
            'score': 100
        }

    # Si no se encuentra en 'nomart', buscar en 'n_comercial'
    exact_match_comercial = ramedicas_df[ramedicas_df['n_comercial'].str.contains(client_name, case=False, na=False)]
    if not exact_match_comercial.empty:
        exact_match_comercial = exact_match_comercial.iloc[0]  # Tomar el primer resultado
        return {
            'nombre_cliente': client_name,
            'nombre_ramedicas': exact_match_comercial['nomart'],
            'codart': exact_match_comercial['codart'],
            'score': 100
        }
    
    # Si no se encuentra en ninguno, buscar la mejor coincidencia aproximada en 'n_comercial'
    matches = process.extract(client_name, ramedicas_df['n_comercial'], scorer=fuzz.token_sort_ratio, limit=5)
    
    best_match = None
    highest_score = 0
    for match, score, idx in matches:
        if score > highest_score:
            highest_score = score
            best_match = ramedicas_df.iloc[idx]
    
    if best_match:
        return {
            'nombre_cliente': client_name,
            'nombre_ramedicas': best_match['nomart'],
            'codart': best_match['codart'],
            'score': highest_score
        }
    
    # Si no hay coincidencia, devolver None
    return {
        'nombre_cliente': client_name,
        'nombre_ramedicas': None,
        'codart': None,
        'score': 0
    }

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
            results.append(match)

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

