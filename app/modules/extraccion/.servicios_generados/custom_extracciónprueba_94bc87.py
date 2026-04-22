import fitz
import re

def extraer_datos(filename):
    """
    Extrae campos específicos de un documento PDF basándose en etiquetas fijas (anchors).
    Diseñado para generalizar independientemente de los valores de los datos.
    """
    # Abrir el documento y extraer todo el texto
    doc = fitz.open(filename)
    text = ""
    for page in doc:
        text += page.get_text()
    
    # Función auxiliar para limpiar espacios, saltos de línea y ruidos de formato (como dobles puntos)
    def clean_text(val):
        if not val:
            return ""
        # Normalizar espacios y eliminar saltos de línea
        val = re.sub(r'\s+', ' ', val)
        # Limpiar caracteres sobrantes comunes en los bordes por el formato del PDF
        val = val.strip(' :;')
        return val

    # 1. REFERENCIA ADMINISTRATIVA
    # Se busca la etiqueta y se captura la palabra/código que sigue (alfanumérico con guiones)
    ref_match = re.search(r'Referencia\s+administrativa:\s*([\w-]+)', text)
    referencia = ref_match.group(1) if ref_match else None

    # 2. TÍTULO
    # Se encuentra en la sección 2, bajo "Título:". Se detiene antes de la versión en inglés (Title:) o el Acrónimo.
    titulo_match = re.search(r'Título:\s*(.*?)(?=\s*(?:Title:|Acrónimo:|\r?\n\r?\n))', text, re.DOTALL | re.IGNORECASE)
    titulo = clean_text(titulo_match.group(1)) if titulo_match else ""

    # Función auxiliar para limpiar los nombres de los investigadores
    def clean_investigator_name(raw_name):
        if not raw_name:
            return ""
        # Reemplaza separadores como " Apellidos: " o " : " por un solo espacio
        cleaned_name = re.sub(r'\s*(Apellidos:?|:)\s*', ' ', raw_name, flags=re.IGNORECASE)
        return clean_text(cleaned_name)

    # 3. INVESTIGADOR/A PRINCIPAL 1 (Sección 6)
    # Acotamos la búsqueda entre la sección 6 y la 7 para evitar colisiones
    ip1_block = ""
    section_6_start = re.search(r'6\.\s*Investigador/a\s*Principal', text, re.IGNORECASE)
    section_7_start = re.search(r'7\.\s*Investigador/a\s*Principal\s*2', text, re.IGNORECASE)
    
    if section_6_start:
        end_pos = section_7_start.start() if section_7_start else len(text)
        ip1_block = text[section_6_start.end():end_pos]
    
    # Extraemos el nombre dentro de ese bloque
    ip1_name_match = re.search(r'Nombre:\s*(.*?)(?=\s*(?:Correo|Fecha|Nacionalidad|Tipo|Documento))', ip1_block, re.DOTALL | re.IGNORECASE)
    ip1_nombre_raw = ip1_name_match.group(1) if ip1_name_match else ""
    ip1_nombre = clean_investigator_name(ip1_nombre_raw)

    # 4. INVESTIGADOR/A PRINCIPAL 2 (Sección 7)
    # Acotamos la búsqueda entre la sección 7 y la 8
    ip2_block = ""
    section_8_start = re.search(r'8\.\s*Equipo\s+de\s+investigación', text, re.IGNORECASE)
    
    if section_7_start:
        end_pos = section_8_start.start() if section_8_start else len(text)
        ip2_block = text[section_7_start.end():end_pos]

    ip2_name_match = re.search(r'Nombre:\s*(.*?)(?=\s*(?:Correo|Fecha|Nacionalidad|País|Tipo|Documento))', ip2_block, re.DOTALL | re.IGNORECASE)
    ip2_nombre_raw = ip2_name_match.group(1) if ip2_name_match else ""
    ip2_nombre = clean_investigator_name(ip2_nombre_raw)

    # 5. EQUIPO DE INVESTIGACIÓN (Sección 8)
    # Buscamos todos los bloques que empiezan por "MIEMBRO DEL EQUIPO DE INVESTIGACIÓN"
    team_members = []
    if section_8_start:
        team_section = text[section_8_start.end():]
        # Dividimos la sección por cada etiqueta de miembro
        member_blocks = re.split(r'MIEMBRO\s+DEL\s+EQUIPO\s+DE\s+INVESTIGACIÓN:', team_section, flags=re.IGNORECASE)
        
        # Lista ampliada de palabras clave que marcan el final del campo del nombre.
        # CORRECCIÓN: Se añade un patrón para detectar el pie de página (que empieza por una fecha) y evitar que se incluya en el nombre.
        stop_words = r'Correo|Fecha|Nacionalidad|País|Tipo|Documento|Rol|Entidad|Centro|electrónico|Datos académicos|Grado|Titulación|Categoría|Vinculación|Duración|Código ORCID|Currículum|\d{2}/\d{2}/\d{4}'

        # El primer elemento del split suele ser texto introductorio antes del primer miembro
        for block in member_blocks[1:]:
            # En cada bloque, buscamos "Nombre:" y paramos en la siguiente etiqueta de campo o el pie de página
            name_match = re.search(r'Nombre:\s*(.*?)(?=\s*(?:' + stop_words + r'))', block, re.DOTALL | re.IGNORECASE)
            if name_match:
                member_name_raw = name_match.group(1)
                member_name = clean_investigator_name(member_name_raw)
                if member_name:
                    team_members.append(member_name)
    
    equipo_nombres = ", ".join(team_members) if team_members else ""

    # Retorno de resultados
    return {
        "Referencia administrativa": referencia,
        "Título": titulo,
        "Nombre y apellidos del investigador/a principal": ip1_nombre,
        "Nombre y apellidos del investigador/a principal 2": ip2_nombre,
        "Nombre y apellidos del equipo de investigación": equipo_nombres
    }