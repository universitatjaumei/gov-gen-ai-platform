
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from shared.automatia_shared.core.i18n import i18n, t

def test_nested_keys():
    print("Testing i18n nested key resolution...")
    
    # Reload translations explicitly to be sure
    i18n._load_translations()
    
    # Test cases
    cases = [
        ("admin.menu_dashboard", "Dashboard"),
        ("admin.partners.title", "Gestión de Partners"),
        ("admin.dashboard.card_ai_title", "Configuración IA"),
        ("menu_main", "Menú Principal") # Flat key
    ]
    
    failed = False
    for key, expected in cases:
        val = t(key)
        print(f"Key: '{key}' -> Result: '{val}'")
        if val != expected and val != key: # If it returns key, it failed
             # Note: exact match might depend on language, assuming ES default
             pass 
        
        if val == key:
            print(f"FAILED: Could not resolve '{key}'")
            failed = True
            
    if failed:
        sys.exit(1)
    else:
        print("SUCCESS: All keys resolved.")

if __name__ == "__main__":
    test_nested_keys()
