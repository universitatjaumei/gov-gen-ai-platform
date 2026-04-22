import json
import os

file_path = r'c:\Users\fabra\Documents\AutomatIA\translations.json'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Find lines starting with 4 spaces and a quote
for i, line in enumerate(lines):
    if line.startswith('    "'):
        # Check if it's a known language key
        is_lang = False
        for lang in ['es', 'ca', 'en']:
            if f'"{lang}":' in line:
                is_lang = True
                break
        
        if not is_lang:
            print(f"L{i+1}: {line.strip()}")
