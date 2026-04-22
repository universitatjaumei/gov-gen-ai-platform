import fitz
import re

def extraer_datos(filename):
    """
    Extrae campos específicos de un documento PDF de solicitud de proyectos 
    de generación de conocimiento utilizando un motor basado en anclas (labels).
    """
    doc = fitz.open(filename)
    text = ""
    for page in doc:
        # Extraemos texto manteniendo un orden visual lógico
        text += page.get_text("text") + "\n"
    
    # --- HELPER: Limpieza de strings ---
    def clean_text(t):
        if not t:
            return ""
        # Eliminar ruidos comunes como colones repetidos detectados en el contenido (ej: "Nombre: Rosa   Apellidos:")
        t = re.sub(r'[:]+', '', t)
        # Eliminar espacios extra y saltos de línea
        return " ".join(t.split()).strip()

    # --- 1. Referencia administrativa ---
    # Se encuentra repetida en encabezados. Buscamos el patrón después de la etiqueta fija.
    ref_match = re.search(r'Referencia\s+administrativa:\s*([\w\d-]+)', text, re.IGNORECASE)
    referencia = ref_match.group(1) if ref_match else None

    # --- 2. Título ---
    # Se encuentra en la sección 2. Suele terminar donde empieza la versión en inglés (Title:).
    titulo_match = re.search(r'Título:\s*(.*?)(?=\n\s*Title:|\n\s*Acrónimo:|\n\s*Duración)', text, re.DOTALL | re.IGNORECASE)
    titulo = clean_text(titulo_match.group(1)) if titulo_match else ""

    # --- SEGMENTACIÓN POR SECCIONES PARA INVESTIGADORES ---
    # Slicing del texto para evitar que el IP2 sea confundido con el IP1 o miembros del equipo.
    sec_6_start = text.find("6. Investigador/a Principal")
    sec_7_start = text.find("7. Investigador/a Principal 2")
    sec_8_start = text.find("8. Equipo de investigación")

    # --- 3. Investigador/a Principal (IP1) ---
    ip1_nombre_completo = ""
    if sec_6_start != -1:
        # Delimitar el bloque de la sección 6
        end_ip1 = sec_7_start if sec_7_start != -1 else (sec_8_start if sec_8_start != -1 else len(text))
        bloque_ip1 = text[sec_6_start:end_ip1]
        
        # Siguiendo la regla de concatenar Nombre + Apellidos si vienen separados
        nom_m = re.search(r'Nombre:\s*(.*?)(?=\s*Apellidos:|\s*Correo|\n)', bloque_ip1, re.IGNORECASE)
        ape_m = re.search(r'Apellidos:\s*(.*?)(?=\s*Correo|\s*Fecha|\s*Nacionalidad|\n)', bloque_ip1, re.IGNORECASE)
        
        nombre = clean_text(nom_m.group(1)) if nom_m else ""
        apellidos = clean_text(ape_m.group(1)) if ape_m else ""
        
        ip1_nombre_completo = clean_text(f"{nombre} {apellidos}")

    # --- 4. Investigador/a Principal 2 (IP2) ---
    ip2_nombre_completo = ""
    if sec_7_start != -1:
        # Delimitar el bloque de la sección 7
        end_ip2 = sec_8_start if sec_8_start != -1 else len(text)
        bloque_ip2 = text[sec_7_start:end_ip2]
        
        nom_m2 = re.search(r'Nombre:\s*(.*?)(?=\s*Apellidos:|\s*Correo|\n)', bloque_ip2, re.IGNORECASE)
        ape_m2 = re.search(r'Apellidos:\s*(.*?)(?=\s*Correo|\s*Fecha|\s*Nacionalidad|\n)', bloque_ip2, re.IGNORECASE)
        
        nombre2 = clean_text(nom_m2.group(1)) if nom_m2 else ""
        apellidos2 = clean_text(ape_m2.group(1)) if ape_m2 else ""
        
        ip2_nombre_completo = clean_text(f"{nombre2} {apellidos2}")

    # --- 5. Equipo de investigación ---
    equipo_lista = []
    if sec_8_start != -1:
        bloque_equipo = text[sec_8_start:]
        # Los miembros suelen aparecer tras la etiqueta "MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:"
        # También buscamos en los bloques de "Datos personales" dentro de la sección 8 si la etiqueta principal falla
        miembros = re.findall(r'MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:\s*(.*?)(?=\n|Entidad|Rol|$)', bloque_equipo, re.IGNORECASE)
        
        for m in miembros:
            nombre_m = clean_text(m)
            # Filtramos nombres vacíos o que solo contienen "Datos personales" por error de captura
            if nombre_m and len(nombre_m) > 3 and "Datos personales" not in nombre_m:
                equipo_lista.append(nombre_m)

    # Si no se encontraron por la etiqueta de miembro, intentamos extraer por Nombre/Apellidos dentro de la Sec 8
    if not equipo_lista:
        # Buscar bloques de Nombre/Apellidos repetidos en la sección 8
        bloque_equipo_clean = re.split(r'Datos personales', bloque_equipo)
        for sub_bloque in bloque_equipo_clean[1:]: # Ignorar el primer fragmento antes del primer miembro
            n = re.search(r'Nombre:\s*(.*?)(?=\s*Apellidos:|\s*Correo|\n)', sub_bloque, re.IGNORECASE)
            a = re.search(r'Apellidos:\s*(.*?)(?=\s*Correo|\s*Fecha|\n)', sub_bloque, re.IGNORECASE)
            if n:
                full = clean_text(f"{n.group(1)} {a.group(1) if a else ''}")
                if full: equipo_lista.append(full)

    equipo_str = ", ".join(equipo_lista) if equipo_lista else ""

    return {
        "Referencia administrativa": referencia,
        "Título": titulo,
        "Nombre y apellidos del investigador/a principal": ip1_nombre_completo if ip1_nombre_completo else None,
        "Nombre y apellidos del investigador/a principal 2": ip2_nombre_completo if ip2_nombre_completo else "",
        "Nombre y apellidos del equipo de investigación": equipo_str
    }