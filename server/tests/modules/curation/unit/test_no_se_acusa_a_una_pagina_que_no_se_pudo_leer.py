"""A una página que no se ha podido leer no se le llama vacía ni pobre (RAS.2).

`empty` es crítico y `thin` es un aviso de contenido pobre. Las dos afirmaciones son sobre **la
página**, y ninguna se sostiene cuando lo que ha pasado es que el rastreador no ha podido leerla:
entonces lo único que el sistema sabe de verdad es «no se ha podido leer sin renderizar».

Es la diferencia entre un informe de calidad que alguien de la casa se cree y uno que descarta en la
primera página que conoce.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest

from server.app.modules.curation.deterministic_detector import DeterministicQualityDetector


@dataclass
class _Pagina:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    url: str = "https://www.uji.es/centres/escola-doctorat/cercador"
    markdown_content: str | None = ""
    token_count: int | None = 0
    status: str = "active"
    error_message: str | None = None
    canonical_url: str | None = None
    sitemap_lastmod: datetime | None = None
    http_last_modified: datetime | None = None
    content_year: int | None = None
    first_seen_at: datetime | None = None
    render_signals: list[dict] | None = None


class _RepoDeHallazgos:
    def __init__(self) -> None:
        self.guardados: list[Any] = []

    async def upsert(self, finding: Any) -> Any:
        self.guardados.append(finding)
        return finding


class _SesionConPaginas:
    def __init__(self, paginas: list[_Pagina]) -> None:
        self._paginas = paginas

    async def execute(self, stmt: Any) -> Any:
        hint = getattr(stmt, "_model_hint", "page")

        class _Resultado:
            def __init__(self, filas: list) -> None:
                self._filas = filas

            def scalars(self) -> Any:
                return self

            def all(self) -> list:
                return self._filas

        return _Resultado(self._paginas if hint == "page" else [])


async def _analizar(pagina: _Pagina) -> list[Any]:
    repo = _RepoDeHallazgos()
    detector = DeterministicQualityDetector(
        session=_SesionConPaginas([pagina]),
        finding_repo=repo,
        now_fn=lambda: datetime(2026, 8, 18, tzinfo=timezone.utc),
    )
    return await detector.analyze(uuid.uuid4())


_SENAL = [{"codigo": "contenedor_vacio", "detalle": 'div id="root" sin contenido'}]


@pytest.mark.asyncio
async def test_una_pagina_con_evidencia_de_dinamismo_no_es_vacia_sino_ilegible():
    hallazgos = await _analizar(_Pagina(markdown_content="", token_count=0,
                                        render_signals=_SENAL))

    tipos = [h.finding_type for h in hallazgos]
    assert "needs_javascript" in tipos
    assert "empty" not in tipos


@pytest.mark.asyncio
async def test_el_aviso_no_es_critico_porque_no_afirma_nada_de_la_pagina():
    hallazgos = await _analizar(_Pagina(markdown_content="", token_count=0,
                                        render_signals=_SENAL))

    aviso = next(h for h in hallazgos if h.finding_type == "needs_javascript")
    assert aviso.severity == "warning"


@pytest.mark.asyncio
async def test_el_aviso_lleva_la_evidencia_para_poder_revisarlo():
    hallazgos = await _analizar(_Pagina(markdown_content="", token_count=0,
                                        render_signals=_SENAL))

    aviso = next(h for h in hallazgos if h.finding_type == "needs_javascript")
    assert "contenedor_vacio" in str(aviso.signal)


@pytest.mark.asyncio
async def test_tampoco_se_le_llama_pobre_a_la_que_no_se_pudo_leer():
    hallazgos = await _analizar(_Pagina(markdown_content="Cargando", token_count=3,
                                        render_signals=_SENAL))

    tipos = [h.finding_type for h in hallazgos]
    assert "needs_javascript" in tipos
    assert "thin" not in tipos


@pytest.mark.asyncio
async def test_una_pagina_vacia_de_verdad_sigue_siendo_un_hallazgo_critico():
    """Sin evidencia de dinamismo, una página sin contenido es exactamente eso."""
    hallazgos = await _analizar(_Pagina(markdown_content="", token_count=0,
                                        render_signals=None))

    tipos = [h.finding_type for h in hallazgos]
    assert "empty" in tipos
    assert "needs_javascript" not in tipos


@pytest.mark.asyncio
async def test_una_pagina_pobre_de_verdad_sigue_siendo_thin():
    hallazgos = await _analizar(_Pagina(markdown_content="Tres palabras aqui",
                                        token_count=4, render_signals=None))

    assert "thin" in [h.finding_type for h in hallazgos]


def test_needs_javascript_es_un_tipo_de_hallazgo_del_contrato():
    """Si no está en el contrato, el hallazgo no se puede ni guardar ni revisar."""
    from typing import get_args

    from server.app.modules.curation.contracts import FindingType

    assert "needs_javascript" in get_args(FindingType)
