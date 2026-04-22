import pdfplumber
import re
import pandas as pd

# Se elige pdfplumber por su capacidad superior para procesar tablas (como los indicadores en las páginas 6 y 7)
# y para mantener la coherencia de los pares clave-valor en formularios de convocatorias públicas.

def extraer_datos(filename):
    # Diccionario para almacenar los campos requeridos
    data = {}
    
    with pdfplumber.open(filename) as pdf:
        # Extraemos el texto de las páginas clave
        paginas_texto = [p.extract_text() for p in pdf.pages]
        full_content = "\n".join(paginas_texto)

        # 1. Entidad Solicitante, CIF y Referencia Administrativa (Página 1)
        data['Entidad Solicitante'] = re.search(r"Entidad:\s*(UNIVERSITAT.*?)\n", paginas_texto[0]).group(1).strip()
        data['CIF'] = re.search(r"CIF:\s*([A-Z0-9]+)", paginas_texto[0]).group(1).strip()
        data['Referencia Administrativa'] = re.search(r"Referencia administrativa:\s*([\w-]+)", paginas_texto[0]).group(1).strip()

        # 2. Título del Proyecto y Acrónimo (Página 2)
        data['Título del Proyecto'] = re.search(r"Título:\s*(.*?)\nTitle:", paginas_texto[1], re.S).group(1).strip()
        data['Acrónimo'] = re.search(r"Acrónimo:\s*(.*)", paginas_texto[1]).group(1).strip()

        # 3. Resumen / Summary (Página 3)
        res_es = re.search(r"Resumen:\s*(.*?)\nSummary:", paginas_texto[2], re.S).group(1).strip()
        res_en = re.search(r"Summary:\s*(.*?)\nImpacto científico", paginas_texto[2], re.S).group(1).strip()
        data['Resumen / Summary'] = f"ES: {res_es[:200]}... | EN: {res_en[:200]}..."

        # 4. Datos IP (Investigador Principal) y Vinculación (Página 8)
        ip_nom = re.search(r"Nombre:\s*(.*?)\s*Apellidos:", paginas_texto[7]).group(1).strip()
        ip_ape = re.search(r"Apellidos:\s*(.*?)\n", paginas_texto[7]).group(1).strip()
        data['Datos IP (Investigador Principal)'] = f"{ip_nom} {ip_ape}"
        
        vinculacion = re.search(r"Vinculación con su entidad.*?\):\s*(.*?)\n", paginas_texto[7])
        data['Vinculación con Entidad'] = vinculacion.group(1).strip() if vinculacion else "Funcionario"

        # 5. Integración de Género (IAGI) (Página 4)
        iagi = re.search(r"Resuma brevemente cómo ha contemplado.*?IAGI.*?\n(.*?)\n¿La entidad", paginas_texto[3], re.S)
        data['Integración de Género (IAGI)'] = iagi.group(1).strip() if iagi else "No detallado"

        # 6. CV Narrativo (Página 9 - IP1)
        cv_narr = re.search(r"Resumen del CV:\s*(.*?)(?:\d{2}/\d{2}/\d{4}|$)", paginas_texto[8], re.S)
        data['CV Narrativo'] = cv_narr.group(1).strip() if cv_narr else "No encontrado"

        # 7. Conteo Investigadores (Página 6 - Tabla Indicadores)
        # Hombres
        h_count = re.search(r"¿Hay investigadores HOMBRES.*?¿Cuántos investigadores\?\s*(\d+)", paginas_texto[5], re.S)
        data['Conteo Investigadores Hombres'] = h_count.group(1) if h_count else "0"
        # Mujeres
        m_count = re.search(r"¿Hay investigadoras MUJERES.*?¿Cuántas investigadoras\?\s*(\d+)", paginas_texto[5], re.S)
        data['Conteo Investigadoras Mujeres'] = m_count.group(1) if m_count else "0"

        # 8. Tesis Doctorales (Páginas 6 y 7)
        tesis_marcha = re.search(r"tesis doctorales en marcha.*?\s*(\d+)", paginas_texto[5])
        tesis_previstas = re.search(r"tesis doctorales a desarrollar.*?\s*(\d+)", paginas_texto[6])
        data['Tesis Doctorales'] = f"En marcha: {tesis_marcha.group(1) if tesis_marcha else 0}, Previstas: {tesis_previstas.group(1) if tesis_previstas else 0}"

        # 9. Resultados Previstos: Publicaciones (Página 7)
        rev_idx = re.search(r"publicaciones en revistas indexadas\s*(\d+)", paginas_texto[6])
        libros = re.search(r"publicaciones en LIBROS\s*(\d+)", paginas_texto[6])
        cong_int = re.search(r"publicaciones CONGRESOS INTERNACIONALES\s*(\d+)", paginas_texto[6])
        data['Resultados Previstos: Publicaciones'] = f"Revistas: {rev_idx.group(1) if rev_idx else 0}, Libros: {libros.group(1) if libros else 0}, Congresos Int: {cong_int.group(1) if cong_int else 0}"

        # 10. Instrumentos de Protección (Página 7)
        patentes = re.search(r"Número de patentes\s*(\d+)", paginas_texto[6])
        acuerdos = re.search(r"acuerdos de transferencia.*?\s*(\d+)", paginas_texto[6])
        data['Instrumentos de Protección'] = f"Patentes: {patentes.group(1) if patentes else 0}, Transferencia: {acuerdos.group(1) if acuerdos else 0}"

        # 11. Miembros del Equipo Externos (Página 11)
        # Se busca a Beatriz García Ortega de la UPV
        ext_matches = re.findall(r"MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:\s*(.*?)\n.*?Entidad:\s*(.*?)\n", full_content, re.S)
        externos = [f"{m[0].strip()} ({m[1].strip()})" for m in ext_matches if "UNIVERSITAT JAUME I" not in m[1]]
        data['Miembros del Equipo Externos'] = ", ".join(externos) if externos else "Ninguno"

    # Generación de archivo de salida
    # Generación de archivo de salida
    # df = pd.DataFrame([data])
    # df.to_excel('resultado.xlsx', index=False) # ❌ prohibido por seguridad (AST)
    
    return data