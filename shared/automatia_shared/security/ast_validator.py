
"""
AST Security Validator - Analyzes Python code for security violations.
Prompt 8 implementation.
"""
import ast
from typing import List, Set, Optional
from dataclasses import dataclass
from enum import Enum

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityViolation:
    violation_type: str  # 'forbidden_import', 'dangerous_call', 'sensitive_attribute'
    line_number: int
    message: str
    risk_level: RiskLevel

@dataclass
class ValidationResult:
    is_safe: bool
    violations: List[SecurityViolation]
    risk_level: RiskLevel

class ASTSecurityValidator:
    """Validates Python code using AST analysis to detect security issues."""
    
    # Forbidden imports that pose security risks
    FORBIDDEN_IMPORTS = {
        'os', 'subprocess', 'sys', 'shutil', 'pathlib',
        'socket', 'ftplib', 'telnetlib', 'smtplib',
        'pickle', 'shelve', 'marshal',
        'ctypes', 'importlib', '__builtin__', 'builtins'
    }
    
    # Network-related imports (configurable)
    NETWORK_IMPORTS = {
        'requests', 'urllib', 'urllib2', 'urllib3', 'httplib', 'http',
        'aiohttp', 'httpx'
    }
    
    # Dangerous function calls
    DANGEROUS_CALLS = {
        'eval', 'exec', 'compile', '__import__', 'open',
        'input', 'raw_input'  # Can be dangerous in automated contexts
    }
    
    # Sensitive attribute access patterns
    SENSITIVE_ATTRIBUTES = {
        '__builtins__', '__globals__', '__locals__', '__dict__',
        '__class__', '__bases__', '__subclasses__'
    }
    
    def __init__(self, allow_network: bool = False, allow_file_read: bool = False):
        """
        Initialize validator with configuration.
        
        Args:
            allow_network: If True, network imports are allowed
            allow_file_read: If True, 'open' in read mode is allowed
        """
        self.allow_network = allow_network
        self.allow_file_read = allow_file_read
        self.violations: List[SecurityViolation] = []
    
    def validate(self, code: str) -> ValidationResult:
        """
        Validate Python code for security issues.
        
        Args:
            code: Python source code as string
            
        Returns:
            ValidationResult with safety status and violations
        """
        self.violations = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.violations.append(SecurityViolation(
                violation_type='syntax_error',
                line_number=e.lineno or 0,
                message=f"Syntax error: {e.msg}",
                risk_level=RiskLevel.HIGH
            ))
            return ValidationResult(
                is_safe=False,
                violations=self.violations,
                risk_level=RiskLevel.HIGH
            )
        
        # Walk the AST and check for violations
        for node in ast.walk(tree):
            self._check_imports(node)
            self._check_calls(node)
            self._check_attributes(node)
        
        # Determine overall risk level
        if not self.violations:
            risk_level = RiskLevel.LOW
        else:
            risk_levels = [v.risk_level for v in self.violations]
            if RiskLevel.CRITICAL in risk_levels:
                risk_level = RiskLevel.CRITICAL
            elif RiskLevel.HIGH in risk_levels:
                risk_level = RiskLevel.HIGH
            elif RiskLevel.MEDIUM in risk_levels:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
        
        return ValidationResult(
            is_safe=len(self.violations) == 0,
            violations=self.violations,
            risk_level=risk_level
        )
    
    def _check_imports(self, node):
        """Check for forbidden imports."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                self._check_module(module_name, node.lineno)
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                self._check_module(module_name, node.lineno)
    
    def _check_module(self, module_name: str, line_number: int):
        """Check if a module is forbidden."""
        if module_name in self.FORBIDDEN_IMPORTS:
            self.violations.append(SecurityViolation(
                violation_type='forbidden_import',
                line_number=line_number,
                message=f"Forbidden import: '{module_name}' poses security risks",
                risk_level=RiskLevel.CRITICAL
            ))
        
        elif module_name in self.NETWORK_IMPORTS and not self.allow_network:
            self.violations.append(SecurityViolation(
                violation_type='forbidden_import',
                line_number=line_number,
                message=f"Network import '{module_name}' not allowed (enable allow_network if needed)",
                risk_level=RiskLevel.HIGH
            ))
    
    def _check_calls(self, node):
        """Check for dangerous function calls."""
        if isinstance(node, ast.Call):
            func_name = None
            
            # Direct function call: eval()
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            
            # Attribute call: obj.method()
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            
            if func_name in self.DANGEROUS_CALLS:
                # Special case: allow 'open' in read mode if configured
                if func_name == 'open' and self.allow_file_read:
                    # Check if mode is 'r' (would need more sophisticated analysis)
                    # For now, still flag it
                    pass
                
                self.violations.append(SecurityViolation(
                    violation_type='dangerous_call',
                    line_number=node.lineno,
                    message=f"Dangerous function call: '{func_name}()' can execute arbitrary code",
                    risk_level=RiskLevel.CRITICAL if func_name in ['eval', 'exec'] else RiskLevel.HIGH
                ))
    
    def _check_attributes(self, node):
        """Check for access to sensitive attributes."""
        if isinstance(node, ast.Attribute):
            attr_name = node.attr
            if attr_name in self.SENSITIVE_ATTRIBUTES:
                self.violations.append(SecurityViolation(
                    violation_type='sensitive_attribute',
                    line_number=node.lineno,
                    message=f"Access to sensitive attribute: '{attr_name}' can bypass security",
                    risk_level=RiskLevel.HIGH
                ))
        
        # Also check for Name nodes (direct variable access)
        if isinstance(node, ast.Name):
            if node.id in self.SENSITIVE_ATTRIBUTES:
                self.violations.append(SecurityViolation(
                    violation_type='sensitive_attribute',
                    line_number=node.lineno,
                    message=f"Access to sensitive name: '{node.id}'",
                    risk_level=RiskLevel.HIGH
                ))
