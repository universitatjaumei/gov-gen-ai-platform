import fitz
import re

def extraer_datos(filename):
    """
    Extrae campos específicos de documentos PDF de solicitudes de proyectos 
    de generación de conocimiento utilizando etiquetas fijas como anclas.
    """
    # Abrir el documento y extraer todo el texto
    doc = fitz.open(filename)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    
    # Helper para normalizar espacios y limpiar ruidos de extracción
    def limpiar_texto(txt):
        if not txt:
            return ""
        # Colapsar múltiples espacios y saltos de línea
        txt = re.sub(r'\s+', ' ', txt)
        # Eliminar posibles dos puntos residuales al final del nombre/valor
        txt = re.sub(r'[:\s]+$', '', txt)
        return txt.strip()

    # --- 1. Referencia administrativa ---
    # Se busca la etiqueta en el encabezado de las páginas
    ref_match = re.search(r'Referencia\s+administrativa:\s*([\w-]+)', full_text, re.IGNORECASE)
    referencia = ref_match.group(1) if ref_match else None

    # --- 2. Título ---
    # Se extrae basándose en la etiqueta Título: y se cierra con Title: (versión inglés) o Acrónimo:
    titulo_match = re.search(r'Título:\s*(.*?)(?=\s*Title:|\s*Acrónimo:)', full_text, re.IGNORECASE | re.DOTALL)
    titulo = limpiar_texto(titulo_match.group(1)) if titulo_match else ""

    # --- 3. Nombre y apellidos del investigador/a principal (IP1) ---
    # Delimitamos la búsqueda a la Sección 6 para evitar capturar nombres de IP2 o equipo
    ip1 = ""
    sec6_match = re.search(r'6\.\s*Investigador/a\s+Principal(.*?)(?=(?:7|8)\.\s*(?:Investigador|Interrupciones|Equipo)|$)', full_text, re.IGNORECASE | re.DOTALL)
    if sec6_match:
        sec6_text = sec6_match.group(1)
        # Dentro de la sección, buscamos el campo Nombre:
        ip1_match = re.search(r'Nombre:\s*(.*?)(?=\s*Correo|\s*Fecha|\s*Nacionalidad|\s*Tipo|\s*Documento)', sec6_text, re.IGNORECASE | re.DOTALL)
        if ip1_match:
            raw_name = ip1_match.group(1)
            # FIX: Eliminar la palabra "Apellidos" (con o sin dos puntos) que a veces
            # se intercala erróneamente entre el nombre y los apellidos durante la extracción.
            processed_name = re.sub(r'\s+Apellidos:?\s+', ' ', raw_name, flags=re.IGNORECASE)
            ip1 = limpiar_texto(processed_name)

    # --- 4. Nombre y apellidos del investigador/a principal 2 (IP2) ---
    # Delimitamos la búsqueda a la Sección 7
    ip2 = ""
    sec7_match = re.search(r'7\.\s*Investigador/a\s+Principal\s+2(.*?)(?=8\.\s*Equipo|$)', full_text, re.IGNORECASE | re.DOTALL)
    if sec7_match:
        sec7_text = sec7_match.group(1)
        ip2_match = re.search(r'Nombre:\s*(.*?)(?=\s*Correo|\s*Fecha|\s*Nacionalidad|\s*Tipo|\s*Documento)', sec7_text, re.IGNORECASE | re.DOTALL)
        if ip2_match:
            raw_name = ip2_match.group(1)
            # FIX: Aplicar la misma corrección que para el IP1.
            processed_name = re.sub(r'\s+Apellidos:?\s+', ' ', raw_name, flags=re.IGNORECASE)
            ip2 = limpiar_texto(processed_name)

    # --- 5. Nombre y apellidos del equipo de investigación ---
    # Extraemos todos los bloques bajo la Sección 8
    equipo_str = ""
    sec8_match = re.search(r'8\.\s*Equipo\s+de\s+investigación(.*)', full_text, re.IGNORECASE | re.DOTALL)
    if sec8_match:
        sec8_text = sec8_match.group(1)
        # Buscamos todas las ocurrencias de "Nombre:" dentro de esta sección
        # Los límites suelen ser los campos siguientes como Correo, Fecha o indicadores de pie de página (fechas de impresión)
        nombres_miembros = re.findall(r'Nombre:\s*(.*?)(?=\s*Correo|\s*Fecha|\s*Nacionalidad|\s*Datos|\s*Tipo|\s*Página|\s*\d{2}/\d{2}/\d{4})', sec8_text, re.IGNORECASE | re.DOTALL)
        
        lista_final = []
        for n in nombres_miembros:
            # FIX: Aplicar la misma corrección que para los IPs a cada miembro del equipo.
            processed_name = re.sub(r'\s+Apellidos:?\s+', ' ', n, flags=re.IGNORECASE)
            nombre_limpio = limpiar_texto(processed_name)
            # Evitar duplicados y entradas vacías
            if nombre_limpio and nombre_limpio not in lista_final:
                lista_final.append(nombre_limpio)
        
        equipo_str = ", ".join(lista_final)

    # Devolver el diccionario con los campos extraídos
    return {
        "Referencia administrativa": referencia,
        "Título": titulo,
        "Nombre y apellidos del investigador/a principal": ip1,
        "Nombre y apellidos del investigador/a principal 2": ip2,
        "Nombre y apellidos del equipo de investigación": equipo_str
    }