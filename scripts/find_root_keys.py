import json

file_path = r'c:\Users\fabra\Documents\AutomatIA\translations.json'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.startswith('    "'):
        print(f"L{i+1}: {line.strip()}")
