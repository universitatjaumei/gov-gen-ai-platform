import fitz
import re

def extraer_datos(filename):
    """
    Extrae campos específicos de documentos de solicitud de proyectos (Ministerio)
    utilizando anclas (etiquetas fijas) y expresiones regulares robustas.
    """
    doc = fitz.open(filename)
    text = ""
    for page in doc:
        # Extraemos texto manteniendo un orden lógico de bloques para evitar saltos de línea inesperados
        text += page.get_text("text", sort=True) + "\n"
    
    def clean_investigator_name(raw_name):
        """
        Limpia los nombres de los investigadores extraídos, eliminando artefactos comunes
        de la extracción de texto, como la inserción de "Apellidos" o ":" en medio del nombre.
        """
        if not raw_name:
            return ""
        # Elimina artefactos como "Apellidos", "Apellidos:" o solo ":" que separan nombre de apellidos.
        # La expresión regular busca "Apellidos" (opcionalmente seguido de ':') O solo ':'.
        # Es insensible a mayúsculas/minúsculas y maneja espaciado variable.
        cleaned_name = re.sub(r'\s*(?:Apellidos\s*:?|:)\s*', ' ', raw_name, flags=re.IGNORECASE)
        # Normaliza los espacios en blanco (convierte múltiples espacios a uno solo) y elimina los de los extremos.
        cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
        return cleaned_name

    # --- 1. Referencia administrativa ---
    # Suele aparecer en el encabezado de las páginas. 
    # Formato típico: PID2024-XXXXXX...
    ref_match = re.search(r'Referencia\s+administrativa:\s*(\S+)', text)
    referencia = ref_match.group(1).strip() if ref_match else None

    # --- 2. Título ---
    # Ubicado en la sección 2. Datos del Proyecto -> Información proyecto.
    # El anchor es "Título:" y termina antes de "Title:" (la versión en inglés).
    titulo_match = re.search(r'Información\s+proyecto\s+Título:\s*(.*?)(?=\s*Title:)', text, re.DOTALL)
    titulo = titulo_match.group(1).replace('\n', ' ').strip() if titulo_match else ""

    # --- Pre-segmentación para Investigadores (Secciones 6, 7 y 8) ---
    # Para evitar colisiones entre "Nombre:" de distintos investigadores, dividimos el texto.
    seccion_6 = ""
    seccion_7 = ""
    seccion_8 = ""
    
    # Buscamos los límites de las secciones numéricas
    s6_start = re.search(r'\n6\.\s+Investigador/a\s+Principal', text)
    s7_start = re.search(r'\n7\.\s+Investigador/a\s+Principal\s+2', text)
    s8_start = re.search(r'\n8\.\s+Equipo\s+de\s+investigación', text)
    
    if s6_start:
        end_idx = s7_start.start() if s7_start else (s8_start.start() if s8_start else len(text))
        seccion_6 = text[s6_start.start():end_idx]
        
    if s7_start:
        end_idx = s8_start.start() if s8_start else len(text)
        seccion_7 = text[s7_start.start():end_idx]
        
    if s8_start:
        seccion_8 = text[s8_start.start():]

    # --- 3. Nombre y apellidos del investigador/a principal (IP1) ---
    # En la sección 6, buscamos "Nombre:"
    ip1_match = re.search(r'Nombre:\s*(.*?)(?=\n|Correo|Fecha|NIF|$)', seccion_6, re.DOTALL)
    raw_ip1_nombre = ip1_match.group(1).strip() if ip1_match else ""
    ip1_nombre = clean_investigator_name(raw_ip1_nombre)

    # --- 4. Nombre y apellidos del investigador/a principal 2 (IP2) ---
    # En la sección 7, buscamos "Nombre:"
    ip2_match = re.search(r'Nombre:\s*(.*?)(?=\n|Correo|Fecha|NIF|$)', seccion_7, re.DOTALL)
    raw_ip2_nombre = ip2_match.group(1).strip() if ip2_match else ""
    ip2_nombre = clean_investigator_name(raw_ip2_nombre)

    # --- 5. Nombre y apellidos del equipo de investigación ---
    # En la sección 8, cada miembro suele empezar con la etiqueta "MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:"
    # seguido de un bloque que contiene "Nombre:".
    miembros = []
    # Buscamos todos los bloques de miembros dentro de la sección 8
    bloques_miembros = re.split(r'MIEMBRO\s+DEL\s+EQUIPO\s+DE\s+INVESTIGACIÓN:', seccion_8)
    
    for bloque in bloques_miembros[1:]: # El primer elemento es el encabezado de la sección
        m_match = re.search(r'Nombre:\s*(.*?)(?=\n|Correo|Fecha|NIF|$)', bloque, re.DOTALL)
        if m_match:
            raw_m_nombre = m_match.group(1).strip()
            m_nombre = clean_investigator_name(raw_m_nombre)
            if m_nombre:
                miembros.append(m_nombre)
    
    equipo_investigacion = ", ".join(miembros) if miembros else ""

    return {
        "Referencia administrativa": referencia,
        "Título": titulo,
        "Nombre y apellidos del investigador/a principal": ip1_nombre,
        "Nombre y apellidos del investigador/a principal 2": ip2_nombre,
        "Nombre y apellidos del equipo de investigación": equipo_investigacion
    }