
import pytest
import ast
from automatia_shared.security.ast_validator import ASTSecurityValidator, SecurityViolation, RiskLevel

def test_safe_code_passes_validation():
    """Safe code with pandas and json should pass."""
    safe_code = """
import pandas as pd
import json

def process_data(df):
    result = df.groupby('category').sum()
    return json.dumps(result.to_dict())
"""
    validator = ASTSecurityValidator()
    result = validator.validate(safe_code)
    
    assert result.is_safe is True
    assert len(result.violations) == 0
    assert result.risk_level == RiskLevel.LOW


def test_dangerous_import_detected():
    """Code with os import should be flagged."""
    dangerous_code = """
import os
import pandas as pd

def delete_files():
    os.remove('/tmp/file.txt')
"""
    validator = ASTSecurityValidator()
    result = validator.validate(dangerous_code)
    
    assert result.is_safe is False
    assert len(result.violations) >= 1
    assert any(v.violation_type == 'forbidden_import' for v in result.violations)
    assert any('os' in v.message for v in result.violations)
    assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]


def test_eval_call_detected():
    """Code using eval() should be flagged."""
    eval_code = """
def dangerous_function(user_input):
    result = eval(user_input)
    return result
"""
    validator = ASTSecurityValidator()
    result = validator.validate(eval_code)
    
    assert result.is_safe is False
    assert any(v.violation_type == 'dangerous_call' for v in result.violations)
    assert any('eval' in v.message.lower() for v in result.violations)


def test_exec_call_detected():
    """Code using exec() should be flagged."""
    exec_code = """
code = "print('hello')"
exec(code)
"""
    validator = ASTSecurityValidator()
    result = validator.validate(exec_code)
    
    assert result.is_safe is False
    assert any(v.violation_type == 'dangerous_call' for v in result.violations)


def test_builtins_access_detected():
    """Access to __builtins__ should be flagged."""
    builtins_code = """
def hack():
    b = __builtins__
    return b['eval']
"""
    validator = ASTSecurityValidator()
    result = validator.validate(builtins_code)
    
    assert result.is_safe is False
    assert any(v.violation_type == 'sensitive_attribute' for v in result.violations)


def test_multiple_violations():
    """Code with multiple issues should report all."""
    bad_code = """
import os
import subprocess

def very_bad():
    eval("print('bad')")
    subprocess.call(['rm', '-rf', '/'])
    os.system('echo hack')
"""
    validator = ASTSecurityValidator()
    result = validator.validate(bad_code)
    
    assert result.is_safe is False
    assert len(result.violations) >= 3
    assert result.risk_level == RiskLevel.CRITICAL


def test_syntax_error_handling():
    """Invalid Python syntax should be handled gracefully."""
    invalid_code = "def broken( syntax error"
    
    validator = ASTSecurityValidator()
    result = validator.validate(invalid_code)
    
    assert result.is_safe is False
    assert any('syntax' in v.message.lower() for v in result.violations)


def test_network_imports_configurable():
    """Network libraries like requests can be allowed/blocked via config."""
    network_code = """
import requests

def fetch_data(url):
    return requests.get(url).json()
"""
    # Default: block network
    validator = ASTSecurityValidator(allow_network=False)
    result = validator.validate(network_code)
    assert result.is_safe is False
    
    # Allow network
    validator_permissive = ASTSecurityValidator(allow_network=True)
    result_permissive = validator_permissive.validate(network_code)
    assert result_permissive.is_safe is True
