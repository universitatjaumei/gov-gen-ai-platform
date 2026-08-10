"""Tests SEC.8.3 — el sandbox local no puede usarse en producción, y el auditor AST
no puede caer con las evasiones de manual.

Dos hallazgos encadenados de la auditoría pre-deploy:

- `SANDBOX_MODE=local` devuelve `LocalSandboxClient`, que ejecuta el script **en el host**,
  con la red del host y heredando `os.environ` —o sea, `JWT_SECRET_KEY`, `DATABASE_URL` y
  las claves de los proveedores—. No había ninguna guarda de entorno: bastaba una variable
  mal puesta en el despliegue.
- El auditor AST solo miraba `ast.Name` y un puñado de `.attr`, así que `__builtins__['eval']`
  o el paseo por `().__class__.__bases__[0].__subclasses__()` pasaban con `approved=True`.

En producción el contenedor Docker contiene el segundo; encadenado con el primero, no.
"""
from __future__ import annotations

import pytest


class TestGateDeProduccion:

    def test_should_reject_local_sandbox_in_production(self, monkeypatch):
        from server.app.core.config import get_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SANDBOX_MODE", "local")
        monkeypatch.setenv("JWT_SECRET_KEY", "una-clave-de-produccion-suficientemente-larga")
        monkeypatch.delenv("TESTING", raising=False)

        with pytest.raises(RuntimeError, match="(?i)sandbox"):
            get_settings()

    def test_should_allow_local_sandbox_in_development(self, monkeypatch):
        from server.app.core.config import get_settings

        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("SANDBOX_MODE", "local")
        monkeypatch.setenv("JWT_SECRET_KEY", "clave-de-desarrollo")

        assert get_settings().sandbox_mode == "local"

    def test_should_allow_http_sandbox_in_production(self, monkeypatch):
        """La guarda es sobre el modo local, no sobre producción en general."""
        from server.app.core.config import get_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SANDBOX_MODE", "http")
        monkeypatch.setenv("JWT_SECRET_KEY", "una-clave-de-produccion-suficientemente-larga")
        monkeypatch.delenv("TESTING", raising=False)

        assert get_settings().sandbox_mode == "http"


class TestAuditorNoEsEvadible:
    """Cada caso es una evasión conocida que hoy devuelve `approved=True`."""

    def _auditar(self, codigo: str):
        from server.app.modules.redaccion.services.script_auditor import (
            ScriptSecurityAuditor,
        )

        return ScriptSecurityAuditor().audit(codigo)

    def test_should_block_builtins_subscript_eval(self):
        resultado = self._auditar("__builtins__['eval']('1+1')")
        assert not resultado.approved, "un eval por subíndice de __builtins__ pasó la auditoría"

    def test_should_block_dunder_class_traversal(self):
        codigo = "().__class__.__bases__[0].__subclasses__()"
        resultado = self._auditar(codigo)
        assert not resultado.approved, "el paseo por __subclasses__ pasó la auditoría"

    def test_should_block_getattr_escape(self):
        resultado = self._auditar("getattr(__builtins__, 'ev' + 'al')('1+1')")
        assert not resultado.approved, "getattr sobre __builtins__ pasó la auditoría"

    def test_should_block_globals_access(self):
        resultado = self._auditar("globals()['__builtins__']")
        assert not resultado.approved

    def test_should_still_approve_a_legitimate_extraction_script(self):
        """Endurecer no puede convertir el auditor en un «no» permanente: el script
        legítimo de extracción tiene que seguir aprobándose."""
        codigo = (
            "import pandas as pd\n"
            "def extract(path):\n"
            "    df = pd.read_excel(path)\n"
            "    return {'filas': len(df), 'columnas': list(df.columns)}\n"
        )
        resultado = self._auditar(codigo)
        assert resultado.approved, resultado.findings
