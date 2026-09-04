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

def test_pymupdf_no_esta_en_la_lista_blanca():
    """`PyMuPDF` es el nombre del paquete; el módulo que se importa es `fitz`.

    Admitir «PyMuPDF» en una lista blanca de *imports* no protege ni permite nada: nadie escribe
    `import PyMuPDF`. Tenerlo ahí sólo hace creer que la lista dice algo que no dice.

    NIC.2 — la segunda mitad de este test **leía el texto de
    `client_app/app/services/sandbox_service.py`**, que se ha ido a la cuarentena. Y leer el
    fichero era la comprobación equivocada: lo que importa es qué admite la lista que consulta el
    auditor, no qué palabras aparecen en un fuente.
    """
    from automatia_shared.core.security import SAFE_IMPORTS

    assert "PyMuPDF" not in SAFE_IMPORTS
    assert "fitz" in SAFE_IMPORTS, "el módulo que sí se importa tiene que estar"

def test_openpyxl_is_allowed_for_pandas():
    """Confirmar que pandas y openpyxl están permitidos."""
    # indirect check via audit_code
    code = "import pandas\nimport openpyxl\ndf = pandas.read_excel('test.xlsx')"
    result = audit_code(code)
    assert result['status'] == 'SAFE'

def test_la_lista_blanca_admite_los_lectores_de_pdf_y_excel():
    """Los tres módulos de lectura que el sandbox tiene que admitir.

    NIC.2 — **este test miraba el texto de un fichero del legacy**: importaba
    `neutralize_dangerous_functions` de `client_app/app/services/sandbox_service.py` sin llamarla
    nunca y luego afirmaba que el contenido del fichero contenía las cadenas «fitz»,
    «pdfplumber» y «openpyxl». Eso no comprobaba la lista blanca: comprobaba que un fichero
    mencionara tres palabras, y habría pasado igual con las tres en un comentario.

    Era además **el único import real hacia `client_app/` en todo el repositorio**, así que
    atañía a la retirada del legacy. Ahora se afirma sobre `SAFE_IMPORTS`, que es la lista que
    el auditor consulta de verdad.
    """
    from automatia_shared.core.security import SAFE_IMPORTS

    assert {"fitz", "pdfplumber", "openpyxl"} <= SAFE_IMPORTS
