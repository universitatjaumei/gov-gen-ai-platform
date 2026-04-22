import json
import sys

file_path = r'c:\Users\fabra\Documents\AutomatIA\translations.json'

def detect_duplicates(ordered_pairs):
    res = {}
    for k, v in ordered_pairs:
        if k in res:
            print(f"DUPLICATE KEY FOUND: {k}")
            # sys.stderr.write(f"DUPLICATE KEY FOUND: {k}\n")
        res[k] = v
    return res

print(f"Opening {file_path}")
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        print("File opened, loading JSON...")
        data = json.load(f, object_pairs_hook=detect_duplicates)
        print("JSON loaded successfully")
except Exception as e:
    print(f"An error occurred: {e}")
    sys.exit(1)
