import pytest
import textwrap
from client_app.app.services.external_script_audit_service import (
    external_script_audit_service,
    FindingSeverity,
    AuditResult,
    ExternalScriptAuditService
)

def test_audit_safe_script_passes():
    """Script sin problemas pasa auditoría"""
    code = textwrap.dedent("""
        import pandas as pd
        def transform(df):
            return df.head()
    """)
    result = external_script_audit_service.audit_script(code)
    assert result.is_safe
    assert result.can_proceed_with_review
    assert len(result.findings) == 0

def test_audit_detects_os_system():
    """Detecta uso de os.system()"""
    code = textwrap.dedent("""
        import os
        os.system('rm -rf /')
    """)
    result = external_script_audit_service.audit_script(code)
    
    assert not result.is_safe
    # Import os is blocked
    assert any(f.severity == FindingSeverity.BLOCKED and "os" in f.message for f in result.findings)
    # os.system is blocked attribute/call
    assert any(f.severity == FindingSeverity.BLOCKED and "os.system" in f.code for f in result.findings)

def test_audit_detects_eval():
    """Detecta uso de eval()"""
    code = "eval('print(1)')"
    result = external_script_audit_service.audit_script(code)
    assert any(f.code == "eval" and f.severity == FindingSeverity.BLOCKED for f in result.findings)

def test_audit_detects_exec():
    """Detecta uso de exec()"""
    code = "exec('import os')"
    result = external_script_audit_service.audit_script(code)
    assert any(f.code == "exec" and f.severity == FindingSeverity.BLOCKED for f in result.findings)

def test_audit_detects_subprocess():
    """Detecta import subprocess"""
    code = "import subprocess"
    result = external_script_audit_service.audit_script(code)
    assert any(f.code == "import subprocess" and f.severity == FindingSeverity.BLOCKED for f in result.findings)

def test_audit_detects_socket():
    """Detecta import socket"""
    code = "import socket"
    result = external_script_audit_service.audit_script(code)
    assert any(f.code == "import socket" and f.severity == FindingSeverity.BLOCKED for f in result.findings)

def test_audit_detects_requests():
    """Detecta import requests (requiere revisión)"""
    code = "import requests"
    result = external_script_audit_service.audit_script(code)
    
    # No es seguro (is_safe=False) pero permite revisión (can_proceed=True)
    assert not result.is_safe
    assert result.can_proceed_with_review
    
    finding = next(f for f in result.findings if "requests" in f.code)
    assert finding.severity == FindingSeverity.WARNING

def test_audit_returns_findings():
    """Retorna lista de hallazgos con severidad"""
    code = textwrap.dedent("""
        import os  # Blocked
        import requests  # Warning
        print('hello')
    """)
    result = external_script_audit_service.audit_script(code)
    
    assert len(result.findings) >= 2
    assert not result.can_proceed_with_review # Blocked by os
    
    severities = [f.severity for f in result.findings]
    assert FindingSeverity.BLOCKED in severities
    assert FindingSeverity.WARNING in severities

def test_syntax_error_returns_blocked():
    """Syntax error blocks the script"""
    code = "def broken_func("
    result = external_script_audit_service.audit_script(code)
    
    assert not result.is_safe
    assert not result.can_proceed_with_review
    assert len(result.findings) == 1
    assert "sintaxis" in result.findings[0].message
