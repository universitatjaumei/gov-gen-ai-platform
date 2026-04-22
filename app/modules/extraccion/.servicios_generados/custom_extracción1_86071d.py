import fitz
import re

def extraer_datos(filename):
    """
    Script para extraer datos de solicitudes de proyectos de investigación.
    Utiliza una estrategia basada en etiquetas (anchors) para garantizar la generalización.
    """
    # Abrir el documento y extraer el texto completo
    doc = fitz.open(filename)
    text = ""
    for page in doc:
        text += page.get_text()
    
    # --- FUNCIONES DE LIMPIEZA ---
    def clean_field(val):
        if not val:
            return ""
        # Colapsar espacios múltiples y saltos de línea
        val = re.sub(r'\s+', ' ', val)
        # CORRECCIÓN: Se mejora la limpieza para eliminar no solo ":" sino también
        # la palabra "apellidos" cuando actúa como separador, tal como solicita el feedback.
        val = re.sub(r'\s*(:|apellidos:?)\s*', ' ', val, flags=re.IGNORECASE)
        return val.strip()

    def extract_name_from_block(block_text):
        """Extrae nombre y apellidos buscando etiquetas específicas dentro de un bloque."""
        # Los delimitadores son etiquetas que suelen seguir a los nombres en el formulario
        delimiters = r'(?:\n\s*(?:Apellidos:|Correo|Fecha|Nacionalidad|Sexo|Documento|DATOS|Datos|Tipo|Teléfono|Móvil|Dirección|Entidad|Centro|Departamento|¿|Categoría|Vinculación|Duración|Código|Otra|Rol))'
        
        # CORRECCIÓN: Se elimina re.DOTALL para que `.` no coincida con saltos de línea.
        # Esto evita que la captura de 'Nombre' se extienda a otras líneas y capture incorrectamente la etiqueta 'Apellidos'.
        n_match = re.search(r'Nombre:\s*(.*?)(?=' + delimiters + '|$)', block_text, re.IGNORECASE)
        a_match = re.search(r'Apellidos:\s*(.*?)(?=' + delimiters + '|$)', block_text, re.IGNORECASE)
        
        # Fallback por si el nombre está en una línea sin delimitadores claros después
        if not n_match:
             n_match = re.search(r'Nombre:\s*([^\n\r]*)', block_text, re.IGNORECASE)
        if not a_match:
             a_match = re.search(r'Apellidos:\s*([^\n\r]*)', block_text, re.IGNORECASE)

        nombre = n_match.group(1) if n_match else ""
        apellidos = a_match.group(1) if a_match else ""
        
        # Si se encontró una etiqueta de Apellidos separada, nos aseguramos de que
        # la variable 'nombre' no contenga también la etiqueta y los apellidos,
        # lo que podría suceder si estuvieran en la misma línea, causando duplicados.
        if a_match and 'apellidos' in nombre.lower():
            nombre = re.split(r'\s*apellidos:?\s*', nombre, maxsplit=1, flags=re.IGNORECASE)[0]

        full_name = f"{nombre} {apellidos}".strip()
        return clean_field(full_name)

    # --- EXTRACCIÓN DE CAMPOS ---

    # 1. Referencia administrativa
    # Se encuentra normalmente en el encabezado. Buscamos la etiqueta y el código alfanumérico.
    ref_admin = None
    ref_match = re.search(r'Referencia\s+administrativa:\s*([\w\-]+)', text, re.IGNORECASE)
    if ref_match:
        ref_admin = ref_match.group(1).strip()

    # 2. Título
    # Se encuentra en la sección 2. Buscamos entre 'Título:' y 'Title:' o 'Acrónimo:'
    titulo = ""
    titulo_match = re.search(r'Título:\s*(.*?)(?=\n\s*(?:Title:|Acrónimo:|Duración|Forma de ejecución))', text, re.DOTALL | re.IGNORECASE)
    if titulo_match:
        titulo = clean_field(titulo_match.group(1))

    # 3. Nombre y apellidos del investigador/a principal (IP1)
    # Buscamos específicamente en la sección 6
    ip1_name = ""
    sec6_block = re.search(r'(?:^|\n)6\.\s*Investigador/a\s+Principal(.*?)(?=\n\s*[78]\.)', text, re.DOTALL | re.IGNORECASE)
    if sec6_block:
        ip1_name = extract_name_from_block(sec6_block.group(1))

    # 4. Nombre y apellidos del investigador/a principal 2 (IP2)
    # Buscamos específicamente en la sección 7, validando que el título sea IP 2
    ip2_name = ""
    sec7_match = re.search(r'(?:^|\n)7\.\s*Investigador/a\s+Principal\s+2(.*?)(?=\n\s*8\.)', text, re.DOTALL | re.IGNORECASE)
    if sec7_match:
        ip2_name = extract_name_from_block(sec7_match.group(1))

    # 5. Nombre y apellidos del equipo de investigación (Sección 8)
    equipo_str = ""
    sec8_match = re.search(r'(?:^|\n)8\.\s*Equipo\s+de\s+investigación(.*)', text, re.DOTALL | re.IGNORECASE)
    if sec8_match:
        equipo_content = sec8_match.group(1)
        # CORRECCIÓN: Se usa re.findall en lugar de re.split para aislar de forma segura el bloque de cada miembro.
        # El lookahead (?=...) asegura que no se consuma el delimitador del siguiente bloque.
        # \Z asegura que se capture el último miembro hasta el final del texto.
        member_blocks = re.findall(r'MIEMBRO\s+DEL\s+EQUIPO\s+DE\s+INVESTIGACIÓN:(.*?)(?=MIEMBRO\s+DEL\s+EQUIPO\s+DE\s+INVESTIGACIÓN:|\Z)', equipo_content, flags=re.DOTALL|re.IGNORECASE)
        nombres_equipo = []
        
        for block in member_blocks:
            # Limitar el bloque hasta la firma o el siguiente identificador para no desbordar
            block_limit = re.split(r'Firma del/de la|Consiento en participar', block, flags=re.IGNORECASE)[0]
            name = extract_name_from_block(block_limit)
            
            # Si no se encontró mediante etiqueta "Nombre:", intentar extraer la primera línea tras la etiqueta de Miembro
            if not name:
                first_line_match = re.search(r'^\s*([^\n\r,]+(?:,\s*[^\n\r,]+)*)', block_limit.strip())
                if first_line_match:
                    # Captura nombres con formato "Apellidos, Nombre" y los normaliza
                    potential_name = first_line_match.group(1).strip()
                    if ',' in potential_name:
                         parts = [p.strip() for p in potential_name.split(',')]
                         if len(parts) == 2:
                             potential_name = f"{parts[1]} {parts[0]}"
                    name = clean_field(potential_name)

            if name and len(name) > 3: # Evitar capturas vacías o ruidos cortos
                nombres_equipo.append(name)
        
        # Eliminar duplicados manteniendo el orden
        seen = set()
        nombres_unicos = [x for x in nombres_equipo if not (x.lower() in seen or seen.add(x.lower()))]
        equipo_str = ", ".join(nombres_unicos)

    return {
        'Referencia administrativa': ref_admin,
        'Título': titulo,
        'Nombre y apellidos del investigador/a principal': ip1_name if ip1_name else None,
        'Nombre y apellidos del investigador/a principal 2': ip2_name if ip2_name else "",
        'Nombre y apellidos del equipo de investigación': equipo_str if equipo_str else ""
    }