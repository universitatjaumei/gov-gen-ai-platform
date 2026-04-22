import fitz
import re

# Elegimos la librería 'fitz' (PyMuPDF) debido a su gran velocidad de procesamiento 
# y a su excelente capacidad para extraer texto plano manteniendo un flujo lineal, 
# lo cual es ideal para aplicar expresiones regulares sobre documentos extensos 
# de múltiples páginas donde la información (como los miembros del equipo) 
# puede estar distribuida de forma repetitiva bajo encabezados específicos.

def extraer_datos(filename):
    # Abrir el documento con fitz
    doc = fitz.open(filename)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    
    # 1. Extracción de Referencia Administrativa
    # Buscamos el patrón PID seguido de año y código, capturando la primera coincidencia
    ref_match = re.search(r"Referencia administrativa:\s*(PID\d{4}-[\w-]+)", full_text)
    referencia = ref_match.group(1) if ref_match else ""

    # 2. Extracción del Título del proyecto
    # El título se encuentra entre el campo 'Título:' y el siguiente campo 'Title:' o 'Acrónimo:'
    title_match = re.search(r"Título:\s*(.*?)(?=\n\s*Title:|\n\s*Acrónimo:)", full_text, re.DOTALL)
    titulo = ""
    if title_match:
        # Limpiamos saltos de línea y espacios extra
        titulo = " ".join(title_match.group(1).split()).strip()

    # 3. Extracción de IP 1
    # Buscamos dentro de la sección "6. Investigador/a Principal"
    ip1_name = ""
    section_ip1 = re.search(r"6\.\s+Investigador/a Principal.*?Datos personales(.*?)(?=7\.\s+Investigador/a Principal 2)", full_text, re.DOTALL)
    if section_ip1:
        text_ip1 = section_ip1.group(1)
        # Capturamos Nombre y Apellidos. Los PDFs suelen tener múltiples espacios entre etiquetas.
        n_match = re.search(r"Nombre:\s+(.*?)\s+Apellidos:\s+(.*?)(?=\n|Correo)", text_ip1)
        if n_match:
            # Unimos nombre y apellidos limpiando espacios internos
            nombre = " ".join(n_match.group(1).split())
            apellidos = " ".join(n_match.group(2).split())
            ip1_name = f"{nombre} {apellidos}".strip()

    # 4. Extracción de IP 2
    # Buscamos dentro de la sección "7. Investigador/a Principal 2"
    ip2_name = ""
    section_ip2 = re.search(r"7\.\s+Investigador/a Principal 2.*?Datos personales(.*?)(?=8\.\s+Equipo de investigación)", full_text, re.DOTALL)
    if section_ip2:
        text_ip2 = section_ip2.group(1)
        n_match = re.search(r"Nombre:\s+(.*?)\s+Apellidos\s+(.*?)(?=\n|Correo)", text_ip2)
        if n_match:
            nombre = " ".join(n_match.group(1).split())
            apellidos = " ".join(n_match.group(2).split())
            ip2_name = f"{nombre} {apellidos}".strip()

    # 5. Nombre y apellidos del equipo de investigación
    # Buscamos todas las ocurrencias de "MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:" 
    # y extraemos el nombre que aparece inmediatamente después.
    team_members = []
    # El patrón busca la etiqueta y captura la siguiente línea que contiene el nombre
    matches = re.finditer(r"MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:\s*\n?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ].*)", full_text)
    for m in matches:
        # Limpiamos el nombre capturado (solo la primera línea tras la etiqueta)
        raw_name = m.group(1).split('\n')[0].strip()
        # Normalizamos espacios
        clean_name = " ".join(raw_name.split())
        if clean_name and clean_name not in team_members:
            team_members.append(clean_name)

    # El IP 2 a veces aparece también en la lista del equipo por error de OCR o estructura, 
    # pero según el objetivo, IP 1 e IP 2 van en sus campos y el equipo en el suyo.
    
    # Cerramos el documento
    doc.close()

    # Retorno de resultados siguiendo la estructura obligatoria
    return {
        "Referencia administrativa": referencia,
        "Título del proyecto": titulo,
        "Nombre y apellidos IP 1": ip1_name,
        "Nombre y apellidos IP 2": ip2_name,
        "Nombre y apellidos del equipo de investigación": team_members
    }