
import re

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
    'format_dates': [
        r'formato\s+de\s+fecha',
        r'convierte\s+(la\s+)?fecha',
        r'cambia(r)?\s+(el\s+)?formato',
        r'format\s+date(s)?'
    ],
}

text = "Quiero eliminar la columna email y renombrar la columna nombre a cliente. También cambia el formato de fecha."
text_lower = text.lower()

found = []
for op, patterns in DETECTION_PATTERNS.items():
    for p in patterns:
        if re.search(p, text_lower):
            found.append(op)
            break

print(f"TEXT: {text_lower}")
print(f"FOUND: {found}")
