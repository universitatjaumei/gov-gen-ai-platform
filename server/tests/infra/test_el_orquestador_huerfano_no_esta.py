"""El consumidor de las dos tablas legacy ya no está (LEG.3).

`knowledge_orchestrator_service.py` era el **único** que leía `ExtractionServiceConfig` y
`SystemPrompt`, y **no lo importaba nadie**: cero referencias en `server/`, 0 % de cobertura, 220
líneas sin ejecutar nunca. Es el Caso B de CLAUDE.md —huérfano sin migración activa—, así que se
borra: el historial de git es la fuente de verdad del pasado.

`AutomationLibrary` **no se toca**: la importaba este orquestador, pero también `library_service`, que
está vivo y lo usa `library_router`.
"""
from __future__ import annotations

import re
from pathlib import Path

SERVER = Path(__file__).resolve().parents[2]


def test_el_orquestador_huerfano_ya_no_existe():
    assert not (SERVER / "app" / "services" / "knowledge_orchestrator_service.py").exists()


def test_nadie_lo_importa():
    """El `grep -r` a cero que exige CLAUDE.md, escrito como test para que no vuelva.

    Busca **imports**, no menciones: nombrarlo en un comentario o en el docstring de otro test
    —explicando por qué se retiró— no es una referencia viva, y un guardarraíl que da falsos
    positivos se acaba desactivando.
    """
    importado = re.compile(r"^\s*(?:from|import)\s+[\w.]*knowledge_orchestrator", re.MULTILINE)
    culpables: list[str] = []
    for carpeta in ("app", "tests", "migrations"):
        for fichero in (SERVER / carpeta).rglob("*.py"):
            if "__pycache__" in str(fichero) or fichero.name == Path(__file__).name:
                continue
            if importado.search(fichero.read_text(encoding="utf-8", errors="ignore")):
                culpables.append(str(fichero.relative_to(SERVER)))
    assert culpables == [], f"quedan imports del orquestador huérfano: {culpables}"


def test_la_biblioteca_de_automatizaciones_sigue_viva():
    """La frontera que el plan marcaba: se retira el orquestador, no lo que también usa otro."""
    from server.app.database.models import AutomationLibrary
    from server.app.services import library_service

    assert AutomationLibrary is not None
    assert library_service is not None
