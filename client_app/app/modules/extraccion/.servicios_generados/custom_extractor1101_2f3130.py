import fitz
import re

def extraer_datos(filename):
    """
    Extrae campos específicos de documentos de Proyectos de Generación de Conocimiento
    utilizando etiquetas fijas como anclas para garantizar la generalización.
    """
    try:
        doc = fitz.open(filename)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
    except Exception:
        return {
            "Referencia administrativa": None,
            "Título del proyecto": None,
            "Nombre y apellidos del investigador/a principal": None,
            "MIEMBRO DEL EQUIPO DE INVESTIGACIÓN (Etiqueta)": []
        }

    # 1. Referencia administrativa
    # Buscamos la etiqueta "Referencia administrativa:" y capturamos el código alfanumérico siguiente.
    ref_match = re.search(r"Referencia\s+administrativa:\s*(\S+)", full_text)
    referencia = ref_match.group(1).strip() if ref_match else None

    # 2. Título del proyecto
    # Se encuentra bajo la etiqueta "Título:". Capturamos hasta que aparezca el título en inglés ("Title:") 
    # o el Acrónimo. Usamos re.DOTALL para capturar títulos que ocupan varias líneas.
    titulo_match = re.search(r"Título:\s*(.*?)(?=\s*Title:|\s*Acrónimo:)", full_text, re.DOTALL)
    titulo = None
    if titulo_match:
        # Limpiamos saltos de línea y espacios múltiples para normalizar el texto
        titulo = re.sub(r'\s+', ' ', titulo_match.group(1)).strip()

    # 3. Nombre y apellidos del investigador/a principal
    # Para evitar los nombres de contacto administrativo (que aparecen en la pág 1),
    # buscamos específicamente dentro de la sección "Investigador/a Principal".
    ip_name = None
    # Localizamos el inicio de la sección 6 (Investigador/a Principal)
    ip_header_match = re.search(r"(?:\d\.)?\s*Investigador/a\s+Principal\s*(?!\d)", full_text)
    if ip_header_match:
        # Extraemos un bloque de texto después del encabezado para buscar los campos Nombre/Apellidos
        start_idx = ip_header_match.end()
        # Buscamos en los siguientes 2500 caracteres (suficiente para cubrir los datos personales)
        ip_context = full_text[start_idx : start_idx + 2500]
        # Buscamos las etiquetas "Nombre:" y "Apellidos:"
        name_match = re.search(r"Nombre:\s*(.*?)\s+Apellidos:?\s*(.*?)(?=\s*Correo|\s*Fecha|\s*Nacionalidad|\n|$)", ip_context)
        if name_match:
            nombre = name_match.group(1).strip()
            apellidos = name_match.group(2).strip()
            ip_name = f"{nombre} {apellidos}".strip()

    # 4. MIEMBRO DEL EQUIPO DE INVESTIGACIÓN (Etiqueta)
    # Buscamos todas las ocurrencias de la etiqueta exacta. 
    # El nombre suele aparecer en la misma línea o inmediatamente después.
    # El patrón ignora posibles saltos de línea entre la etiqueta y el nombre.
    miembros_raw = re.findall(r"MIEMBRO\s+DEL\s+EQUIPO\s+DE\s+INVESTIGACIÓN:\s*\n?\s*([^\n\r]+)", full_text)
    
    # Limpiamos la lista de posibles ruidos y eliminamos duplicados manteniendo el orden
    miembros_list = []
    for m in miembros_raw:
        clean_name = m.strip()
        if clean_name and clean_name not in miembros_list:
            # Filtro básico: si el nombre capturado parece ser una etiqueta (contiene ':'), se ignora
            if ":" not in clean_name:
                miembros_list.append(clean_name)

    return {
        "Referencia administrativa": referencia,
        "Título del proyecto": titulo,
        "Nombre y apellidos del investigador/a principal": ip_name,
        "MIEMBRO DEL EQUIPO DE INVESTIGACIÓN (Etiqueta)": miembros_list
    }