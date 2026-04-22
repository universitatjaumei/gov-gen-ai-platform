
import sys
from pathlib import Path

project_root = Path(r"C:\Users\fabra\Documents\AutomatIA")
sys.path.insert(0, str(project_root))

print("Checking imports...")
try:
    from client_app.app.database.models import AtomRegistry
    print("✓ AtomRegistry found in models")
except ImportError as e:
    print(f"✗ AtomRegistry NOT found: {e}")

try:
    from client_app.app.database.models import Atom
    print("✓ Atom found in models (UNEXPECTED)")
except ImportError:
    print("✓ Atom NOT found in models (EXPECTED)")

try:
    print("Importing pdf_tools_atom_page...")
    from client_app.app.ui import pdf_tools_atom_page
    print("✓ pdf_tools_atom_page imported successfully")
except ImportError as e:
    print(f"✗ pdf_tools_atom_page import FAILED: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
