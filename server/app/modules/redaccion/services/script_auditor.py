"""ScriptSecurityAuditor — auditoría AST de scripts de extracción (9R.5.4).

Migrado y refactorizado desde supervisar_codigo() en
automation/extraction_strategies.py. Usa análisis AST en lugar de
búsqueda de strings: detecta usos indirectos y no es engañado por
espaciado ni concatenación.

PRO.1 — la auditoría deja de ser binaria y recupera los tres niveles del legacy
(`AutomatIA/shared/automatia_shared/core/security.py:audit_code()`):

- `SAFE`     — ningún hallazgo.
- `WARNING`  — hallazgos, ninguno crítico. Es un hueco en una lista, no un problema de
               seguridad: una persona puede aceptarlo mirándolo (`puede_revisarse`).
- `CRITICAL` — hay al menos un hallazgo que nadie puede aceptar: `eval()`, la
               introspección que alcanza al intérprete, una ruta absoluta o un
               fichero que no compila.

`approved` sigue significando **sin hallazgos**, así que las puertas de ejecución
(`AdminScriptExtractionPipeline`, `chart_renderer`, el propio sandbox) no cambian de
comportamiento. Quien decide si algo puede llegar a una revisión humana mira
`puede_revisarse`.

Y se recupera la comprobación que la aplicación nueva había perdido: **rutas absolutas**.
Un script de informe solo puede leer el fichero que la plataforma le pasa en `file_path`;
uno que abra `C:\\Users\\...` con pandas no usa ninguna llamada prohibida y hasta PRO.1
pasaba la auditoría.
"""
from __future__ import annotations

import ast
import re
from enum import StrEnum
from typing import Literal

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

# PRO.1 — el legacy tenía dos listas, y la diferencia es justo la que hace segura la
# graduación: `FORBIDDEN_IMPORTS` (denegación explícita) frente a «no está en la lista
# blanca» (denegación por defecto). Un `import csv` es un hueco en una lista y lo puede
# aceptar una persona; un `import os`, `socket` o `requests` es una capacidad —sistema
# operativo, red, deserialización— y no se acepta mirándola. Portado de
# `automatia_shared/core/security.py:FORBIDDEN_IMPORTS`.
_MODULOS_PROHIBIDOS: frozenset[str] = frozenset({
    "os", "sys", "subprocess", "shutil", "platform",
    "importlib", "socket", "ssl", "http", "urllib", "requests", "httpx",
    "ctypes", "cffi", "pickle", "marshal", "shelve",
    "code", "codeop", "pty", "tty",
    "multiprocessing", "threading", "concurrent",
    "ast", "dis", "inspect", "gc", "traceback",
    "builtins", "types", "nicegui", "fastapi", "uvicorn",
})

# Módulos permitidos (lista blanca)
WHITELIST_MODULES: frozenset[str] = frozenset({
    "pandas", "json", "re", "math", "datetime", "collections",
    "typing", "io", "openpyxl", "pdfplumber", "unicodedata",
    "fitz",
    # Charts (9R.5.7)
    "matplotlib", "seaborn", "numpy", "base64",
})

# PRO.1 — rutas absolutas, antes del AST y sobre el texto (comentarios incluidos: una ruta
# escrita en un comentario también dice qué intentaba el modelo).
#
# El legacy usaba `[a-zA-Z]:/`, que marca como ruta de Windows cualquier `https://` —dentro
# lleva `s:/`— y da un motivo falso. La letra de unidad tiene que ir precedida de algo que
# no sea alfanumérico.
_RUTA_WINDOWS = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z]:[\\/])")
_RUTA_SISTEMA = re.compile(r"""['"](/(?:home|etc|usr|var|root|tmp|proc|sys)(?:/|['"]))""")


class RiskLevel(StrEnum):
    """Los tres niveles del legacy. El nivel es el del peor hallazgo."""

    SAFE = "SAFE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AuditFinding(BaseModel):
    """Un hallazgo con su línea: lo que convierte «hay un problema» en «está en la 14»."""

    severity: Literal[RiskLevel.WARNING, RiskLevel.CRITICAL]
    rule: str
    detail: str
    line: int
    message: str


class AuditResult(BaseModel):
    """Resultado de la auditoría de seguridad de un script."""

    approved: bool
    risk_level: RiskLevel
    puede_revisarse: bool
    findings: list[AuditFinding]
    confidence: float


def _linea_de(codigo: str, offset: int) -> int:
    return codigo.count("\n", 0, offset) + 1


