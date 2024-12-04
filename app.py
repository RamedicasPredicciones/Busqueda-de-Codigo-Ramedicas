import streamlit as st
import pandas as pd
from io import BytesIO
from rapidfuzz import process

# Función para cargar datos
@st.cache_data
def load_ramedicas_data():
    """Carga los datos de Ramedicas."""
    ramedicas_url = (
        "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    )
    try:
        ramedicas_df = pd.read_excel(ramedicas_url, sheet_name="Hoja1")
        return ramedicas_df[['codart', 'nomart']]
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame()

# Preprocesar nombres
def preprocess_name(name):
    """Preprocesa los nombres para una comparación más precisa."""
    name = str(name).lower()
    for char in ["+", "/", "-", ",", "(", ")", "."]:
        name = name.replace(char, " ")
    return " ".join(name.split())

# Buscar la mejor coincidencia
def find_best_match(client_name, ramedicas_df, threshold=70):
    """
    Encuentra la mejor coincidencia para un nombre de cliente en la base de datos de Ramedicas.
    Devuelve un diccionario con los resultados.
    """
    client_name = preprocess_name(client_name)
    ramedicas_df['nomart_processed'] = ramedicas_df['nomart'].apply(preprocess_name)

    # Usar rapidfuzz para buscar la mejor coincidencia
    match = process.extractOne(client_name, ramedicas_df['nomart_processed'], score_cutoff=threshold)
    if match:
        idx = ramedicas_df.index[ramedicas_df['nomart_processed'] == match[0]].tolist()[0]
        return {
            'nombre_cliente': client_name,
            'nombre_ramedicas': ramedicas_df.loc[idx, 'nomart'],
            'codart': ramedicas_df.loc[idx, 'codart'],
            'score': match[1]
        }
    else:
        return {
            'nombre_cliente': client_name,
            'nombre_ramedicas': "No encontrado",
            'codart': None,
            'score': 0
        }

# Convertir DataFrame a archivo Excel
def to_excel(df):
    """Convierte un DataFrame a un archivo Excel."""
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
        Homologador Inteligente de Productos
    </h3>
    <p style="text-align: center; font-family: Arial, sans-serif; color: #6B6B6B;">
        Busca coincidencias de manera más eficiente utilizando tecnología avanzada.
    </p>
    """,
    unsafe_allow_html=True
)

ramedicas_df = load_ramedicas_data()

# Validar si los datos de Ramedicas están cargados
if ramedicas_df.empty:
    st.error("No se pudieron cargar los datos de RAMEDICAS. Por favor, verifica la conexión.")
else:
    # Procesar archivo subido
    uploaded_file = st.file_uploader("Sube tu archivo de Excel con la columna 'nombre':", type="xlsx")

    # Procesar nombres manualmente
    client_names_manual = st.text_area("Ingresa los nombres de los productos, separados por saltos de línea:")

    if uploaded_file or client_names_manual:
        st.info("Procesando los datos, por favor espera...")

        client_names = []
        if uploaded_file:
            client_names_df = pd.read_excel(uploaded_file)
            if 'nombre' not in client_names_df.columns:
                st.error("El archivo debe tener una columna llamada 'nombre'.")
            else:
                client_names = client_names_df['nombre'].tolist()

        if client_names_manual:
            client_names.extend(client_names_manual.split("\n"))

        # Filtrar nombres válidos
        client_names = [name.strip() for name in client_names if name.strip()]

        # Calcular coincidencias
        matches = [find_best_match(name, ramedicas_df) for name in client_names]

        results_df = pd.DataFrame(matches)
        st.dataframe(results_df)

        # Descargar resultados
        if not results_df.empty:
            excel_data = to_excel(results_df)
            st.download_button(
                label="📥 Descargar resultados en Excel",
                data=excel_data,
                file_name="homologacion_resultados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("Por favor sube un archivo o ingresa nombres manualmente.")
