import fitz
import re

def clean_name(raw_name: str) -> str:
    """
    Cleans a raw name string by removing extra content that might follow it.
    It handles cases where name parts are separated by colons or contain extraneous
    labels like "Apellidos", which can occur due to PDF layout issues. It first
    truncates the string at known field separators like "Correo electrónico", then
    replaces colons and removes the word "Apellidos", and finally normalizes whitespace.
    """
    if not raw_name:
        return ""

    # Stop at markers that are very likely to indicate the end of a name field
    name = re.split(r'correo electrónico|fecha nacimiento', raw_name, 1, flags=re.IGNORECASE)[0]
    
    # Replace colons with spaces, as they sometimes separate parts of a name in the source PDF
    name = name.replace(':', ' ')
    
    # Remove the word "Apellidos" when it appears as an extraneous label, based on error reports.
    # Using word boundaries (\b) to avoid removing the substring from a real name.
    name = re.sub(r'\bApellidos\b', '', name, flags=re.IGNORECASE)
    
    # Normalize all whitespace (multiple spaces, newlines) to a single space and strip
    cleaned_name = re.sub(r'\s+', ' ', name).strip()
    
    return cleaned_name

def extraer_datos(filename: str) -> dict:
    """
    Extracts administrative and research data from a project proposal PDF.

    Args:
        filename: The path to the PDF file.

    Returns:
        A dictionary containing the extracted fields.
    """
    data = {
        'Referencia administrativa': "",
        'Título': "",
        'Nombre y apellidos del investigador/a principal': "",
        'Nombre y apellidos del investigador/a principal 2': "",
        'Nombre y apellidos del equipo de investigación': ""
    }
    
    try:
        doc = fitz.open(filename)
        # Concatenate text from all pages into a single string for easier regex matching
        text = "".join(page.get_text() for page in doc)
    except Exception:
        # Handle cases where the file might be corrupted, not found, or not a PDF
        return data

    # 1. Referencia administrativa: Found in the header of pages.
    # Anchor: "Referencia administrativa:"
    ref_match = re.search(r"Referencia administrativa:\s*([\w-]+)", text)
    if ref_match:
        data['Referencia administrativa'] = ref_match.group(1).strip()

    # 2. Título: Found in section 2, between "Título:" and "Title:".
    # Anchor: "Título:"
    titulo_match = re.search(r"Título:\s*(.*?)\n\s*Title:", text, re.DOTALL)
    if titulo_match:
        titulo = titulo_match.group(1)
        data['Título'] = re.sub(r'\s+', ' ', titulo).strip()

    # 3. Nombre y apellidos del investigador/a principal (Sección 6)
    # Anchor: Section "6. Investigador/a Principal" and label "Nombre:"
    # We isolate the section to avoid capturing 'Nombre:' from other parts of the document.
    section_6_match = re.search(r"\n\s*6\.\s*Investigador/a\s*Principal\s*([\s\S]*?)\n\s*7\.\s", text, re.DOTALL)
    if section_6_match:
        section_6_text = section_6_match.group(1)
        name_match = re.search(r"Nombre:\s*(.*?)(?:\n|$)", section_6_text)
        if name_match:
            data['Nombre y apellidos del investigador/a principal'] = clean_name(name_match.group(1))

    # 4. Nombre y apellidos del investigador/a principal 2 (Sección 7)
    # Anchor: Section "7. Investigador/a Principal 2" and label "Nombre:"
    # This section is optional.
    section_7_match = re.search(r"\n\s*7\.\s*Investigador/a\s*Principal\s*2\s*([\s\S]*?)\n\s*8\.\s", text, re.DOTALL)
    if section_7_match:
        section_7_text = section_7_match.group(1)
        name_match = re.search(r"Nombre:\s*(.*?)(?:\n|$)", section_7_text)
        if name_match:
            data['Nombre y apellidos del investigador/a principal 2'] = clean_name(name_match.group(1))

    # 5. Nombre y apellidos del equipo de investigación (Sección 8)
    # Anchor: Section "8. Equipo de investigación" and repeating blocks starting with "MIEMBRO..."
    # This section may contain multiple members.
    section_8_match = re.search(r"\n\s*8\.\s*Equipo de investigación([\s\S]*)", text, re.DOTALL)
    if section_8_match:
        section_8_text = section_8_match.group(1)
        
        # Find all name lines that are preceded by a "MIEMBRO" block.
        raw_names = re.findall(r"MIEMBRO DEL EQUIPO DE INVESTIGACIÓN:[\s\S]*?Nombre:\s*(.*?)(?:\n|$)", section_8_text)
        
        # Clean each found name and filter out any empty results.
        cleaned_names = [clean_name(name) for name in raw_names if clean_name(name)]
        
        if cleaned_names:
            data['Nombre y apellidos del equipo de investigación'] = ", ".join(cleaned_names)
            
    return data