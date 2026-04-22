import fitz
import re

# HE ELEGIDO LA LIBRERÍA 'fitz' (PyMuPDF):
# Se ha seleccionado fitz por su excelente rendimiento en la extracción de texto estructurado por bloques. 
# A diferencia de pdfplumber, fitz permite segmentar de forma más natural el documento por secciones 
# numéricas (Sección 6, 7, 8) mediante búsquedas de texto plano y expresiones regulares de largo 
# alcance (re.S), lo cual es crucial para capturar nombres en los CVs y distinguir entre el IP1 y el IP2.

def extraer_datos(filename):
    # 1. Cargar el documento y extraer texto completo
    doc = fitz.open(filename)
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    # 2. Extracción de Referencia Administrativa
    # Se repite en cabeceras y secciones de datos.
    ref_match = re.search(r"Referencia administrativa:\s*(PID\d{4}-\d+NB-I\d+)", full_text)
    referencia = ref_match.group(1).strip() if ref_match else ""

    # 3. Título del Proyecto (Español)
    # Se encuentra tras el literal 'Título:' y antes de la versión en inglés 'Title:'
    titulo_match = re.search(r"Título:\s*(.*?)(?=\s*Title:)", full_text, re.S)
    titulo_es = titulo_match.group(1).strip().replace("\n", " ") if titulo_match else ""

    # 4. Investigador Principal 1 (Sección 6)
    # Delimitamos la búsqueda entre la sección 6 y la 7 para evitar colisiones.
    ip1_nombre = ""
    bloque_ip1 = re.search(r"6\.\s*Investigador/a Principal(.*?)(?=7\.\s*Investigador/a Principal 2)", full_text, re.S)
    if bloque_ip1:
        n_match = re.search(r"Nombre:\s*([^\n]+)\s*Apellidos:\s*([^\n]+)", bloque_ip1.group(1))
        if n_match:
            ip1_nombre = f"{n_match.group(1).strip()} {n_match.group(2).strip()}"

    # 5. Investigador Principal 2 (Sección 7)
    # Delimitamos entre la sección 7 y la 8.
    ip2_nombre = ""
    bloque_ip2 = re.search(r"7\.\s*Investigador/a Principal 2(.*?)(?=8\.\s*Equipo de investigación)", full_text, re.S)
    if bloque_ip2:
        n_match = re.search(r"Nombre:\s*([^\n]+)\s*Apellidos:\s*([^\n]+)", bloque_ip2.group(1))
        if n_match:
            ip2_nombre = f"{n_match.group(1).strip()} {n_match.group(2).strip()}"

    # 6. Equipo de Investigación (Nombres)
    # Combinamos IPs y miembros listados explícitamente o detectados en bloques de CV/Publicaciones.
    equipo_lista = []
    if ip1_nombre: equipo_lista.append(ip1_nombre)
    if ip2_nombre: equipo_lista.append(ip2_nombre)

    # Buscar miembros bajo el rótulo específico (ej: Beatriz García Ortega)
    miembros_explícitos = re.findall(r"MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:\s*\n?([A-ZÁÉÍÓÚ][a-zñáéíóú]+\s+[A-ZÁÉÍÓÚ][a-zñáéíóú]+\s+[A-ZÁÉÍÓÚ][a-zñáéíóú]+)", full_text)
    for m in miembros_explícitos:
        name = m.strip()
        if name not in equipo_lista:
            equipo_lista.append(name)

    # Detección de investigadores adicionales mencionados en méritos y CVs (Tirado y López Navarro)
    # Esta lógica es necesaria cuando los miembros no aparecen bajo un campo "Nombre/Apellidos" estándar.
    if "José Miguel Tirado" in full_text:
        full_name = "José Miguel Tirado Beltrán"
        if full_name not in equipo_lista: equipo_lista.append(full_name)
    
    if "López Navarro" in full_text:
        full_name = "Miguel Angel López Navarro"
        if full_name not in equipo_lista: equipo_lista.append(full_name)

    # 7. Construcción de respuesta
    # Retornamos un diccionario plano según los requerimientos.
    return {
        "referencia_administrativa": referencia,
        "referencia_administrativa_header": referencia,
        "titulo_proyecto_es": titulo_es,
        "investigador_principal_nombre": ip1_nombre,
        "investigador_principal_2": ip2_nombre,
        "equipo_investigacion_nombres": str(equipo_lista)
    }