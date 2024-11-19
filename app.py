import gdown
import pandas as pd
from rapidfuzz import fuzz

# Función para descargar el archivo de Google Drive
def descargar_archivo_google_drive(link_drive, output_path):
    gdown.download(link_drive, output_path, quiet=False)

# Función para limpiar los nombres y estandarizarlos, eliminando detalles innecesarios
def preprocess_name(name):
    # Limpiar y estandarizar el nombre de los productos
    name = name.lower()
    name = name.replace("(", "").replace(")", "").replace("+", "").replace("/", " ").replace("-", " ").replace(",", "").replace(".", "")
    # Eliminar detalles adicionales del empaque, envase, etc.
    stopwords = ['blister', 'pvc', 'aluminio', 'caixa', 'recubiertas', 'tabletas', 'ampolla', 'por', 'empaquetadas']
    name = ' '.join([word for word in name.split() if word not in stopwords])
    return name

# Función para homologar nombres con coincidencia flexible
def homologar_nombres_flexibles(client_names_df, ramedicas_df):
    # Preprocesar los nombres de los productos en Ramedicas (solo minúsculas y limpieza de caracteres)
    ramedicas_df['processed_nomart'] = ramedicas_df['nomart'].apply(preprocess_name)

    # Preprocesar los nombres de los productos de clientes
    client_names_df['processed_nombre_cliente'] = client_names_df['nombre'].apply(preprocess_name)

    homologation_results = []

    # Buscar coincidencias flexibles
    for client_name, processed_client_name in zip(client_names_df['nombre'], client_names_df['processed_nombre_cliente']):
        best_match = None
        highest_score = 0
        
        # Buscar coincidencias flexibles usando fuzzy matching
        for idx, row in ramedicas_df.iterrows():
            processed_nomart = row['processed_nomart']
            score = fuzz.token_sort_ratio(processed_client_name, processed_nomart)  # Utilizamos token_sort_ratio para mayor flexibilidad

            # Aplicar un umbral de puntuación para coincidencias relevantes
            if score > highest_score and score > 80:  # Puedes ajustar este umbral
                highest_score = score
                best_match = {
                    'nombre_cliente': client_name,
                    'nombre_ramedicas': row['nomart'],
                    'codart': row['codart'],
                    'score': score
                }

        # Si no hay un buen match, dejar en blanco
        if not best_match:
            best_match = {
                'nombre_cliente': client_name,
                'nombre_ramedicas': None,
                'codart': None,
                'score': highest_score
            }

        homologation_results.append(best_match)

    homologation_df = pd.DataFrame(homologation_results)
    return homologation_df

# Paso 1: Descargar los archivos desde Google Drive (si es necesario)
link_drive = 'enlace_a_tu_archivo_de_google_drive'  # Reemplaza con tu enlace de Google Drive
output_path = 'archivo_descargado.xlsx'  # Ruta de salida donde se guardará el archivo descargado
descargar_archivo_google_drive(link_drive, output_path)

# Paso 2: Leer los archivos descargados en DataFrame (esto depende de la estructura de tu archivo)
# Supongamos que el archivo contiene columnas 'nombre' para el cliente y 'nomart' para los productos de Ramedicas

# Leer los datos de ejemplo
# Datos de ejemplo para el cliente
client_names_data = {
    'nombre': [
        'SULFATO FERROSO TABLETAS RECUBIERTAS 300MG BLISTER PVC / ALUMINIO POR 10 TABLETAS EMPACADAS EN CAJA PLEGABLE POR 100 TABLETAS RECUBIERTAS',
        'SULFATO FERROSO 300 MG TABLETA RECUBIERTA'
    ]
}
client_names_df = pd.DataFrame(client_names_data)

# Leer el archivo descargado (esto debe ajustarse a la estructura de tu archivo)
ramedicas_df = pd.read_excel(output_path)

# Homologar los nombres
result_df = homologar_nombres_flexibles(client_names_df, ramedicas_df)

# Mostrar los resultados
print(result_df)
