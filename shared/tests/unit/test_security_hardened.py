import pytest
from automatia_shared.core.security import audit_code, SecurityAuditor

# === Tests básicos ===

def test_block_dangerous_imports():
    code = "import os\nos.system('whoami')"
    result = audit_code(code)
    assert result['status'] == 'CRITICAL'
    assert any('os' in r for r in result['reasons'])

def test_block_open_write_outside_jail():
    code = "open('/etc/passwd','w')"
    result = audit_code(code)
    assert result['status'] in ('CRITICAL', 'WARNING')

def test_allow_safe_imports():
    code = "import pandas as pd\nimport re\nfrom datetime import datetime"
    result = audit_code(code)
    assert result['status'] == 'SAFE'

def test_allow_extended_safe_imports():
    """Verificar whitelist extendida."""
    code = """
import json
import math
import csv
import itertools
import functools
import decimal
import string
from pathlib import Path
from collections import defaultdict
"""
    result = audit_code(code)
    assert result['status'] == 'SAFE'

# === Casos de bypass ===

def test_block_dunder_mro_chain():
    code = "print([].__class__.__mro__)"
    result = audit_code(code)
    assert result['status'] == 'CRITICAL'

def test_block_builtins_open_via_getattr():
    code = "import builtins\ngetattr(builtins,'o'+'pen')('x','r')"
    result = audit_code(code)
    assert result['status'] == 'CRITICAL'

def test_block_dynamic_import_and_system():
    code = "__import__('os').system('dir')"
    result = audit_code(code)
    assert result['status'] == 'CRITICAL'

def test_block_ctypes():
    code = "import ctypes; ctypes.c_int(1)"
    result = audit_code(code)
    assert result['status'] == 'CRITICAL'

def test_block_pickle():
    code = "import pickle; pickle.loads(b'data')"
    result = audit_code(code)
    assert result['status'] == 'CRITICAL'

def test_block_marshal():
    code = "import marshal; marshal.loads(b'data')"
    result = audit_code(code)
    assert result['status'] == 'CRITICAL'

def test_block_subclasses_access():
    code = "().__class__.__bases__[0].__subclasses__()"
    result = audit_code(code)
    assert result['status'] == 'CRITICAL'

def test_block_globals_access():
    code = "x = lambda: None; x.__globals__"
    result = audit_code(code)
    assert result['status'] == 'CRITICAL'

def test_block_code_object_access():
    code = "def f(): pass\nf.__code__"
    result = audit_code(code)
    assert result['status'] == 'CRITICAL'

# === Test de salida enriquecida ===

def test_audit_returns_blocked_nodes():
    code = "import os\neval('1+1')"
    result = audit_code(code)
    assert 'blocked_nodes' in result
    assert len(result['blocked_nodes']) >= 1
    assert any(n['rule'] for n in result['blocked_nodes'])
