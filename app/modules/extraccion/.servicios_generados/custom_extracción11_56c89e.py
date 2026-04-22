import fitz
import re

def extraer_datos(filename):
    """
    Extrae información específica de documentos de solicitud de proyectos
    utilizando un motor híbrido basado en etiquetas (anchors) y segmentación por secciones.
    """
    try:
        doc = fitz.open(filename)
    except Exception:
        return {
            "Referencia administrativa": None,
            "Título": None,
            "Nombre y apellidos del investigador/a principal": None,
            "Nombre y apellidos del investigador/a principal 2": None,
            "Nombre y apellidos del equipo de investigación": ""
        }

    text = ""
    for page in doc:
        text += page.get_text()

    # Normalización de caracteres y espacios para facilitar el regex
    text = text.replace('\xa0', ' ')
    
    # --- 1. Referencia administrativa ---
    # Se busca en los encabezados, etiqueta fija: "Referencia administrativa:"
    ref_match = re.search(r"Referencia administrativa:\s*([\w\-]+)", text)
    referencia = ref_match.group(1).strip() if ref_match else None

    # --- 2. Título ---
    # Se encuentra en la sección 2, usualmente entre "Título:" y la versión en inglés "Title:"
    titulo_match = re.search(r"Título:\s*(.*?)(?=\nTitle:|\nTitle\s|\nAcrónimo:|\nDuración)", text, re.DOTALL | re.IGNORECASE)
    titulo = " ".join(titulo_match.group(1).split()).strip() if titulo_match else None

    # --- Localización de Secciones ---
    # El documento tiene una estructura numerada fija. Usamos estos índices para delimitar búsquedas.
    idx_6 = text.find("6. Investigador/a Principal")
    idx_7 = text.find("7. Investigador/a Principal 2")
    idx_8 = text.find("8. Equipo de investigación")

    def limpiar_nombre(raw_text):
        if not raw_text:
            return None
        
        # CORRECCIÓN: Detectar y truncar el texto si contiene el patrón del pie de página.
        # Esto soluciona el problema de capturar texto basura en saltos de página.
        # El patrón de fecha/hora puede variar (con ':' o sin ellos), se hace flexible.
        footer_pattern = r'\d{2}/\d{2}/\d{4}\s+\d{2}[\s:]?\d{2}[\s:]?\d{2}\s+Página'
        footer_match = re.search(footer_pattern, raw_text)
        if footer_match:
            raw_text = raw_text[:footer_match.start()]
            
        # Eliminar la palabra "Apellidos", que a veces es capturada por el regex.
        res = re.sub(r'apellidos', '', raw_text, flags=re.IGNORECASE)
        # Reemplazar dos puntos y saltos de línea con espacios para unificar el nombre.
        res = res.replace(":", " ").replace("\n", " ")
        # Normalizar espacios múltiples.
        res = " ".join(res.split()).strip()
        return res if res else None

    # --- 3. Investigador Principal 1 (Sección 6) ---
    ip1 = None
    if idx_6 != -1:
        # Delimitamos el bloque de la sección 6
        fin_6 = idx_7 if idx_7 != -1 else (idx_8 if idx_8 != -1 else len(text))
        bloque_6 = text[idx_6:fin_6]
        # Buscamos el "Nombre:" dentro de este bloque, con un lookahead mejorado.
        nombre_6_match = re.search(r"Nombre:\s*(.*?)(?=\nCorreo|Correo Electrónico:|Fecha Nacimiento:|\nTipo de Documento:|Entidad del/de la)", bloque_6, re.DOTALL | re.IGNORECASE)
        if nombre_6_match:
            ip1 = limpiar_nombre(nombre_6_match.group(1))

    # --- 4. Investigador Principal 2 (Sección 7) ---
    ip2 = None
    if idx_7 != -1:
        # Delimitamos el bloque de la sección 7
        fin_7 = idx_8 if idx_8 != -1 else len(text)
        bloque_7 = text[idx_7:fin_7]
        # Regex con lookahead para detenerse en los campos subsiguientes
        nombre_7_match = re.search(r"Nombre:\s*(.*?)(?=\nCorreo|Correo Electrónico:|Fecha Nacimiento:|\nTipo de Documento:|País de residencia|Entidad del/de la)", bloque_7, re.DOTALL | re.IGNORECASE)
        if nombre_7_match:
            ip2 = limpiar_nombre(nombre_7_match.group(1))

    # --- 5. Equipo de investigación (Sección 8) ---
    equipo_lista = []
    if idx_8 != -1:
        # Buscamos desde el inicio de la sección 8 hasta el final del documento
        bloque_8 = text[idx_8:]
        
        # Estrategia ÚNICA y MEJORADA: Buscar etiquetas "Nombre:" dentro de la sección de equipo.
        # El lookahead se ha hecho más robusto para evitar capturar texto basura (headers/footers)
        # entre los datos de diferentes miembros del equipo.
        terminators = r'\nCorreo|\nFecha nacimiento|\nTipo de documento|\nPaís de residencia|\nDatos académicos|Currículum del/de la investigador/a'
        regex_equipo = fr"Nombre:\s*(.*?)(?={terminators})"
        
        nombres_iter = re.finditer(regex_equipo, bloque_8, re.DOTALL | re.IGNORECASE)
        for m in nombres_iter:
            candidato = limpiar_nombre(m.group(1))
            if candidato and candidato not in equipo_lista:
                # Evitar duplicar los IPs si aparecen listados aquí
                if candidato != ip1 and candidato != ip2:
                    equipo_lista.append(candidato)
        
        # Se elimina la Estrategia B anterior (buscar "MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:")
        # porque era propensa a errores y capturaba texto que no correspondía a un nombre.
        # La Estrategia A mejorada es mucho más fiable.

    equipo_final = ", ".join(equipo_lista) if equipo_lista else ""

    doc.close()

    return {
        "Referencia administrativa": referencia,
        "Título": titulo,
        "Nombre y apellidos del investigador/a principal": ip1,
        "Nombre y apellidos del investigador/a principal 2": ip2,
        "Nombre y apellidos del equipo de investigación": equipo_final
    }