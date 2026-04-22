import re

file_path = r'c:\Users\fabra\Documents\AutomatIA\translations.json'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    # Match strings starting with 8 spaces and a key in quotes
    match = re.match(r'^        "([^"]+)":', line)
    if match:
        key = match.group(1)
        print(f"L{i+1}: {key}")
