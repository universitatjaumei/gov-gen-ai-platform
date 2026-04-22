import json

file_path = r'c:\Users\fabra\Documents\AutomatIA\translations.json'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for lang in ['es', 'ca']:
    if lang in data:
        keys = list(data[lang].keys())
        # Since json.load overwrites duplicates, we need to check the file manually or use a customized parser
        print(f"Keys in {lang} (last win): {keys}")

# Let's use a parser that detects duplicates
def detect_duplicates(ordered_pairs):
    res = {}
    for k, v in ordered_pairs:
        if k in res:
            print(f"DUPLICATE KEY FOUND: {k}")
        res[k] = v
    return res

with open(file_path, 'r', encoding='utf-8') as f:
    print("Checking for duplicates in entire file...")
    json.load(f, object_pairs_hook=detect_duplicates)
