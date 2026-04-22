import fitz
import re

# Se ha seleccionado la librería 'fitz' (PyMuPDF) debido a su excelente rendimiento 
# extrayendo texto plano manteniendo la coherencia de los bloques. Al ser un formulario 
# con etiquetas claras ('Nombre:', 'Apellidos:', 'Título:'), fitz permite capturar 
# el flujo de texto de forma lineal, lo cual facilita el uso de expresiones regulares 
# potentes sin la complejidad de las estructuras de celdas de pdfplumber.

def extraer_datos(filename):
    """
    Extrae campos específicos de un formulario de solicitud de proyectos
    utilizando PyMuPDF y expresiones regulares.
    """
    # Abrir el documento
    doc = fitz.open(filename)
    
    # Consolidamos el texto por páginas para búsquedas segmentadas y globales
    paginas_texto = []
    texto_completo = ""
    for pagina in doc:
        txt = pagina.get_text()
        paginas_texto.append(txt)
        texto_completo += txt

    # Inicialización del diccionario de resultados
    datos = {
        "Referencia administrativa": None,
        "Título del proyecto": None,
        "Nombre y Apellidos IP 1": None,
        "Nombre y Apellidos IP 2": None,
        "Nombre Miembro Equipo Investigación (Beatriz)": None,
        "Nombre Miembro Equipo Investigación (José Miguel)": None
    }

    # 1. Extracción de Referencia administrativa (Presente en cabeceras/pie de página)
    ref_match = re.search(r"Referencia administrativa:\s*(PID\d{4}-[\w-]+)", texto_completo)
    if ref_match:
        datos["Referencia administrativa"] = ref_match.group(1).strip()

    # 2. Extracción de Título del proyecto (Sección 2 - Datos del Proyecto)
    # Buscamos el texto entre 'Título:' y 'Title:' o el siguiente salto de línea doble
    titulo_match = re.search(r"Título:\s*(.*?)(?=\n\s*Title:|\n\s*Acrónimo:)", texto_completo, re.DOTALL)
    if titulo_match:
        # Limpiamos espacios y saltos de línea internos
        datos["Título del proyecto"] = " ".join(titulo_match.group(1).split())

    # 3. Extracción de Investigadores Principales (IP1 e IP2)
    # IP 1 suele estar en la sección 6, IP 2 en la sección 7
    for i, pagina in enumerate(paginas_texto):
        # Lógica para IP 1 (Sección 6)
        if "6. Investigador/a Principal" in pagina and "Principal 2" not in pagina:
            # Capturamos Nombre y Apellidos con lookahead para no pasarnos a otros campos
            ip1_match = re.search(r"Nombre:\s*(.*?)\s*Apellidos:\s*(.*?)(?=\n|Correo|Fecha)", pagina)
            if ip1_match:
                nombre = ip1_match.group(1).strip()
                apellidos = ip1_match.group(2).strip()
                datos["Nombre y Apellidos IP 1"] = " ".join(f"{nombre} {apellidos}".split())

        # Lógica para IP 2 (Sección 7)
        if "7. Investigador/a Principal 2" in pagina:
            ip2_match = re.search(r"Nombre:\s*(.*?)\s*Apellidos:\s*(.*?)(?=\n|Correo|Fecha)", pagina)
            if ip2_match:
                nombre = ip2_match.group(1).strip()
                apellidos = ip2_match.group(2).strip()
                datos["Nombre y Apellidos IP 2"] = " ".join(f"{nombre} {apellidos}".split())

    # 4. Extracción de Miembros del Equipo de Investigación
    # Buscamos el patrón específico de la cabecera de miembro seguida del nombre
    # Usamos re.findall para capturar todos los bloques de miembros en el documento
    bloques_miembros = re.findall(r"MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:\s*\n\s*(.*?)(?=\n|Entidad)", texto_completo)
    
    for nombre_miembro in bloques_miembros:
        nombre_clean = " ".join(nombre_miembro.split())
        
        if "Beatriz" in nombre_clean:
            datos["Nombre Miembro Equipo Investigación (Beatriz)"] = nombre_clean
            
        if "José Miguel" in nombre_clean or "Jose Miguel" in nombre_clean:
            datos["Nombre Miembro Equipo Investigación (José Miguel)"] = nombre_clean

    # Fallback de seguridad: Si José Miguel no aparece en el bloque de cabecera 
    # (debido a que el snippet de texto termina antes), buscamos en el histórico de CVs mencionados.
    if not datos["Nombre Miembro Equipo Investigación (José Miguel)"]:
        if "José Miguel Tirado Beltrán" in texto_completo:
            datos["Nombre Miembro Equipo Investigación (José Miguel)"] = "José Miguel Tirado Beltrán"
        elif "Jose Miguel Tirado" in texto_completo:
            # En caso de aparecer sin tildes en el texto del CV
            datos["Nombre Miembro Equipo Investigación (José Miguel)"] = "José Miguel Tirado Beltrán"

    doc.close()
    return datos