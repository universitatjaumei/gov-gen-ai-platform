import fitz
import re

def extraer_datos(filename):
    """
    Extrae campos específicos de documentos de solicitud de proyectos usando 
    un enfoque basado puramente en etiquetas (anchors) para garantizar la generalización.
    """
    doc = fitz.open(filename)
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    # Pre-procesamiento básico para normalizar espacios y facilitar la búsqueda de etiquetas
    text = re.sub(r'[ \t]+', ' ', full_text)

    def clean_val(val):
        """Limpia ruidos de extracción, saltos de línea y colones de tablas."""
        if not val:
            return ""
        # Eliminar posibles restos de etiquetas colindantes si el regex falló en el stop
        val = re.split(r'\n[A-Z][a-z]+:', val)[0]
        # Sustituir ":" por espacio (común en extracciones de tablas fitz)
        val = val.replace(":", " ")
        # Limpiar espacios en blanco extra
        val = " ".join(val.split()).strip()
        return val

    def get_block(text, start_pattern, end_pattern=None):
        """Extrae un bloque de texto entre dos etiquetas o secciones."""
        try:
            start_match = re.search(start_pattern, text, re.IGNORECASE | re.DOTALL)
            if not start_match:
                return ""
            start_idx = start_match.end()
            
            if end_pattern:
                end_match = re.search(end_pattern, text[start_idx:], re.IGNORECASE | re.DOTALL)
                if end_match:
                    return text[start_idx : start_idx + end_match.start()]
            
            return text[start_idx:]
        except Exception:
            return ""

    # --- 1. Referencia administrativa ---
    # Se busca globalmente ya que suele estar en el encabezado
    ref_match = re.search(r"Referencia\s+administrativa:\s*([A-Z0-9-I]+)", text)
    referencia = ref_match.group(1).strip() if ref_match else None

    # --- 2. Título ---
    # Se busca en la sección 2 (Datos del Proyecto)
    sec2 = get_block(text, r"2\.\s*Datos\s+del\s+Proyecto", r"3\.\s*Otros\s+datos")
    titulo = None
    if sec2:
        titulo_match = re.search(r"Título:\s*(.*?)(?=\s*Title:|\n\s*Acrónimo|\n\s*Duración|\n\s*Palabras\s+clave)", sec2, re.S)
        if titulo_match:
            titulo = clean_val(titulo_match.group(1))

    # --- 3. Investigador/a Principal 1 ---
    sec6 = get_block(text, r"6\.\s*Investigador/a\s+Principal", r"7\.\s*")
    ip1 = None
    if sec6:
        # Se busca el bloque del nombre, deteniéndonos antes de los siguientes campos o de un pie de página para evitar capturar basura.
        stop_pattern_ip = r"\n\s*(?:Correo|Fecha|Tipo Documento|Documento|Nacionalidad|\d{2}/\d{2}/\d{4})"
        ip1_match = re.search(fr"Nombre:\s*(.*?)(?={stop_pattern_ip})", sec6, re.S)
        if ip1_match:
            raw_name = ip1_match.group(1)
            # Se elimina la etiqueta "Apellidos:", haciendo el ':' opcional para casos donde no aparezca.
            cleaned_name = re.sub(r'Apellidos\s*:?', ' ', raw_name, flags=re.IGNORECASE)
            ip1 = clean_val(cleaned_name)

    # --- 4. Investigador/a Principal 2 ---
    sec7 = get_block(text, r"7\.\s*Investigador/a\s+Principal\s+2", r"8\.\s*Equipo")
    ip2 = None
    if sec7:
        # Se aplica la misma lógica que para IP1, ajustando los campos de parada.
        stop_pattern_ip2 = r"\n\s*(?:Correo|Fecha|Tipo Documento|Documento|País|\d{2}/\d{2}/\d{4})"
        ip2_match = re.search(fr"Nombre:\s*(.*?)(?={stop_pattern_ip2})", sec7, re.S)
        if ip2_match:
            raw_name = ip2_match.group(1)
            # Se elimina la etiqueta "Apellidos:", haciendo el ':' opcional para casos donde no aparezca.
            cleaned_name = re.sub(r'Apellidos\s*:?', ' ', raw_name, flags=re.IGNORECASE)
            ip2 = clean_val(cleaned_name)

    # --- 5. Equipo de investigación ---
    # Se busca en la sección 8. El 'get_block' es abierto porque puede ser la última sección.
    sec8 = get_block(text, r"8\.\s*Equipo\s+de\s+investigación")
    equipo_str = ""
    if sec8:
        # Se divide el texto por cada ocurrencia de "MIEMBRO DEL EQUIPO..."
        member_blocks = re.split(r"MIEMBRO\s+DEL\s+EQUIPO\s+DE\s+INVESTIGACIÓN:", sec8)
        names = []
        for block in member_blocks[1:]: # El primer elemento es el texto antes del primer miembro
            # Se define un patrón de parada robusto para no capturar pies de página u otros datos.
            stop_pattern_team = r"\n\s*(?:Correo electrónico|Correo|Fecha nacimiento|Fecha|Datos|Rol|Entidad|\d{2}/\d{2}/\d{4})"
            m = re.search(fr"Nombre:\s*(.*?)(?={stop_pattern_team})", block, re.S)
            if m:
                raw_name = m.group(1)
                # Se aplica la misma limpieza que a los IPs, haciendo el ':' de "Apellidos:" opcional.
                cleaned_name = re.sub(r'Apellidos\s*:?', ' ', raw_name, flags=re.IGNORECASE)
                name = clean_val(cleaned_name)
                if name and name not in names: # Evitar duplicados
                    names.append(name)
        
        equipo_str = ", ".join(names) if names else ""

    return {
        "Referencia administrativa": referencia,
        "Título": titulo,
        "Nombre y apellidos del investigador/a principal": ip1,
        "Nombre y apellidos del investigador/a principal 2": ip2,
        "Nombre y apellidos del equipo de investigación": equipo_str
    }