import fitz
import re

# He elegido la librería fitz (PyMuPDF) porque la vista previa muestra que preserva 
# la estructura de etiquetas en línea (ej. "Nombre: ... Apellidos: ...") de forma 
# más coherente que la vista tabular, permitiendo el uso de expresiones regulares 
# potentes para capturar campos que no están estrictamente en tablas.

def extraer_datos(filename):
    # 1. Carga del documento y extracción de texto completo
    doc = fitz.open(filename)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()

    # 2. Lógica de extracción de campos
    
    # Referencia administrativa (Presente en cabeceras)
    ref_match = re.search(r"Referencia administrativa:\s*(PID\d+-\S+)", full_text)
    referencia = ref_match.group(1).strip() if ref_match else ""

    # Título del proyecto
    # Se busca el texto entre 'Título:' y el inicio del título en inglés 'Title:'
    titulo_match = re.search(r"Título:\s*(.+?)(?=\s*Title:)", full_text, re.DOTALL)
    titulo = " ".join(titulo_match.group(1).split()).strip() if titulo_match else ""

    # Segmentación por secciones para IPs (Evita cruces de datos entre IP1 e IP2)
    # Buscamos los bloques de texto específicos de cada IP
    sec_ip1 = ""
    sec_ip2 = ""
    sec_equipo = ""
    
    parts_ip1 = re.split(r"6\.\s*Investigador/a Principal", full_text)
    if len(parts_ip1) > 1:
        parts_ip2 = re.split(r"7\.\s*Investigador/a Principal 2", parts_ip1[1])
        sec_ip1 = parts_ip2[0]
        if len(parts_ip2) > 1:
            parts_equipo = re.split(r"8\.\s*Equipo de investigación", parts_ip2[1])
            sec_ip2 = parts_equipo[0]
            if len(parts_equipo) > 1:
                sec_equipo = parts_equipo[1]

    def extraer_nombre_apellidos(texto):
        # Captura el patrón "Nombre: [valor] Apellidos: [valor]"
        m = re.search(r"Nombre:\s*(.*?)\s*Apellidos[:\s]\s*(.*)", texto)
        if m:
            nombre = m.group(1).strip()
            # Limpieza de posibles etiquetas pegadas al final de apellidos
            apellidos = re.split(r"Correo Electrónico|Fecha Nacimiento|Sexo|NIF", m.group(2))[0].strip()
            full_name = f"{nombre} {apellidos}"
            return " ".join(full_name.split()) # Normalizar espacios
        return ""

    ip1_nombre = extraer_nombre_apellidos(sec_ip1)
    ip2_nombre = extraer_nombre_apellidos(sec_ip2)

    # Equipo de investigación - Miembros
    # Se buscan las ocurrencias después de la etiqueta específica de miembro
    miembros_encontrados = re.findall(r"MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:\s*\n?\s*([^\n\r]+)", full_text)
    
    # Limpieza de los nombres de los miembros
    miembros_limpios = []
    for m in miembros_encontrados:
        nombre_m = m.strip()
        if nombre_m and "Entidad" not in nombre_m:
            miembros_limpios.append(nombre_m)

    # 3. Construcción del diccionario de respuesta
    return {
        "Referencia administrativa": referencia,
        "Título del proyecto": titulo,
        "Investigador Principal 1 - Nombre y Apellidos": ip1_nombre,
        "Investigador Principal 2 - Nombre y Apellidos": ip2_nombre,
        "Equipo de investigación - Miembro 1": miembros_limpios[0] if len(miembros_limpios) > 0 else "",
        "Equipo de investigación - Miembro 2": miembros_limpios[1] if len(miembros_limpios) > 1 else ""
    }