import json

file_path = r'c:\Users\fabra\Documents\AutomatIA\translations.json'

def check_duplicates(ordered_pairs, path=""):
    d = {}
    for k, v in ordered_pairs:
        current_path = f"{path}.{k}" if path else k
        if k in d:
            print(f"Duplicate key found at root LEVEL? No, key: {k} in {path or 'root'}")
        d[k] = v
    return d

def dict_hook(ordered_pairs):
    return check_duplicates(ordered_pairs)

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        # Standard json.load doesn't easily track path in object_pairs_hook without recursion
        # But we can see if it's at 'root' level.
        data = f.read()
        
        # Simple recursion for path tracking
        def parse_obj(pairs):
            d = {}
            for k, v in pairs:
                if k in d:
                    print(f"Duplicate '{k}' found in object.")
                d[k] = v
            return d

        json.loads(data, object_pairs_hook=parse_obj)
except Exception as e:
    print(f"Error: {e}")
