"""
AutomatIA Server Package

This package initialization ensures the shared library is available on the Python path.
"""
import sys
from pathlib import Path

# Add shared library to path
_project_root = Path(__file__).parent.parent
_shared_path = str(_project_root / 'shared')
if _shared_path not in sys.path:
    sys.path.insert(0, _shared_path)