class ScriptSecurityAuditor:
    """Audita scripts Python contra una lista blanca de módulos y patrones peligrosos.

    Más robusto que la búsqueda de strings del legacy supervisar_codigo():
    analiza el AST para detectar uso indirecto (getattr, aliases, etc.).
    """

    def audit(self, code: str) -> AuditResult:
        findings: list[AuditFinding] = []

        findings.extend(self._rutas_absolutas(code))

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            findings.append(_critico(
                rule="syntax-error",
                detail=str(e.msg),
                line=e.lineno or 1,
                texto=f"error de sintaxis irrecuperable: {e.msg}",
            ))
            return _resultado(findings)

        for node in ast.walk(tree):
            linea = getattr(node, "lineno", 0)

            # Llamadas directas peligrosas: eval(), exec(), __import__()…
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in _DANGEROUS_CALLS:
                    findings.append(_critico(
                        rule="forbidden-call",
                        detail=node.func.id,
                        line=linea,
                        texto=f"llamada peligrosa '{node.func.id}()'",
                    ))
                elif isinstance(node.func, ast.Attribute) and node.func.attr in _DANGEROUS_ATTRS:
                    findings.append(_critico(
                        rule="forbidden-call",
                        detail=node.func.attr,
                        line=linea,
                        texto=f"llamada peligrosa '.{node.func.attr}()'",
                    ))

            # SEC.8.3: la introspección que lleva al intérprete, mirada por su forma.
            # `__builtins__` como nombre suelto, `.__class__` como atributo, `getattr`
            # como llamada: cualquiera de las tres abre el camino, se use como se use.
            if isinstance(node, ast.Name) and node.id in _NOMBRES_PROHIBIDOS:
                findings.append(_critico(
                    rule="interpreter-access",
                    detail=node.id,
                    line=linea,
                    texto=f"acceso a '{node.id}', que da alcance al intérprete",
                ))
            if isinstance(node, ast.Attribute) and node.attr in _NOMBRES_PROHIBIDOS:
                findings.append(_critico(
                    rule="interpreter-access",
                    detail=node.attr,
                    line=linea,
                    texto=f"acceso a '.{node.attr}', que da alcance al intérprete",
                ))

            # Importaciones de módulos fuera de la lista blanca
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module not in WHITELIST_MODULES:
                        findings.append(_hallazgo_de_modulo(module, linea))

            if isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if module and module not in WHITELIST_MODULES:
                    findings.append(_hallazgo_de_modulo(module, linea))

        return _resultado(findings)

    def _rutas_absolutas(self, code: str) -> list[AuditFinding]:
        hallazgos: list[AuditFinding] = []
        for patron, que in (
            (_RUTA_WINDOWS, "de Windows"),
            (_RUTA_SISTEMA, "de sistema Linux"),
        ):
            for m in patron.finditer(code):
                ruta = m.group(1)
                hallazgos.append(_critico(
                    rule="absolute-path",
                    detail=ruta,
                    line=_linea_de(code, m.start(1)),
                    texto=(
                        f"ruta absoluta {que} ('{ruta}'): un script de informe solo puede "
                        "leer el fichero que la plataforma le pasa en file_path"
                    ),
                ))
        return hallazgos


def _critico(*, rule: str, detail: str, line: int, texto: str) -> AuditFinding:
    return AuditFinding(
        severity=RiskLevel.CRITICAL,
        rule=rule,
        detail=detail,
        line=line,
        message=f"CRITICO (línea {line}): {texto}",
    )


def _hallazgo_de_modulo(module: str, line: int) -> AuditFinding:
    if module in _MODULOS_PROHIBIDOS:
        return _critico(
            rule="forbidden-module",
            detail=module,
            line=line,
            texto=(
                f"módulo '{module}' prohibido: da acceso al sistema, a la red o al "
                "intérprete, y eso no se acepta con una revisión"
            ),
        )
    return AuditFinding(
        severity=RiskLevel.WARNING,
        rule="module-not-whitelisted",
        detail=module,
        line=line,
        message=f"ADVERTENCIA (línea {line}): módulo '{module}' no está en la lista blanca",
    )


def _resultado(findings: list[AuditFinding]) -> AuditResult:
    hay_critico = any(f.severity == RiskLevel.CRITICAL for f in findings)
    if hay_critico:
        nivel = RiskLevel.CRITICAL
    elif findings:
        nivel = RiskLevel.WARNING
    else:
        nivel = RiskLevel.SAFE

    return AuditResult(
        approved=not findings,
        risk_level=nivel,
        # El `can_proceed_with_review` del legacy: hay advertencias pero nada bloqueante,
        # así que una persona con nombre y apellidos puede aceptarlo.
        puede_revisarse=not hay_critico,
        findings=findings,
        confidence=1.0 if not findings else (0.0 if hay_critico else 0.5),
    )
