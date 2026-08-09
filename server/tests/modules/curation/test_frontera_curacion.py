"""Guardarraíl de frontera entre `agents_hub` y `curation` (CUR.1).

`ingestion/quality/` y los spiders dejan de ser un detalle de la ingesta y pasan a
`modules/curation/`, el módulo propio de la herramienta de curación
(`docs/DECISION_CURACION_SEPARADA.md`). La regla que sostiene la separación es de
importación, no de directorio, y por eso se vigila con grep sobre el árbol, como los
guardarraíles de TST y CAL.1:

- `curation` no importa de `agents_hub/agent/` (el grafo LangGraph) ni de routers cloud.
  Puede usar `services/embedding_resolver` y `core/` compartidos.
- `agents_hub` no importa de `curation`. La única comunicación entre las dos mitades es la
  tabla `hub_content_findings`, con su CHECK de sujeto único.
- `gap_detector.py` nace de conversaciones (`HubInteraction`), no de páginas: es la señal que
  el asistente EMITE hacia la curación, y por eso se queda en `agents_hub`, no en `curation`.
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
SERVIDOR = RAIZ / "server"
CURATION = SERVIDOR / "app" / "modules" / "curation"
AGENTS_HUB = SERVIDOR / "app" / "modules" / "agents_hub"


def _fuentes(directorio: Path) -> list[Path]:
    return [
        f
        for f in directorio.rglob("*.py")
        if ".venv" not in f.parts and "__pycache__" not in f.parts
    ]


def test_should_not_import_agent_module_from_curation() -> None:
    culpables = [
        str(f.relative_to(RAIZ))
        for f in _fuentes(CURATION)
        if "modules.agents_hub.agent" in f.read_text(encoding="utf-8", errors="ignore")
        or "modules.agents_hub import agent" in f.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not culpables, (
        f"curation importa del grafo del agente: {culpables}. La curación es previa al "
        "asistente y no puede depender de su lógica de conversación."
    )


def test_should_not_import_cloud_routers_from_curation() -> None:
    culpables = [
        str(f.relative_to(RAIZ))
        for f in _fuentes(CURATION)
        if "from server.app.routers" in f.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not culpables, (
        f"curation importa un router: {culpables}. Los routers consumen servicios, nunca "
        "al revés."
    )


def test_should_not_import_curation_from_agents_hub() -> None:
    culpables = [
        str(f.relative_to(RAIZ))
        for f in _fuentes(AGENTS_HUB)
        if "modules.curation" in f.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not culpables, (
        f"agents_hub importa de curation: {culpables}. La única comunicación autorizada "
        "entre las dos mitades es la tabla hub_content_findings."
    )


def test_should_keep_gap_detector_in_agents_hub() -> None:
    """La señal de huecos de corpus (RAG.14) nace del uso del chatbot, no de auditar páginas."""
    assert (AGENTS_HUB / "ingestion" / "gap_detector.py").is_file(), (
        "gap_detector.py no está donde CUR.1 lo deja: agents_hub/ingestion/gap_detector.py"
    )
    assert not (CURATION / "gap_detector.py").exists(), (
        "gap_detector.py se coló en curation; su sujeto es un chatbot, no un sitio, y su "
        "señal la emite el asistente hacia la curación, no al revés"
    )


def test_should_have_no_leftover_quality_package() -> None:
    """El movimiento fue completo: `ingestion/quality/` y `ingestion/spiders/` ya no existen."""
    ingestion = AGENTS_HUB / "ingestion"
    assert not (ingestion / "quality").exists(), "ingestion/quality/ debería haberse vaciado a curation/"
    assert not (ingestion / "spiders").exists(), "ingestion/spiders/ debería haberse movido a curation/spiders/"
