import fitz
import re

def extraer_datos(filename):
    """
    Extrae campos específicos de documentos de Proyectos de Generación de Conocimiento 
    utilizando una estrategia basada exclusivamente en etiquetas (anchors).
    """
    doc = fitz.open(filename)
    text = ""
    for page in doc:
        text += page.get_text()

    # Función auxiliar para limpiar nombres y eliminar el ruido de los dos puntos del PDF
    def limpiar_valor(val):
        if not val:
            return ""
        # CORRECCIÓN: Se invierte el orden de las operaciones para solucionar el feedback.
        # 1. Primero se eliminan los dos puntos. Esto es crucial para dos casos:
        #    a) Nombres largos que el PDF separa con ":", como "Nombre A: Nombre B".
        #    b) La etiqueta "Apellidos:", que al quitarle el ":" se convierte en "Apellidos"
        #       y puede ser eliminada en el siguiente paso.
        val = val.replace(":", " ")

        # 2. Se elimina la palabra "Apellidos" que a veces se intercala. Se usa una expresión
        #    regular más robusta con límites de palabra (\b) para evitar coincidencias no deseadas.
        val = re.sub(r'\bApellidos\b', ' ', val, flags=re.IGNORECASE)
        
        # 3. Se normalizan todos los espacios (incluyendo saltos de línea y espacios múltiples
        #    resultantes de los reemplazos) para obtener una cadena limpia y unificada.
        return " ".join(val.split())

    # 1. Referencia administrativa
    # Se busca la etiqueta y se captura el código alfanumérico que le sigue.
    ref_match = re.search(r"Referencia\s+administrativa:\s*([\w-]+)", text)
    referencia = ref_match.group(1) if ref_match else None

    # 2. Título
    # Se busca en la sección 2, entre "Título:" y la siguiente etiqueta técnica ("Title:" o "Acrónimo:")
    titulo_match = re.search(r"Título:\s*(.+?)(?=\n\s*Title:|\n\s*Acrónimo:)", text, re.S)
    titulo = limpiar_valor(titulo_match.group(1)) if titulo_match else ""

    # 3. Nombre y apellidos del investigador/a principal (Sección 6)
    ip1 = ""
    # Delimitamos la búsqueda a la sección 6 para evitar colisiones
    sec6_match = re.search(r"6\.\s*Investigador/a\s*Principal(.*?)(?=7\.\s*Investigador/a|$)", text, re.S)
    if sec6_match:
        sec6_text = sec6_match.group(1)
        # El nombre suele venir después de 'Nombre:' y antes de los datos de contacto
        nombre_ip1_match = re.search(r"Nombre:\s*(.*?)(?=\n\s*Correo|\n\s*Fecha|\n\s*Nacionalidad)", sec6_text, re.S)
        if nombre_ip1_match:
            ip1 = limpiar_valor(nombre_ip1_match.group(1))

    # 4. Nombre y apellidos del investigador/a principal 2 (Sección 7)
    ip2 = ""
    sec7_match = re.search(r"7\.\s*Investigador/a\s*Principal\s*2(.*?)(?=8\.\s*Equipo|$)", text, re.S)
    if sec7_match:
        sec7_text = sec7_match.group(1)
        nombre_ip2_match = re.search(r"Nombre:\s*(.*?)(?=\n\s*Correo|\n\s*Fecha|\n\s*Nacionalidad)", sec7_text, re.S)
        if nombre_ip2_match:
            ip2 = limpiar_valor(nombre_ip2_match.group(1))

    # 5. Nombre y apellidos del equipo de investigación (Sección 8)
    # Extraemos todos los bloques que comiencen con la etiqueta de miembro
    equipo_list = []
    if "8. Equipo de investigación" in text:
        # Se busca el texto desde el inicio de la sección 8 hasta el final del documento o la siguiente sección principal (ej. 9.)
        sec8_text_match = re.search(r"8\.\s*Equipo\s*de\s*investigación(.*?)(?=\n\d+\.\s*|$)", text, re.S)
        sec8_text = sec8_text_match.group(1) if sec8_text_match else ""

        # Buscamos cada ocurrencia de miembro del equipo.
        # El patrón captura el contenido de la línea de "Nombre:" hasta el siguiente salto de línea.
        bloques_miembros = re.findall(r"MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:.*?Nombre:\s*([^\n]+)", sec8_text, re.S)
        
        for bloque in bloques_miembros:
            nombre_limpio = limpiar_valor(bloque)
            if nombre_limpio and nombre_limpio not in equipo_list:
                # Evitamos duplicar si el IP está listado también aquí (común en ciertos formatos)
                if nombre_limpio != ip1 and nombre_limpio != ip2:
                    equipo_list.append(nombre_limpio)

    return {
        "Referencia administrativa": referencia,
        "Título": titulo,
        "Nombre y apellidos del investigador/a principal": ip1 if ip1 else None,
        "Nombre y apellidos del investigador/a principal 2": ip2 if ip2 else "",
        "Nombre y apellidos del equipo de investigación": ", ".join(equipo_list) if equipo_list else ""
    }