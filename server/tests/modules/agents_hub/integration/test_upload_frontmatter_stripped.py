"""La subida del panel debe tratar el front-matter igual que el CLI de curación.

`corpus/source.py` (el CLI) separa front-matter y cuerpo con `parse_frontmatter` antes de
ingerir: el cuerpo es lo que se embebe, y `language` del front-matter es dato de primera
clase (CONTRATO_MD_CORPUS.md §3). La subida del panel (`upload_document` -> `run_job`) leía
el fichero de storage y lo pasaba entero — front-matter incluido — a `process_source`, así
que:

1. El bloque YAML se guardaba y se troceaba como si fuera contenido del documento, violando
   CLAUDE.md §5 (nada de metadatos en el texto que se embebe).
2. El `language:` declarado en el front-matter nunca se leía: sin selección explícita en el
   desplegable del panel, `language=None` caía a `detect_language()` sobre el texto crudo
   —front-matter incluido—, que es una fuente mucho peor que un campo declarado a mano.

Encontrado verificando a mano el Camino 2 de plataforma: un `.md` con `language: es` en el
front-matter (y encabezados de sección en catalán, herencia del esqueleto de ejemplo del
contrato) se guardó con `language='ca'`.
"""
from __future__ import annotations

import uuid

import pytest


class _Embedding:
    model_name = "BAAI/bge-m3"
    dimensions = 1024

    async def embed(self, text: str) -> list[float]:
        return [0.1] * 1024

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1024 for _ in texts]


class _Provider:
    async def get_retrieval_mode(self, chatbot_id):
        return "RAG"


class _StorageDeUnSoloFichero:
    """Doble mínimo de `StorageService`: sirve siempre el mismo contenido."""

    def __init__(self, contenido: str) -> None:
        self._contenido = contenido

    async def get(self, key: str) -> bytes:
        return self._contenido.encode("utf-8")


CONTENIDO_CON_FRONTMATTER = """---
id_publicacio: TEST-FM
title: Reglament de prova
language: es
url_oficial: https://www.uji.es/prueba
---

# Reglament de prova

##### Article 1. Objecte {#art-1}

Este reglamento de prueba fija el importe en 42 euros.
"""


async def _job_de_subida(session, chatbot_id: uuid.UUID):
    """Un job cuyo `source_url` es una clave de storage, no una URL http(s) -- así se
    ejercita la misma rama que la subida real del panel, y no la del prefetch directo que
    ya cubre `test_job_progress.py`."""
    from server.app.modules.agents_hub.database.operational_models import HubIngestionJob

    job = HubIngestionJob(
        chatbot_id=chatbot_id,
        source_url=f"ingestion/{chatbot_id}/{uuid.uuid4()}.md",
        language=None,  # "Detecta-ho automàticament" en el desplegable del panel
    )
    session.add(job)
    await session.flush()
    return job


class TestElFrontMatterSeSepara:

    @pytest.mark.asyncio
    async def test_should_not_embed_the_yaml_frontmatter_block(self, db_session):
        chatbot_id = uuid.uuid4()
        job = await _job_de_subida(db_session, chatbot_id)
        await db_session.commit()

        watcher_cls = __import__(
            "server.app.modules.agents_hub.ingestion.watcher", fromlist=["IngestionWatcher"]
        ).IngestionWatcher
        watcher = watcher_cls(
            db_session,
            _Embedding(),
            storage=_StorageDeUnSoloFichero(CONTENIDO_CON_FRONTMATTER),
            chatbot_provider=_Provider(),
        )
        await watcher.run_job(job.id)

        from sqlalchemy import select
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        doc = (
            await db_session.execute(
                select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
            )
        ).scalar_one()

        assert "id_publicacio" not in doc.markdown_content
        assert "---" not in doc.markdown_content.split("\n", 1)[0]
        assert doc.markdown_content.startswith("# Reglament de prova")

    @pytest.mark.asyncio
    async def test_should_use_the_frontmatter_language_when_the_dropdown_is_auto(
        self, db_session
    ):
        chatbot_id = uuid.uuid4()
        job = await _job_de_subida(db_session, chatbot_id)
        await db_session.commit()

        watcher_cls = __import__(
            "server.app.modules.agents_hub.ingestion.watcher", fromlist=["IngestionWatcher"]
        ).IngestionWatcher
        watcher = watcher_cls(
            db_session,
            _Embedding(),
            storage=_StorageDeUnSoloFichero(CONTENIDO_CON_FRONTMATTER),
            chatbot_provider=_Provider(),
        )
        await watcher.run_job(job.id)

        from sqlalchemy import select
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        doc = (
            await db_session.execute(
                select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
            )
        ).scalar_one()

        assert doc.language == "es"
