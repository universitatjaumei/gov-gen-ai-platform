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

# SEC.8.3 — la evasión de manual no llama a `eval` por su nombre.
#
# El auditor miraba `ast.Name` y `ast.Attribute`, así que `eval(...)` se veía pero
# `__builtins__['eval'](...)` no: ahí `eval` es una cadena dentro de un Subscript. Lo mismo
# con el paseo `().__class__.__bases__[0].__subclasses__()`, que llega a cualquier clase
# cargada sin nombrar nada prohibido, y con `getattr(o, 'ev' + 'al')`, donde el nombre ni
# siquiera existe como literal. Se bloquean los tres por su forma, no por su nombre.
_NOMBRES_PROHIBIDOS: frozenset[str] = frozenset({
    "__builtins__", "__globals__", "__subclasses__", "__bases__", "__class__",
    "__mro__", "__code__", "__closure__", "__dict__", "__loader__", "__module__",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
})

# Módulos permitidos (lista blanca)
WHITELIST_MODULES: frozenset[str] = frozenset({
    "pandas", "json", "re", "math", "datetime", "collections",
    "typing", "io", "openpyxl", "pdfplumber", "unicodedata",
    "fitz",
    # Charts (9R.5.7)
    "matplotlib", "seaborn", "numpy", "base64",
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

            # SEC.8.3: la introspección que lleva al intérprete, mirada por su forma.
            # `__builtins__` como nombre suelto, `.__class__` como atributo, `getattr`
            # como llamada: cualquiera de las tres abre el camino, se use como se use.
            if isinstance(node, ast.Name) and node.id in _NOMBRES_PROHIBIDOS:
                findings.append(
                    f"CRITICO: acceso a '{node.id}', que da alcance al intérprete"
                )
            if isinstance(node, ast.Attribute) and node.attr in _NOMBRES_PROHIBIDOS:
                findings.append(
                    f"CRITICO: acceso a '.{node.attr}', que da alcance al intérprete"
                )

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
