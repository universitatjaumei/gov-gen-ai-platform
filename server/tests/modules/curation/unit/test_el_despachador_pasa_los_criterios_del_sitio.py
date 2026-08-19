"""El despachador pasa al detector los criterios del sitio (CUR.2.1).

Que el contrato del sitio los declare no sirve de nada si quien construye el detector los ignora, y
era exactamente lo que pasaba: `DeterministicDetectorDispatcher` lo instanciaba con los valores por
defecto del constructor, así que **todas las organizaciones compartían criterio** por mucho que cada
sitio guardara el suyo. Es la mitad del camino que convierte «configurable» en real.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from server.app.modules.curation.site_crawler_dispatcher import (
    DeterministicDetectorDispatcher,
)


@dataclass
class _Sitio:
    config_json: dict = field(default_factory=dict)


class _Sesion:
    def __init__(self, sitio: Any) -> None:
        self._sitio = sitio

    async def __aenter__(self) -> "_Sesion":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def get(self, modelo: Any, ident: Any) -> Any:
        return self._sitio

    async def commit(self) -> None:
        return None


@pytest.mark.asyncio
async def test_el_detector_recibe_los_criterios_que_declara_el_sitio(monkeypatch):
    recibidos: dict = {}

    class _DetectorEspia:
        def __init__(self, session: Any, **kwargs: Any) -> None:
            recibidos.update(kwargs)

        async def analyze(self, site_id: uuid.UUID) -> list:
            return []

    monkeypatch.setattr(
        "server.app.modules.curation.deterministic_detector.DeterministicQualityDetector",
        _DetectorEspia,
    )

    sitio = _Sitio(config_json={
        "stale_days": 1095,
        "thin_min_tokens": 40,
        "version_series_policy": "superseded",
    })
    despachador = DeterministicDetectorDispatcher(lambda: _Sesion(sitio))

    await despachador.analyze(uuid.uuid4())

    assert recibidos["stale_days"] == 1095
    assert recibidos["thin_token_threshold"] == 40
    assert recibidos["version_series_policy"] == "superseded"


@pytest.mark.asyncio
async def test_un_sitio_que_no_declara_nada_conserva_el_criterio_de_hoy(monkeypatch):
    """Desplegar esto no puede cambiarle el informe a quien no ha tocado nada."""
    recibidos: dict = {}

    class _DetectorEspia:
        def __init__(self, session: Any, **kwargs: Any) -> None:
            recibidos.update(kwargs)

        async def analyze(self, site_id: uuid.UUID) -> list:
            return []

    monkeypatch.setattr(
        "server.app.modules.curation.deterministic_detector.DeterministicQualityDetector",
        _DetectorEspia,
    )

    despachador = DeterministicDetectorDispatcher(lambda: _Sesion(_Sitio()))

    await despachador.analyze(uuid.uuid4())

    assert recibidos["stale_days"] == 365
    assert recibidos["thin_token_threshold"] == 120
    assert recibidos["version_series_policy"] == "series"
