from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import ast

class FindingSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKED = "blocked"

@dataclass
class AuditFinding:
    line: int
    code: str
    message: str
    severity: FindingSeverity

@dataclass
class AuditResult:
    is_safe: bool
    can_proceed_with_review: bool  # True si hay warnings pero no blocked
    findings: List[AuditFinding]
    summary: str

# Patrones peligrosos
BLOCKED_IMPORTS = ['subprocess', 'socket', 'ctypes', 'multiprocessing', 'os', 'sys', 'shutil', 'platform']
BLOCKED_FUNCTIONS = ['eval', 'exec', 'compile', '__import__', 'open']
BLOCKED_ATTRIBUTES = ['os.system', 'os.popen', 'os.spawn', 'subprocess.call', 'subprocess.run']
REVIEW_REQUIRED_IMPORTS = ['requests', 'urllib', 'httpx', 'aiohttp']

class ExternalScriptAuditService:
    """
    Servicio de auditoría de seguridad para scripts Python externos.
    Utiliza el análisis de Árbol de Sintaxis Abstracta (AST) para detectar
    patrones de código peligrosos o no autorizados.
    """

    def audit_script(self, code: str) -> AuditResult:
        """
        Audita un script Python externo.

        Proceso:
        1. Parsear AST
        2. Buscar imports peligrosos
        3. Buscar llamadas a funciones peligrosas
        4. Buscar atributos peligrosos
        5. Generar informe

        Returns:
            AuditResult con hallazgos y decisión
        """
        findings = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return AuditResult(
                is_safe=False,
                can_proceed_with_review=False,
                findings=[AuditFinding(e.lineno or 0, "", f"Error de sintaxis: {e.msg}", FindingSeverity.BLOCKED)],
                summary="El código tiene errores de sintaxis"
            )

        # Analizar imports
        findings.extend(self._check_imports(tree))

        # Analizar llamadas y atributos
        findings.extend(self._check_nodes(tree))

        # Determinar resultado
        blocked = any(f.severity == FindingSeverity.BLOCKED for f in findings)
        warnings = any(f.severity == FindingSeverity.WARNING for f in findings)

        summary = self._generate_summary(findings)
        
        return AuditResult(
            is_safe=len(findings) == 0,
            can_proceed_with_review=not blocked,
            findings=findings,
            summary=summary
        )

    def _check_imports(self, tree: ast.AST) -> List[AuditFinding]:
        """Busca imports peligrosos."""
        findings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split('.')[0] # Check base module
                    if name in BLOCKED_IMPORTS:
                        findings.append(AuditFinding(
                            node.lineno,
                            f"import {alias.name}",
                            f"Import bloqueado: {alias.name}",
                            FindingSeverity.BLOCKED
                        ))
                    elif name in REVIEW_REQUIRED_IMPORTS:
                        findings.append(AuditFinding(
                            node.lineno,
                            f"import {alias.name}",
                            f"Import requiere revisión: {alias.name}",
                            FindingSeverity.WARNING
                        ))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module.split('.')[0]
                    if name in BLOCKED_IMPORTS:
                         findings.append(AuditFinding(
                            node.lineno,
                            f"from {node.module} import ...",
                            f"Import bloqueado: {node.module}",
                            FindingSeverity.BLOCKED
                        ))
                    elif name in REVIEW_REQUIRED_IMPORTS:
                        findings.append(AuditFinding(
                            node.lineno,
                            f"from {node.module} import ...",
                            f"Import requiere revisión: {node.module}",
                            FindingSeverity.WARNING
                        ))
        return findings

    def _check_nodes(self, tree: ast.AST) -> List[AuditFinding]:
        """
        Inspecciona los nodos del AST en busca de llamadas a funciones o accesos
        a atributos que estén en la lista negra de seguridad.
        """
        findings = []
        for node in ast.walk(tree):
            # Check Calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in BLOCKED_FUNCTIONS:
                        findings.append(AuditFinding(
                            node.lineno,
                            node.func.id,
                            f"Función bloqueada: {node.func.id}",
                            FindingSeverity.BLOCKED
                        ))
            
            # Check Attributes (e.g. os.system)
            if isinstance(node, ast.Attribute):
                # Try to resolve full name like os.system
                full_name = self._resolve_attribute_name(node)
                if full_name in BLOCKED_ATTRIBUTES:
                     findings.append(AuditFinding(
                            node.lineno,
                            full_name,
                            f"Atributo/Método bloqueado: {full_name}",
                            FindingSeverity.BLOCKED
                        ))
        return findings

    def _resolve_attribute_name(self, node: ast.Attribute) -> str:
        """
        Resuelve de forma recursiva el nombre completo de un atributo (ej. 'os.path.join').
        """
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        
        if isinstance(current, ast.Name):
            parts.append(current.id)
            
        return ".".join(reversed(parts))

    def _generate_summary(self, findings: List[AuditFinding]) -> str:
        """
        Genera un resumen textual legible de los hallazgos de la auditoría.
        """
        if not findings:
            return "Código seguro."
        
        blocked_count = sum(1 for f in findings if f.severity == FindingSeverity.BLOCKED)
        warning_count = sum(1 for f in findings if f.severity == FindingSeverity.WARNING)
        
        parts = []
        if blocked_count:
            parts.append(f"{blocked_count} elementos bloqueados")
        if warning_count:
            parts.append(f"{warning_count} advertencias")
            
        return "Auditoría completada: " + ", ".join(parts)

external_script_audit_service = ExternalScriptAuditService()
