"""Si el arranque falla, la causa tiene que caber en la pantalla.

Traído de unos logs de desarrollo: la aplicación no arrancaba y **el log no permitía saber por
qué**. FastAPI fusiona un `lifespan` por cada router incluido, así que con unas cuarenta
superficies HTTP el traceback llega con ~40 marcos idénticos de `merged_lifespan` **antes** de la
excepción real; cualquier captura de log lo corta por el medio y el mensaje que importa se pierde.
El log terminaba literalmente a media palabra:

    async with original_context(app) as mayERROR:    Application startup failed. Exiting.

El anidamiento no es un fallo —es el precio de tener muchos routers—, pero un arranque que falla
sin decir por qué sí lo es, y en el despliegue previsto (una máquina con Docker Compose) esa traza
es lo único que habrá para diagnosticar.
"""
from __future__ import annotations

import logging

import pytest

from server.app.main import _resumen_del_fallo, lifespan


def test_el_resumen_dice_el_tipo_y_el_mensaje() -> None:
    try:
        raise RuntimeError("la base de datos no responde")
    except RuntimeError as exc:
        resumen = _resumen_del_fallo(exc)

    assert "RuntimeError" in resumen
    assert "la base de datos no responde" in resumen


def test_el_resumen_senala_nuestro_codigo_y_no_el_del_framework() -> None:
    """Lo que hace falta es el fichero y la línea nuestros, no cuarenta marcos de la librería."""
    try:
        raise ValueError("algo")
    except ValueError as exc:
        resumen = _resumen_del_fallo(exc)

    assert "test_el_fallo_de_arranque_se_puede_leer.py" in resumen
    assert "site-packages" not in resumen


def test_el_resumen_incluye_la_causa_encadenada() -> None:
    """Un `ImportError` envuelto en otro error no dice nada si se pierde el original."""
    try:
        try:
            raise ImportError("cannot import name 'X' from partially initialized module")
        except ImportError as original:
            raise RuntimeError("fallo al sembrar") from original
    except RuntimeError as exc:
        resumen = _resumen_del_fallo(exc)

    assert "partially initialized module" in resumen


def test_el_resumen_es_corto() -> None:
    """Si no cabe en una pantalla, vuelve a pasar lo de los logs: se corta y no sirve."""
    try:
        raise RuntimeError("x" * 50)
    except RuntimeError as exc:
        resumen = _resumen_del_fallo(exc)

    assert len(resumen.splitlines()) <= 12, resumen


@pytest.mark.asyncio
async def test_un_arranque_que_falla_deja_la_causa_en_el_log_y_sigue_fallando(
    monkeypatch, caplog
):
    """El guardarraíl registra y **vuelve a lanzar**: tragarse el error sería mucho peor."""
    import server.app.main as main_mod

    async def _init_que_revienta():
        raise RuntimeError("no hay base de datos en el 5432")

    monkeypatch.setattr(main_mod, "init_server_db", _init_que_revienta)

    with caplog.at_level(logging.CRITICAL, logger=main_mod.__name__):
        with pytest.raises(RuntimeError, match="no hay base de datos"):
            async with lifespan(main_mod.app):
                pass  # no debería llegar aquí

    registro = "\n".join(caplog.messages)
    assert "no hay base de datos en el 5432" in registro
    assert "RuntimeError" in registro
