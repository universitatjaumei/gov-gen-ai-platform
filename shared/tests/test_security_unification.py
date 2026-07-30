import pytest
import ast
import os
from automatia_shared.core.security import audit_code, SecurityException, validate_code_ast

def test_fitz_and_pdfplumber_are_safe():
    """Validar que un código con import fitz y import pdfplumber sea marcado como SAFE."""
    code = """
import fitz
import pdfplumber

def process(file):
    doc = fitz.open(file)
    with pdfplumber.open(file) as pdf:
        pass
    return True
"""
    result = audit_code(code)
    assert result['status'] == 'SAFE', f"Errors found: {result['reasons']}"

def test_pymupdf_is_not_in_any_whitelist():
    """Verificar que el nombre 'PyMuPDF' ya no existe en ninguna de las listas blancas."""
    # 1. Check shared/automatia_shared/core/security.py
    shared_security_path = os.path.abspath("shared/automatia_shared/core/security.py")
    with open(shared_security_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "PyMuPDF" not in content, "PyMuPDF found in shared/automatia_shared/core/security.py"

    # 2. Check client_app/app/services/sandbox_service.py
    sandbox_service_path = os.path.abspath("client_app/app/services/sandbox_service.py")
    with open(sandbox_service_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "PyMuPDF" not in content, "PyMuPDF found in client_app/app/services/sandbox_service.py"

def test_openpyxl_is_allowed_for_pandas():
    """Confirmar que pandas y openpyxl están permitidos."""
    # indirect check via audit_code
    code = "import pandas\nimport openpyxl\ndf = pandas.read_excel('test.xlsx')"
    result = audit_code(code)
    assert result['status'] == 'SAFE'

def test_sandbox_allowed_imports_contains_fitz_and_pdfplumber():
    """Verificar que sandbox_service tiene los nuevos imports permitidos."""
    from client_app.app.services.sandbox_service import neutralize_dangerous_functions
    import builtins
    
    # We can't easily call neutralize_dangerous_functions safely here without side effects,
    # but we can inspect the file content (already done) or use internal inspection if available.
    # Since we are in the same environment, let's just check the file again.
    # Actually, we could import the service and check ALLOWED_IMPORTS if it was global,
    # but it's defined inside a function.
    
    # Let's rely on the file content check in test_pymupdf_is_not_in_any_whitelist
    # and add a specific check for fitz/pdfplumber in the file.
    sandbox_service_path = os.path.abspath("client_app/app/services/sandbox_service.py")
    with open(sandbox_service_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "fitz" in content
        assert "pdfplumber" in content
        assert "openpyxl" in content
