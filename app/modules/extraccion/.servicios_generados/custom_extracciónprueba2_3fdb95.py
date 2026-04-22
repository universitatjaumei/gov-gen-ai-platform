import fitz
import re

def extraer_datos(filename):
    """
    Extrae campos específicos de documentos de Proyectos de Generación de Conocimiento
    utilizando una estrategia basada exclusivamente en etiquetas (anchors) para
    garantizar la generalización.
    """
    doc = fitz.open(filename)
    text = ""
    for page in doc:
        text += page.get_text()

    # --- FUNCIONES DE LIMPIEZA ---
    def limpiar_valor(valor):
        if not valor:
            return ""
        # Eliminar saltos de línea y espacios múltiples
        valor = re.sub(r'\s+', ' ', valor)
        # Eliminar posibles ruidos de etiquetas repetidas en el valor capturado
        valor = re.sub(r':\s*:', ':', valor)
        return valor.strip()

    def limpiar_nombre(nombre):
        if not nombre:
            return ""
        # CORRECCIÓN: Eliminar la etiqueta "Apellidos" que puede ser capturada por error.
        # Se hace de forma robusta para casos con/sin dos puntos y espaciado variable,
        # usando \b para asegurar que se trata de la palabra completa.
        nombre = re.sub(r'\bApellidos\b\s*:?', '', nombre, flags=re.I)
        
        # Limpieza general de espacios y saltos de línea.
        nombre = limpiar_valor(nombre)
        
        # CORRECCIÓN: Simplificar la unión de partes del nombre.
        # Los nombres a veces vienen en partes separadas por ":", los unimos.
        partes = [p.strip() for p in nombre.split(':') if p.strip()]
        return " ".join(partes)

    # --- 1. REFERENCIA ADMINISTRATIVA ---
    # Se busca en los encabezados de página
    ref_admin = "" # Inicializar como string vacío
    ref_match = re.search(r'Referencia administrativa:\s*(\S+)', text)
    if ref_match:
        ref_admin = ref_match.group(1).strip()

    # --- 2. TÍTULO ---
    # Ubicado en la sección 2. Datos del Proyecto -> Información proyecto
    titulo = ""
    titulo_match = re.search(r'Título:\s*(.*?)(?=\nTitle:|\nAcrónimo:|Duración \(años\):)', text, re.S | re.I)
    if titulo_match:
        titulo = limpiar_valor(titulo_match.group(1))

    # --- 3. INVESTIGADOR/A PRINCIPAL (IP1) ---
    # Ubicado en la sección 6.
    ip1_nombre = ""
    # Delimitamos el bloque de la sección 6 para evitar capturar otros nombres
    bloque_ip1 = re.search(r'6\.\s*Investigador/a Principal\s*(.*?)7\.\s*Investigador/a Principal 2', text, re.S | re.I)
    if bloque_ip1:
        contenido_ip1 = bloque_ip1.group(1)
        # CORRECCIÓN: Añadido delimitador de pie de página para evitar captura de basura en saltos de página.
        match_nombre = re.search(r'Nombre:\s*(.*?)(?=\nCorreo Electrónico:|\nFecha Nacimiento:|\s*\d{2}/\d{2}/\d{4})', contenido_ip1, re.S | re.I)
        if match_nombre:
            ip1_nombre = limpiar_nombre(match_nombre.group(1))

    # --- 4. INVESTIGADOR/A PRINCIPAL 2 (IP2) ---
    # Ubicado en la sección 7.
    ip2_nombre = ""
    # Delimitamos el bloque entre sección 7 y 8
    bloque_ip2 = re.search(r'7\.\s*Investigador/a Principal 2\s*(.*?)8\.\s*Equipo de investigación', text, re.S | re.I)
    if bloque_ip2:
        contenido_ip2 = bloque_ip2.group(1)
        # CORRECCIÓN: Añadido delimitador de pie de página para evitar captura de basura en saltos de página.
        match_nombre = re.search(r'Nombre:\s*(.*?)(?=\nCorreo Electrónico:|\nFecha Nacimiento:|\s*\d{2}/\d{2}/\d{4})', contenido_ip2, re.S | re.I)
        if match_nombre:
            ip2_nombre = limpiar_nombre(match_nombre.group(1))

    # --- 5. EQUIPO DE INVESTIGACIÓN ---
    # Ubicado en la sección 8 en adelante. 
    # Cada miembro suele empezar con "MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:"
    equipo_nombres = []
    # Buscamos la sección 8 hasta el final o siguiente sección relevante
    bloque_equipo_match = re.search(r'8\.\s*Equipo de investigación\s*(.*)', text, re.S | re.I)
    if bloque_equipo_match:
        bloque_equipo = bloque_equipo_match.group(1)
        
        # CORRECCIÓN: Añadido delimitador de pie de página para evitar captura de basura en saltos de página.
        miembros_raw = re.findall(r'MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:.*?\nNombre:\s*(.*?)(?=\nCorreo [eE]lectrónico:|\nFecha [nN]acimiento:|\s*\d{2}/\d{2}/\d{4})', bloque_equipo, re.S)
        
        for m in miembros_raw:
            nombre_limpio = limpiar_nombre(m)
            if nombre_limpio and nombre_limpio not in equipo_nombres:
                equipo_nombres.append(nombre_limpio)
    
    equipo_str = ", ".join(equipo_nombres) if equipo_nombres else ""

    # --- RESULTADO FINAL ---
    return {
        "Referencia administrativa": ref_admin,
        "Título": titulo,
        "Nombre y apellidos del investigador/a principal": ip1_nombre,
        "Nombre y apellidos del investigador/a principal 2": ip2_nombre,
        "Nombre y apellidos del equipo de investigación": equipo_str
    }