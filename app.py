import streamlit as st
import pandas as pd
from io import BytesIO
from rapidfuzz import fuzz, process

# Cargar datos de Ramedicas desde Google Drive
@st.cache_data  # Cachear los datos para evitar recargarlos en cada ejecución
def load_ramedicas_data():
    # URL del archivo Excel en Google Drive
    ramedicas_url = (
        "https://docs.google.com/spreadsheets/d/1Y9SgliayP_J5Vi2SdtZmGxKWwf1iY7ma/export?format=xlsx&sheet=Hoja1"
    )
    # Leer el archivo Excel desde la URL
    ramedicas_df = pd.read_excel(ramedicas_url, sheet_name="Hoja1")
    # Retornar solo las columnas relevantes
    return ramedicas_df[['codart', 'nomart']]

# Preprocesar nombres para una mejor comparación
def preprocess_name(name):
    # Diccionario de reemplazos para limpiar y unificar los nombres
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
        "capsula": " capsulas",  # Unificar terminología
        "tablet": " tableta",
        "tableta": " tableta",
        "parches": " parche",
        "parche": " parche"
    }
    # Aplicar los reemplazos al nombre
    for old, new in replacements.items():
        name = name.lower().replace(old, new)
    
    # Lista de palabras vacías que se eliminarán
    stopwords = {"de", "el", "la", "los", "las", "un", "una", "y", "en", "por"}
    # Dividir el nombre en palabras y eliminar las palabras vacías
    words = [word for word in name.split() if word not in stopwords]
    # Devolver el nombre procesado, ordenado alfabéticamente para una comparación más confiable
    return " ".join(sorted(words))

# Buscar la mejor coincidencia entre el nombre del cliente y los productos de Ramedicas
def find_best_match(client_name, ramedicas_df):
    # Preprocesar el nombre del cliente
    client_name_processed = preprocess_name(client_name)
    # Aplicar el preprocesamiento a todos los productos de Ramedicas
    ramedicas_df['processed_nomart'] = ramedicas_df['nomart'].apply(preprocess_name)

    # Buscar coincidencia exacta primero
    if client_name_processed in ramedicas_df['processed_nomart'].values:
        exact_match = ramedicas_df[ramedicas_df['processed_nomart'] == client_name_processed].iloc[0]
        return {
            'nombre_cliente': client_name,
            'nombre_ramedicas': exact_match['nomart'],
            'codart': exact_match['codart'],
            'score': 100  # Puntaje 100 para coincidencia exacta
        }

    # Separar palabras del nombre del cliente para buscar todos los términos
    client_terms = set(client_name_processed.split())

    # Buscar las mejores coincidencias utilizando RapidFuzz (algoritmo de fuzzy matching)
    matches = process.extract(
        client_name_processed,
        ramedicas_df['processed_nomart'],
        scorer=fuzz.token_set_ratio,  # Usar el método de puntuación token_set_ratio
        limit=10  # Limitar el número de coincidencias a 10
    )

    best_match = None
    highest_score = 0

    # Iterar sobre las coincidencias encontradas
    for match, score, idx in matches:
        candidate_row = ramedicas_df.iloc[idx]  # Obtener la fila candidata
        candidate_terms = set(match.split())  # Separar las palabras de la coincidencia candidata

        # Verificar que todos los términos del cliente estén presentes en la coincidencia
        if client_terms.issubset(candidate_terms):
            if score > highest_score:  # Si la puntuación es mejor que la anterior, se actualiza
                highest_score = score
                best_match = {
                    'nombre_cliente': client_name,
                    'nombre_ramedicas': candidate_row['nomart'],
                    'codart': candidate_row['codart'],
                    'score': score
                }

    # Si no hay coincidencias completas, se devuelve la mejor aproximación
    if not best_match and matches:
        best_match = {
            'nombre_cliente': client_name,
            'nombre_ramedicas': matches[0][0],
            'codart': ramedicas_df.iloc[matches[0][2]]['codart'],
            'score': matches[0][1]  # Puntuación de la mejor coincidencia
        }

    return best_match

# Interfaz de Streamlit
st.title("Homologador de Productos - Ramedicas")  # El título de la aplicación

# Opción para actualizar la base de datos y limpiar el caché
if st.button("Actualizar base de datos"):
    st.cache_data.clear()  # Limpiar el caché para cargar los datos de nuevo

# Opción para ingresar un nombre de cliente manualmente
client_name_manual = st.text_input("Ingresa el nombre del cliente (si solo deseas buscar uno):")

# Opción para subir un archivo con los nombres de los clientes
uploaded_file = st.file_uploader("O sube tu archivo con los nombres de los clientes", type="xlsx")

# Procesar si el usuario ha ingresado un nombre manual
if client_name_manual:
    # Cargar los datos de productos de Ramedicas
    ramedicas_df = load_ramedicas_data()

    # Buscar la mejor coincidencia
    match = find_best_match(client_name_manual, ramedicas_df)

    # Mostrar los resultados
    if match:
        st.write(f"**Nombre cliente**: {match['nombre_cliente']}")
        st.write(f"**Nombre Ramedicas**: {match['nombre_ramedicas']}")
        st.write(f"**Código Artículo**: {match['codart']}")
        st.write(f"**Score**: {match['score']}")

        # Crear el DataFrame para la descarga
        results_df = pd.DataFrame([match])
        st.download_button(
            label="Descargar archivo con resultado",
            data=to_excel(results_df),
            file_name="resultado_homologacion.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Procesar si el usuario sube un archivo
if uploaded_file:
    # Leer el archivo subido con los nombres de los clientes
    client_names_df = pd.read_excel(uploaded_file)
    
    # Verificar si la columna 'nombre' está presente en el archivo subido
    if 'nombre' not in client_names_df.columns:
        st.error("El archivo debe contener una columna llamada 'nombre'.")
    else:
        # Cargar los datos de productos de Ramedicas
        ramedicas_df = load_ramedicas_data()
        
        # Lista para almacenar los resultados de la homologación
        results = []

        # Se crea la iteración sobre cada nombre de cliente para encontrar la mejor coincidencia
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

        # Crear un DataFrame con los resultados
        results_df = pd.DataFrame(results)
        st.write("Resultados de homologación:")
        st.dataframe(results_df)  # Mostrar los resultados en una tabla

        # Función para convertir el DataFrame a un archivo Excel
        def to_excel(df):
            output = BytesIO()  # Usamos BytesIO para manejar el archivo en memoria
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Homologación")  # Escribir el DataFrame al archivo
            return output.getvalue()

        # Botón para descargar los resultados como un archivo Excel
        st.download_button(
            label="Descargar archivo con resultados",
            data=to_excel(results_df),
            file_name="homologacion_productos.xlsx",  # Nombre del archivo de descarga
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # Tipo de archivo excel 
        )
