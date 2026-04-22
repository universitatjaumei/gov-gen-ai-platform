import fitz
import re
import unicodedata

def extraer_datos(filename):
    """
    Extrae campos específicos de documentos de solicitud de Proyectos de Generación de Conocimiento
    utilizando segmentación por etiquetas fijas y expresiones regulares robustas.
    """
    try:
        doc = fitz.open(filename)
        text = ""
        for page in doc:
            text += page.get_text()
    except Exception:
        return {
            "Referencia administrativa": None,
            "Título del proyecto": None,
            "Investigador/a Principal (Nombre y Apellidos)": None,
            "Investigador/a Principal 2 (Nombre y Apellidos)": None,
            "Equipo de investigación - Miembros": []
        }

    # Normalización básica de espacios para facilitar el matching de regex
    text = re.sub(r'[ \t]+', ' ', text)

    def limpiar_valor(val):
        if val:
            val = val.strip()
            # Elimina posibles anclas pegadas al final
            val = re.sub(r'\s+$', '', val)
            return val
        return None

    # 1. Referencia administrativa
    # Buscamos la etiqueta fija y capturamos el código alfanumérico
    ref_match = re.search(r'Referencia administrativa:\s*([\w-]+)', text)
    referencia = ref_match.group(1) if ref_match else None

    # 2. Título del proyecto
    # Buscamos entre 'Título:' y la siguiente etiqueta común 'Title:' o 'Acrónimo:'
    titulo_match = re.search(r'Título:\s*(.*?)(?=\n\s*(?:Title:|Acrónimo:))', text, re.DOTALL)
    titulo = limpiar_valor(titulo_match.group(1)) if titulo_match else None
    if titulo:
        titulo = titulo.replace('\n', ' ')

    # Segmentación por secciones para evitar colisiones entre IP1, IP2 y Contactos
    # Seccion 6: IP1
    # Seccion 7: IP2
    # Seccion 8: Equipo
    sec_ip1 = ""
    sec_ip2 = ""
    sec_equipo = ""

    # Usamos los encabezados numerados como anclas de sección
    parts_ip1 = re.split(r'\n\s*6\.\s+Investigador/a Principal\s*\n', text)
    if len(parts_ip1) > 1:
        # El contenido de la sección 6 está entre el encabezado 6 y el 7
        sub_content = re.split(r'\n\s*7\.\s+Investigador/a Principal 2\s*\n', parts_ip1[1])
        sec_ip1 = sub_content[0]
        if len(sub_content) > 1:
            # El contenido de la sección 7 está entre el encabezado 7 y el 8
            sub_content_2 = re.split(r'\n\s*8\.\s+Equipo de investigación\s*\n', sub_content[1])
            sec_ip2 = sub_content_2[0]
            if len(sub_content_2) > 1:
                sec_equipo = sub_content_2[1]
    else:
        # Backup si no hay números de sección: búsqueda por texto de etiqueta
        parts_ip1_alt = re.split(r'Investigador/a Principal', text)
        # Esto es más arriesgado, pero sirve de fallback
        pass

    # Función auxiliar para extraer Nombre y Apellidos de un bloque
    def extraer_nombre_completo(bloque):
        if not bloque: return None
        # Busca Nombre: ... Apellidos: ... terminando en salto de línea o etiqueta como 'Correo'
        match = re.search(r'Nombre:\s*(.*?)\s+Apellidos:?\s*(.*?)(?=\n|Correo|Fecha|Documento|$)', bloque, re.IGNORECASE)
        if match:
            nombre = match.group(1).strip()
            apellidos = match.group(2).strip()
            return f"{nombre} {apellidos}".strip()
        return None

    # 3. Investigador/a Principal (Nombre y Apellidos)
    ip1_nombre = extraer_nombre_completo(sec_ip1)

    # 4. Investigador/a Principal 2 (Nombre y Apellidos)
    ip2_nombre = extraer_nombre_completo(sec_ip2)

    # 5. Equipo de investigación - Miembros
    # Los miembros suelen aparecer tras la etiqueta "MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:"
    miembros = []
    # Buscamos todas las ocurrencias de la etiqueta de miembro en la sección de equipo o en el resto del doc
    # Si la sección de equipo está vacía, buscamos en todo el texto a partir de donde debería estar la sección 8
    target_text_equipo = sec_equipo if sec_equipo else text.split("Equipo de investigación")[-1]
    
    # Regex para capturar el nombre que sigue inmediatamente a la etiqueta de miembro
    # Suele venir el nombre solo en las siguientes líneas o en la misma
    matches_miembros = re.findall(r'MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:\s*\n?\s*([^\n\r\t]+)', target_text_equipo)
    
    for m in matches_miembros:
        nombre_m = limpiar_valor(m)
        if nombre_m and len(nombre_m) > 3 and "Entidad" not in nombre_m:
            miembros.append(nombre_m)

    # Deduplicación manteniendo orden
    miembros_final = list(dict.fromkeys(miembros))

    return {
        "Referencia administrativa": referencia,
        "Título del proyecto": titulo,
        "Investigador/a Principal (Nombre y Apellidos)": ip1_nombre,
        "Investigador/a Principal 2 (Nombre y Apellidos)": ip2_nombre,
        "Equipo de investigación - Miembros": miembros_final
    }