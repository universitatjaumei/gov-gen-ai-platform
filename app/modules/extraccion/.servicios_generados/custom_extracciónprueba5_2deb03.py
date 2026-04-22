import fitz
import re

def extraer_datos(filename):
    """
    Extrae información específica de documentos PDF de solicitudes de proyectos
    utilizando una estrategia basada en etiquetas (anchors) para asegurar la generalización.
    """
    doc = fitz.open(filename)
    text = ""
    for page in doc:
        text += page.get_text()

    # Normalizamos espacios para evitar problemas con saltos de línea inesperados
    # pero mantenemos suficiente estructura para delimitar secciones.
    clean_text = re.sub(r'[ \t]+', ' ', text)

    # Inicialización de resultados
    results = {
        "Referencia administrativa": None,
        "Título": None,
        "Nombre y apellidos del investigador/a principal": None,
        "Nombre y apellidos del investigador/a principal 2": None,
        "Nombre y apellidos del equipo de investigación": ""
    }

    # --- 1. REFERENCIA ADMINISTRATIVA ---
    # Se busca la etiqueta fija y se captura el primer bloque de texto no vacío.
    ref_match = re.search(r"Referencia administrativa:\s*(\S+)", clean_text)
    if ref_match:
        results["Referencia administrativa"] = ref_match.group(1).strip()

    # --- 2. TÍTULO ---
    # El título suele estar en la sección 2. Se detiene ante la versión en inglés (Title:) o el Acrónimo.
    titulo_match = re.search(r"Título:\s*(.+?)(?=\s*(?:\n\s*Title:|Title:|Acrónimo:|Duración))", clean_text, re.DOTALL | re.IGNORECASE)
    if titulo_match:
        # Limpieza de saltos de línea internos en títulos largos
        results["Título"] = re.sub(r'\s+', ' ', titulo_match.group(1)).strip()

    # --- 3. INVESTIGADOR/A PRINCIPAL (SECCIÓN 6) ---
    # Delimitamos la búsqueda a la sección 6 para evitar colisiones con otros nombres.
    sec6 = re.search(r"6\.\s+Investigador/a Principal(.+?)(?=7\.\s+Investigador/a Principal 2|8\.\s+Equipo de investigación)", clean_text, re.DOTALL | re.IGNORECASE)
    if sec6:
        ip1_block = sec6.group(1)
        # El nombre termina donde empiezan otros datos personales o el correo
        name_match = re.search(r"Nombre:\s*(.+?)(?=\s*(?:\n|Correo [eE]lectrónico|Fecha Nacimiento|Nacionalidad|Sexo|Tipo de Documento|[a-zA-Z0-9._%+-]+@))", ip1_block, re.DOTALL)
        if name_match:
            # Unificamos nombres separados por ':' y eliminamos la etiqueta "Apellidos" si aparece.
            name = re.sub(r'\s*:\s*', ' ', name_match.group(1))
            name = re.sub(r'\bApellidos\b', '', name, flags=re.IGNORECASE)
            results["Nombre y apellidos del investigador/a principal"] = re.sub(r'\s+', ' ', name).strip()

    # --- 4. INVESTIGADOR/A PRINCIPAL 2 (SECCIÓN 7) ---
    sec7 = re.search(r"7\.\s+Investigador/a Principal 2(.+?)(?=8\.\s+Equipo de investigación|$)", clean_text, re.DOTALL | re.IGNORECASE)
    if sec7:
        ip2_block = sec7.group(1)
        name_match = re.search(r"Nombre:\s*(.+?)(?=\s*(?:\n|Correo [eE]lectrónico|Fecha Nacimiento|Nacionalidad|Sexo|Tipo de Documento|[a-zA-Z0-9._%+-]+@))", ip2_block, re.DOTALL)
        if name_match:
            # Unificamos nombres separados por ':' y eliminamos la etiqueta "Apellidos" si aparece.
            name = re.sub(r'\s*:\s*', ' ', name_match.group(1))
            name = re.sub(r'\bApellidos\b', '', name, flags=re.IGNORECASE)
            results["Nombre y apellidos del investigador/a principal 2"] = re.sub(r'\s+', ' ', name).strip()

    # --- 5. EQUIPO DE INVESTIGACIÓN (SECCIÓN 8) ---
    # Buscamos todas las ocurrencias de la etiqueta de miembro dentro o después de la sección 8.
    sec8_start = re.search(r"8\.\s+Equipo de investigación", clean_text, re.IGNORECASE)
    if sec8_start:
        sec8_text = clean_text[sec8_start.end():]
        # Capturamos el nombre que sigue a la etiqueta hasta encontrar un cambio de campo (Rol, Entidad, etc.)
        members = re.findall(r"MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:\s*(.+?)(?=\s*(?:a la que pertenece|Rol:|Entidad:|Centro:|Datos personales|\n))", sec8_text, re.IGNORECASE | re.DOTALL)
        
        cleaned_members = []
        for m in members:
            # Limpieza de ruidos de lectura (caracteres de control, múltiples espacios)
            m_clean = re.sub(r'\s*:\s*', ' ', m)
            m_clean = re.sub(r'\s+', ' ', m_clean).strip()
            # Evitamos duplicados y entradas vacías
            if m_clean and m_clean not in cleaned_members:
                cleaned_members.append(m_clean)
        
        results["Nombre y apellidos del equipo de investigación"] = ", ".join(cleaned_members)

    return results