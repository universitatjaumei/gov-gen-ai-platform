import fitz
import re

# Elegimos la librería 'fitz' (PyMuPDF) porque la estructura del documento del Ministerio 
# presenta etiquetas (Nombre, Apellidos, Título) y valores en un flujo de texto que 'fitz' 
# extrae de forma muy limpia, preservando la relación de vecindad entre la etiqueta y su valor, 
# lo cual es ideal para aplicar expresiones regulares precisas sin el ruido de las celdas 
# de tablas complejas que a veces confunden a otros extractores.

def extraer_datos(filename):
    # Abrir el documento
    doc = fitz.open(filename)
    full_text = ""
    
    # Extraer texto de todas las páginas para tener el contexto completo
    for page in doc:
        full_text += page.get_text()
    
    # 1. Extraer Referencia administrativa
    # Suele aparecer en el encabezado o pie de página: "Referencia administrativa: PID..."
    ref_match = re.search(r'Referencia administrativa:\s*([A-Z0-9-ñÑ]+)', full_text)
    ref_admin = ref_match.group(1) if ref_match else ""
    
    # 2. Extraer Título del proyecto
    # Se encuentra en la sección "Información proyecto" -> "Título: ..."
    titulo_match = re.search(r'Título:\s*(.*?)(?:\n|Title:)', full_text, re.DOTALL)
    titulo = ""
    if titulo_match:
        # Limpiamos saltos de línea y espacios extra
        titulo = " ".join(titulo_match.group(1).split()).strip()
    
    # 3. Extraer Investigadores Principales (IP1 e IP2)
    # Segmentamos por secciones para no confundir a los IPs con el equipo de trabajo o contacto
    ip1_name = ""
    ip1_section = re.search(r'6\.\s*Investigador/a Principal\s*(.*?)(?=7\.\s*Investigador/a Principal 2)', full_text, re.DOTALL)
    if ip1_section:
        n = re.search(r'Nombre:\s*(.*?)\s+Apellidos:?\s*(.*?)(?:\n|Correo|Fecha|Documento)', ip1_section.group(1))
        if n:
            ip1_name = " ".join(f"{n.group(1).strip()} {n.group(2).strip()}".split())

    ip2_name = ""
    ip2_section = re.search(r'7\.\s*Investigador/a Principal 2\s*(.*?)(?=8\.\s*Equipo de investigación)', full_text, re.DOTALL)
    if ip2_section:
        n = re.search(r'Nombre:\s*(.*?)\s+Apellidos:?\s*(.*?)(?:\n|Correo|Fecha|Documento)', ip2_section.group(1))
        if n:
            ip2_name = " ".join(f"{n.group(1).strip()} {n.group(2).strip()}".split())

    # 4. Nombre y apellidos del equipo de investigación
    # En este modelo de formulario, el "Equipo de Investigación" está compuesto por los IPs 
    # y los miembros detallados a partir de la sección 8.
    # Buscamos todos los bloques de "Nombre: ... Apellidos: ..." en las secciones 6, 7 y 8.
    equipo_investigacion = []
    
    # Capturamos desde la sección 6 hasta el final del documento para incluir a todos
    seccion_equipo = re.search(r'(?:6\.\s*Investigador/a Principal|8\.\s*Equipo de investigación).*', full_text, re.DOTALL)
    if seccion_equipo:
        # Buscamos el patrón repetitivo de identificación personal en el formulario
        matches = re.finditer(r'Nombre:\s*(.*?)\s+Apellidos:?\s*(.*?)(?=\n|Correo|Fecha|Tipo|País|Entidad)', seccion_equipo.group(0))
        for m in matches:
            nombre_completo = " ".join(f"{m.group(1).strip()} {m.group(2).strip()}".split())
            if nombre_completo and nombre_completo not in equipo_investigacion:
                equipo_investigacion.append(nombre_completo)
                
    # Si por alguna razón la extracción por campos falla, intentamos capturar los nombres 
    # después de la etiqueta "MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:"
    miembros_header = re.findall(r'MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:\s*\n?\s*([A-ZÁÉÍÓÚÑa-záéíóúñ\s]+?)\s*\n', full_text)
    for m in miembros_header:
        m_clean = " ".join(m.split()).strip()
        if m_clean and "Entidad" not in m_clean and m_clean not in equipo_investigacion:
            equipo_investigacion.append(m_clean)

    # 5. Construcción de respuesta
    return {
        "Referencia administrativa": ref_admin,
        "Título del proyecto": titulo,
        "Investigador/a Principal 1 (Nombre y Apellidos)": ip1_name,
        "Investigador/a Principal 2 (Nombre y Apellidos)": ip2_name,
        "Nombre y apellidos del equipo de investigación": str(equipo_investigacion)
    }