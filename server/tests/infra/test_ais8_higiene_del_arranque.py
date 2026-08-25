"""AIS.8 — Higiene del arranque: que un fallo se vea, y que la reserva no sea una trampa.

Cuatro cosas pequeñas con la misma forma: comportamientos que **funcionan** y que, cuando algo va
mal, no dejan nada con lo que volver.

1. **No había configuración de logging.** El único `basicConfig` del proyecto vivía dentro de un
   script de reingesta, así que el servidor hablaba por `print`: sin nivel, sin marca de tiempo y
   sin forma de subir el detalle. En el piloto eso es toda la observabilidad que habría.
2. **`to_pdf` era `async def` y llamaba a LibreOffice de forma síncrona**, con `timeout=30`. No es
   un detalle de estilo: mientras un informe se convertía, el bucle de eventos estaba bloqueado y
   el servidor entero dejaba de atender.
3. **El DSN de reserva llevaba credenciales.** En local es comodidad; en producción, un
   despliegue al que se le olvide `DATABASE_URL` no falla — se conecta a otra base con una
   credencial publicada en el repositorio, y el síntoma es «faltan datos», no «falta
   configuración».
4. **El extra `local-models` no lo ejercita nadie.** Añadido tras la falsa alarma del `uv.lock`
   de la raíz (2026-08-24): aquel borrado resultó ser el árbol de Docling poniéndose al día con
   EXT.3, no la pila de torch. Pero al mirarlo apareció el hueco de verdad — **CI hace
   `uv sync --frozen` sin `--extra local-models`**, así que ese camino no se comprueba en ninguna
   parte. El `--frozen` del `Dockerfile` protege la imagen; la instalación local de un edge no
   tiene nada.
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest

_APP = Path("app")


class TestElArranqueConfiguraElLogging:

    def test_should_configure_application_logging_at_startup(self):
        from server.app.main import _arranque, configurar_logging  # noqa: F401

        fuente = Path("app/main.py").read_text(encoding="utf-8")
        cuerpo = fuente.split("async def _arranque", 1)[1][:600]
        assert "configurar_logging()" in cuerpo, (
            "el arranque no configura el logging, así que los mensajes del propio arranque "
            "—los que más falta hacen cuando algo va mal— salen sin nivel ni marca de tiempo"
        )

    def test_should_take_the_level_from_the_environment(self, monkeypatch):
        import logging

        from server.app.main import configurar_logging

        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        configurar_logging()
        assert logging.getLogger().level == logging.WARNING

        monkeypatch.setenv("LOG_LEVEL", "INFO")
        configurar_logging()
        assert logging.getLogger().level == logging.INFO

    def test_should_not_speak_through_print_at_startup(self):
        """`main.py` es el punto de entrada: si aquí se cuela un `print`, se cuela en todas
        partes. El resto del árbol tiene más y se limpian aparte; éste queda a cero."""
        arbol = ast.parse(Path("app/main.py").read_text(encoding="utf-8"))
        prints = [
            nodo.lineno
            for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id == "print"
        ]
        assert prints == [], f"`print(` en main.py, líneas {prints}: usa el logger"


class TestLaConversionNoBloqueaElBucle:

    def test_should_not_block_the_event_loop_on_pdf_export(self):
        texto = Path("app/modules/curation/report_exporter.py").read_text(encoding="utf-8")
        cuerpo = texto.split("async def to_pdf", 1)[1]

        assert "asyncio.to_thread" in cuerpo, (
            "to_pdf es async y llama a LibreOffice de forma síncrona con timeout de 30 s: "
            "bloquea el bucle de eventos y el servidor deja de atender mientras convierte"
        )
        # Y la llamada síncrona vive dentro de la función que se manda al hilo, no suelta.
        assert cuerpo.index("def _convertir") < cuerpo.index("subprocess.run")


class TestLaReservaDelDsnNoEsUnaTrampa:

    def test_should_fail_loudly_when_database_url_is_absent_in_production(self, monkeypatch):
        from server.app.database.db import _dsn

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")

        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            _dsn()

    def test_should_keep_the_development_fallback_outside_production(self, monkeypatch):
        """La reserva se conserva **fuera** de producción a propósito: sin ella no se arranca en
        local ni corre la suite sin montar un `.env`, y esa fricción se paga todos los días."""
        from server.app.database.db import _dsn

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")

        assert _dsn().startswith("postgresql+asyncpg://")

    def test_should_declare_the_fallback_in_a_single_place(self):
        """Estaba escrito dos veces, aquí y en la conexión del hub. Dos copias del mismo valor
        por omisión divergen, y la que no se toque seguirá conectando a la base vieja."""
        conexion = Path(
            "app/modules/agents_hub/database/connection.py"
        ).read_text(encoding="utf-8")
        assert "govgenai_dev@localhost" not in conexion


class TestElExtraDeModelosLocalesEstaFijado:
    """El guardarraíl que salió de la falsa alarma del `uv.lock`.

    Es **estático**: lee el lock, no instala nada. Cuesta milisegundos y cubre justo lo que no
    cubre nadie — CI sincroniza sin el extra, así que la pila de modelos locales no se resuelve
    en ninguna comprobación automática, y un despliegue `edge` la necesita entera.
    """

    #: Lo que importan `LocalEmbeddingService` y `LocalReranker`, más lo que el extra declara.
    _PAQUETES = ("torch", "torchvision", "sentence-transformers")

    def test_should_pin_the_local_models_stack_in_the_server_lock(self):
        lock = Path("uv.lock").read_text(encoding="utf-8", errors="ignore")
        faltan = [p for p in self._PAQUETES if f'name = "{p}"' not in lock]

        assert faltan == [], (
            f"server/uv.lock no fija {faltan}. Es lo que instala `uv sync --extra local-models`, "
            "y sin ello un despliegue edge se queda sin embeddings ni reranker locales. CI "
            "sincroniza SIN el extra, así que esto no lo caza ninguna otra comprobación."
        )

    def test_should_declare_the_extra_in_pyproject(self):
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        bloque = pyproject.split("local-models = [", 1)
        assert len(bloque) == 2, "el extra `local-models` ya no está declarado"
        for paquete in ("torch", "torchvision", "sentence-transformers"):
            assert paquete in bloque[1][:300], f"el extra no declara {paquete}"
