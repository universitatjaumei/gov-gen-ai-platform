
import re
from typing import List, Dict, Any, Optional

# Patrones para detectar operaciones deterministas en lenguaje natural
# Clave: tipo de operación (coincide con TransformOperation.type)
# Valor: Lista de patrones regex (se compilarán)
DETECTION_PATTERNS = {
    'drop_columns': [
        r'elimina(r)?\s+((la|las)\s+)?columna(s)?',
        r'borra(r)?\s+((la|las)\s+)?columna(s)?',
        r'quita(r)?\s+((la|las)\s+)?columna(s)?',
        r'drop\s+column(s)?',
        r'remove\s+column(s)?'
    ],
    'rename_columns': [
        r'renombra(r)?\s+((la|las)\s+)?columna(s)?',
        r'cambia(r)?\s+(el\s+)?nombre\s+de',
        r'rename\s+column(s)?'
    ],
    'merge_columns': [
        r'une(r)?\s+(las\s+)?columna(s)?',
        r'combina(r)?\s+(las\s+)?columna(s)?',
        r'junta(r)?\s+(las\s+)?columna(s)?',
        r'merge\s+column(s)?',
        r'concatena(r)?'
    ],
    'format_dates': [
        r'formato\s+de\s+fecha',
        r'convierte\s+(la\s+)?fecha',
        r'cambia(r)?\s+(el\s+)?formato',
        r'format\s+date(s)?'
    ],
    'filter_rows': [
        r'filtra(r)?\s+(las\s+)?fila(s)?',
        r'elimina(r)?\s+(las\s+)?fila(s)?\s+donde',
        r'mant(en|ener)\s+solo',
        r'filter\s+row(s)?'
    ],
    'replace_values': [
        r'reemplaza(r)?\s+(los\s+)?valor(es)?',
        r'sustituy(e|ir)\s+',
        r'cambia(r)?\s+valor(es)?',
        r'replace\s+value(s)?'
    ],
    'normalize_text': [
        r'normaliza(r)?\s+(el\s+)?texto',
        r'a\s+mayuscula(s)?',
        r'a\s+minuscula(s)?',
        r'quita(r)?\s+espacios',
        r'trim',
        r'uppercase',
        r'lowercase'
    ],
    'fill_nulls': [
        r'rellena(r)?\s+(los\s+)?(nulos|vacios)',
        r'reemplaza(r)?\s+(los\s+)?(nulos|vacios)',
        r'fill\s+null(s)?',
        r'fill\s+nan'
    ],
    'remove_duplicates': [
        r'elimina(r)?\s+(los\s+)?duplicado(s)?',
        r'quita(r)?\s+(los\s+)?duplicado(s)?',
        r'borra(r)?\s+(los\s+)?duplicado(s)?',
        r'remove\s+duplicate(s)?',
        r'drop\s+duplicate(s)?',
        r'deduplicate'
    ],
    'remove_null_rows': [
        r'elimina(r)?\s+(las\s+)?filas\s+(nulas|vacias)',
        r'quita(r)?\s+(las\s+)?filas\s+(nulas|vacias)',
        r'remove\s+null\s+row(s)?',
        r'drop\s+na',
        r'drop\s+null(s)?'
    ]
}

def detect_potential_operations(instruction: str) -> List[Dict[str, str]]:
    """
    Analiza una instrucción en lenguaje natural y detecta posibles operaciones deterministas.
    
    Args:
        instruction: Texto de la instrucción del usuario.
        
    Returns:
        Lista de diccionarios con 'type' (tipo de operación) y 'match' (texto coincidente).
    """
    if not instruction:
        return []
    
    found_ops = []
    instruction_lower = instruction.lower()
    
    for op_type, patterns in DETECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, instruction_lower):
                found_ops.append({
                    'type': op_type,
                    'label': _get_op_label(op_type)
                })
                break # Solo reportar una vez por tipo de operación
                
    return found_ops

def _get_op_label(op_type: str) -> str:
    """Devuelve un nombre legible para el tipo de operación."""
    # Esto podría estar en un shared enum o config
    labels = {
        'drop_columns': 'Eliminar Columnas',
        'rename_columns': 'Renombrar Columnas',
        'merge_columns': 'Unir Columnas',
        'format_dates': 'Formato de Fechas',
        'filter_rows': 'Filtrar Filas',
        'replace_values': 'Reemplazar Valores',
        'normalize_text': 'Normalizar Texto',
        'fill_nulls': 'Rellenar Nulos',
        'remove_duplicates': 'Eliminar Duplicados',
        'remove_null_rows': 'Eliminar Filas Nulas'
    }
    return labels.get(op_type, op_type)
