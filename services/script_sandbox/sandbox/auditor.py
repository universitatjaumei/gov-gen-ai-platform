"""ScriptSecurityAuditor — copia DEFENSIVA, autocontenida, sin importar nada de server/app.

Es la segunda barrera de la defensa en profundidad: aunque el API tenga su
propio `ScriptSecurityAuditor` (server/app/modules/redaccion/services/script_auditor.py)
que ya audita antes de enviar el código al sandbox, este módulo audita de nuevo
antes de exec. La duplicación es intencionada (documentada en
docs/SANDBOX_SECURITY.md a partir de SBX.4): si las dos listas blancas divergen,
es porque el sandbox debe ser MÁS estricto que el API, no menos.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

# Llamadas a funciones o builtins que bloquean la aprobación.
_DANGEROUS_CALLS: frozenset[str] = frozenset({
    "eval", "exec", "__import__", "compile", "open",
})

# Atributos de objeto cuyas llamadas son peligrosas (.system(), .popen(), .rmtree()...).
_DANGEROUS_ATTRS: frozenset[str] = frozenset({
    "system", "popen", "rmtree", "remove", "unlink", "chmod", "spawn",
})

# Módulos permitidos (lista blanca). Debe contener TODO lo que los wrappers
# del sandbox importan al ejecutar scripts de usuario; cualquier módulo fuera
# de esta lista es rechazado.
WHITELIST_MODULES: frozenset[str] = frozenset({
    "pandas", "json", "re", "math", "datetime", "collections",
    "typing", "io", "openpyxl", "pdfplumber", "unicodedata",
    "fitz",
    "matplotlib", "seaborn", "numpy", "base64",
})


@dataclass(frozen=True)
class AuditResult:
    approved: bool
    risk_level: str  # "low" | "medium" | "high"
    findings: list[str] = field(default_factory=list)
    confidence: float = 1.0


class ScriptSecurityAuditor:
    """Audita scripts Python contra una lista blanca y patrones peligrosos.

    Analiza el AST (no string-matching) para detectar uso indirecto vía aliases.
    """

    def audit(self, code: str) -> AuditResult:
        findings: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return AuditResult(
                approved=False,
                risk_level="high",
                findings=[f"SyntaxError: {exc}"],
                confidence=0.0,
            )

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in _DANGEROUS_CALLS:
                    findings.append(f"CRITICO: llamada peligrosa '{node.func.id}()'")
                elif isinstance(node.func, ast.Attribute) and node.func.attr in _DANGEROUS_ATTRS:
                    findings.append(f"CRITICO: llamada peligrosa '.{node.func.attr}()'")

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
