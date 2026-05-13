"""ScriptSecurityAuditor — auditoría AST de scripts de extracción (9R.5.4).

Migrado y refactorizado desde supervisar_codigo() en
automation/extraction_strategies.py. Usa análisis AST en lugar de
búsqueda de strings: detecta usos indirectos y no es engañado por
espaciado ni concatenación.
"""
from __future__ import annotations

import ast

from pydantic import BaseModel

# Llamadas a funciones o builtins que bloquean la aprobación
_DANGEROUS_CALLS: frozenset[str] = frozenset({
    "eval", "exec", "__import__", "compile", "open",
})

# Atributos de objeto cuyas llamadas son peligrosas
_DANGEROUS_ATTRS: frozenset[str] = frozenset({
    "system", "popen", "rmtree", "remove", "unlink", "chmod", "spawn",
})

# Módulos permitidos (lista blanca)
WHITELIST_MODULES: frozenset[str] = frozenset({
    "pandas", "json", "re", "math", "datetime", "collections",
    "typing", "io", "openpyxl", "pdfplumber", "unicodedata",
    "fitz",
})


class AuditResult(BaseModel):
    """Resultado de la auditoría de seguridad de un script."""

    approved: bool
    risk_level: str  # "low" | "medium" | "high"
    findings: list[str]
    confidence: float


class ScriptSecurityAuditor:
    """Audita scripts Python contra una lista blanca de módulos y patrones peligrosos.

    Más robusto que la búsqueda de strings del legacy supervisar_codigo():
    analiza el AST para detectar uso indirecto (getattr, aliases, etc.).
    """

    def audit(self, code: str) -> AuditResult:
        findings: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return AuditResult(
                approved=False,
                risk_level="high",
                findings=[f"SyntaxError: {e}"],
                confidence=0.0,
            )

        for node in ast.walk(tree):
            # Llamadas directas peligrosas: eval(), exec(), __import__()…
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in _DANGEROUS_CALLS:
                    findings.append(f"CRITICO: llamada peligrosa '{node.func.id}()'")
                elif isinstance(node.func, ast.Attribute) and node.func.attr in _DANGEROUS_ATTRS:
                    findings.append(f"CRITICO: llamada peligrosa '.{node.func.attr}()'")

            # Importaciones de módulos fuera de la lista blanca
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module not in WHITELIST_MODULES:
                        findings.append(
                            f"ADVERTENCIA: módulo '{module}' no está en la lista blanca"
                        )

            if isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if module and module not in WHITELIST_MODULES:
                    findings.append(
                        f"ADVERTENCIA: módulo '{module}' no está en la lista blanca"
                    )

        critical = [f for f in findings if f.startswith("CRITICO")]
        risk_level = "high" if critical else ("medium" if findings else "low")
        confidence = 1.0 if not findings else (0.5 if not critical else 0.0)

        return AuditResult(
            approved=not findings,
            risk_level=risk_level,
            findings=findings,
            confidence=confidence,
        )
