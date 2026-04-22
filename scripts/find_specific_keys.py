import re

file_path = r'c:\Users\fabra\Documents\AutomatIA\translations.json'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '"common": {' in line:
        # Check indentation
        indent = len(line) - len(line.lstrip())
        print(f"L{i+1}: Indent={indent}: {line.strip()}")

for i, line in enumerate(lines):
    if '"export_pkg": {' in line:
        indent = len(line) - len(line.lstrip())
        print(f"L{i+1}: Indent={indent}: {line.strip()}")
