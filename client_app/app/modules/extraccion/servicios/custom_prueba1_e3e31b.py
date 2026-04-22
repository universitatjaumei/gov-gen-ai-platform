import pdfplumber
import re
import pandas as pd

# Se ha seleccionado 'pdfplumber' por su capacidad superior para reconstruir la estructura visual
# del texto y las tablas en documentos tipo formulario de la administración pública, lo que
# facilita la captura de campos con etiquetas repetidas (como en los indicadores de personal)
# y bloques de texto multilínea (resúmenes e IAGI).

def extraer_datos(filename):
    text_full = ""
    with pdfplumber.open(filename) as pdf:
        for page in pdf.pages:
            text_full += page.extract_text() + "\n"

    # Diccionario para almacenar resultados
    data = {}

    # 1. Campos simples con Regex
    def buscar(pattern, text, flags=0):
        match = re.search(pattern, text, flags)
        return match.group(1).strip() if match else ""

    data['Entidad Solicitante'] = buscar(r"Entidad:\s*(.*)", text_full)
    data['Representante Legal'] = buscar(r"Representante Legal:\s*(.*)", text_full)
    data['Acrónimo del Proyecto'] = buscar(r"Acrónimo:\s*(.*)", text_full)
    data['Palabras Clave'] = buscar(r"Palabras clave:\s*([\s\S]*?)(?=Key words|¿Considera)", text_full)
    data['Resumen del Proyecto'] = buscar(r"Resumen:\s*([\s\S]*?)(?=Summary:)", text_full)
    
    # IAGI: Captura el bloque después de la descripción de la pregunta hasta el inicio de la siguiente pregunta
    iagi_pattern = r"impacto social y económico de los mismos\.\s*([\s\S]*?)(?=¿La entidad solicitante dispone)"
    data['Integración del análisis de género (IAGI)'] = buscar(iagi_pattern, text_full)
    
    data['Plan de Igualdad (Enlace)'] = buscar(r"enlace al documento en la página web:\s*(https?://[^\s]+)", text_full)
    
    # Resumen CV IP1: Se encuentra en la página 9 (usualmente termina al pie de página o inicio de IP2)
    cv_pattern = r"Resumen del CV:\s*([\s\S]*?)(?=\d{2}/\d{2}/\d{4}|7\. Investigador/a Principal 2)"
    data['Resumen CV IP1'] = buscar(cv_pattern, text_full)

    # 2. Indicadores de Personal (Requiere segmentación porque las preguntas son idénticas para H/M)
    # Segmento Hombres
    bloque_hombres = buscar(r"(HOMBRES[\s\S]*?)(?=MUJERES)", text_full)
    data['Total Investigadores Hombres'] = buscar(r"¿Cuántos investigadores\?\s*(\d+)", bloque_hombres)
    data['Hombres Doctores'] = buscar(r"¿Cuántos de estos son DOCTORES\?\s*(\d+)", bloque_hombres)

    # Segmento Mujeres
    bloque_mujeres = buscar(r"(MUJERES[\s\S]*?)(?=ACTIVIDADES)", text_full)
    data['Total Investigadoras Mujeres'] = buscar(r"¿Cuántas investigadoras\?\s*(\d+)", bloque_mujeres)
    data['Mujeres Doctoras'] = buscar(r"¿Cuántas de estas son DOCTORAS\?\s*(\d+)", bloque_mujeres)

    # 3. Otros Indicadores
    data['Tesis en marcha'] = buscar(r"Número de tesis doctorales en marcha relacionadas con el proyecto\s*(\d+)", text_full)
    data['Publicaciones Revistas Indexadas'] = buscar(r"Número de publicaciones en revistas indexadas\s*(\d+)", text_full)
    data['Publicaciones Congresos Internacionales'] = buscar(r"Número de publicaciones CONGRESOS INTERNACIONALES\s*(\d+)", text_full)
    
    # Referencia Administrativa (tomada de cualquier página)
    data['Referencia Administrativa'] = buscar(r"Referencia administrativa:\s*([\w-]+)", text_full)

    # Limpieza final de saltos de línea innecesarios en campos largos
    campos_largos = ['Palabras Clave', 'Resumen del Proyecto', 'Integración del análisis de género (IAGI)', 'Resumen CV IP1']
    for campo in campos_largos:
        if campo in data:
            data[campo] = re.sub(r'\s+', ' ', data[campo]).strip()

    # Guardado de Resultado
    # Guardado de Resultado
    # df = pd.DataFrame([data])
    # df.to_excel('resultado.xlsx', index=False) # ❌ prohibido por seguridad (AST)
    
    return data

if __name__ == "__main__":
    # El entorno garantiza que el archivo está en el directorio local
    # Se asume un nombre genérico o el detectado en el flujo si fuera necesario
    extraer_datos('documento.pdf')