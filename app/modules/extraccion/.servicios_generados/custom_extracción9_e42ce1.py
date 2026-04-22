import fitz
import re

def extraer_datos(filename):
    """
    Extrae campos específicos de documentos de Proyectos de Generación de Conocimiento
    utilizando técnicas de anclaje por etiquetas para garantizar la generalización.
    """
    doc = fitz.open(filename)
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    # 1. Referencia administrativa
    # Se encuentra comúnmente en el encabezado: "Referencia administrativa: PID..."
    ref_match = re.search(r"Referencia\s+administrativa:\s*([\w\-]+)", full_text, re.IGNORECASE)
    referencia = ref_match.group(1) if ref_match else None

    # 2. Título
    # Se encuentra bajo la sección 2 en "Información proyecto".
    # El ancla final suele ser "Title:" (título en inglés) o "Acrónimo:".
    titulo_match = re.search(
        r"Título:\s*(.*?)(?=\s*Title:|\s*Acrónimo:|\n\s*\d+\.)",
        full_text,
        re.DOTALL | re.IGNORECASE
    )
    titulo = ""
    if titulo_match:
        # Limpieza de saltos de línea internos en el título
        titulo = re.sub(r'\s+', ' ', titulo_match.group(1).strip())

    # 3. Nombre y apellidos del investigador/a principal (IP1)
    # Se busca dentro de la Sección 6. Investigador/a Principal.
    ip1_name = ""
    # Se usa un negative lookahead para no confundir con "Investigador/a Principal 2"
    sec6_match = re.search(r"6\.\s*Investigador/a\s*Principal(?!\s*2)(.*?)(?=7\.\s*|8\.\s*)", full_text, re.DOTALL | re.IGNORECASE)
    if sec6_match:
        content_sec6 = sec6_match.group(1)
        # El nombre está seguido de etiquetas como Correo Electrónico o Fecha Nacimiento.
        name_match = re.search(r"Nombre:\s*(.*?)(?=\s*Correo|\s*Fecha|\s*Nacionalidad|Tipo\s+de\s+Documento|$)", content_sec6, re.DOTALL)
        if name_match:
            name_raw = name_match.group(1).strip()
            # Limpieza robusta: elimina "Apellidos:", colons extra, y normaliza espacios.
            name_clean = re.sub(r'\bApellidos\b\s*:?', '', name_raw, flags=re.IGNORECASE)
            name_clean = name_clean.replace(':', ' ').strip()
            ip1_name = re.sub(r'\s+', ' ', name_clean)

    # 4. Nombre y apellidos del investigador/a principal 2 (IP2)
    # Se busca específicamente en la Sección 7.
    ip2_name = ""
    sec7_match = re.search(r"7\.\s*Investigador/a\s*Principal\s*2(.*?)(?=8\.\s*)", full_text, re.DOTALL)
    if sec7_match:
        content_sec7 = sec7_match.group(1)
        name_match = re.search(r"Nombre:\s*(.*?)(?=\s*Correo|\s*Fecha|\s*Nacionalidad|Tipo\s+de\s+Documento|$)", content_sec7, re.DOTALL)
        if name_match:
            name_raw = name_match.group(1).strip()
            # Se aplica la misma lógica de limpieza que para IP1.
            name_clean = re.sub(r'\bApellidos\b\s*:?', '', name_raw, flags=re.IGNORECASE)
            name_clean = name_clean.replace(':', ' ').strip()
            ip2_name = re.sub(r'\s+', ' ', name_clean)

    # 5. Nombre y apellidos del equipo de investigación
    # Se buscan todos los bloques "MIEMBRO..." y se extrae el campo "Nombre:" de cada uno.
    equipo_list = []
    member_blocks = re.split(r"MIEMBRO\s+DEL\s+EQUIPO\s+DE\s+INVESTIGACIÓN:", full_text)

    if len(member_blocks) > 1:
        # Se omite el primer bloque, que es todo el texto anterior al primer miembro.
        for block in member_blocks[1:]:
            # CORRECCIÓN: Se busca el nombre solo en su línea ([^\n]+) para evitar capturar pies de página.
            # El regex anterior usaba re.DOTALL y era demasiado 'greedy', capturando texto no deseado.
            name_match = re.search(r"Nombre:\s*([^\n]+)", block)
            if name_match:
                name_raw = name_match.group(1).strip()
                # CORRECCIÓN: Se mejora la limpieza para eliminar la palabra 'Apellidos'
                # con o sin dos puntos, usando límites de palabra (\b), según el feedback.
                name_clean = re.sub(r'\bApellidos\b\s*:?', '', name_raw, flags=re.IGNORECASE)
                name_clean = name_clean.replace(':', ' ').strip()
                final_name = re.sub(r'\s+', ' ', name_clean)
                if final_name:
                    equipo_list.append(final_name)

    equipo_str = ", ".join(equipo_list) if equipo_list else ""

    return {
        "Referencia administrativa": referencia,
        "Título": titulo,
        "Nombre y apellidos del investigador/a principal": ip1_name if ip1_name else None,
        "Nombre y apellidos del investigador/a principal 2": ip2_name if ip2_name else "",
        "Nombre y apellidos del equipo de investigación": equipo_str
    }