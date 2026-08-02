"""Tests TDD — Caducidad activa del corpus (Prompt SYNC.2).

El sync solo detecta lo que **cambia en origen**. Una norma que nadie toca durante tres años
no genera ninguna señal, y sin embargo es exactamente el riesgo nº1 del informe: 312 de 314
fichas dicen «vigent?». Este detector convierte el paso del tiempo en una señal.

Su fuente es `data_revisio_prevista`, la columna de ING.0.2. Cuando el front-matter no la
trae, se pone una por defecto **al ingerir** —un año—; las normas de vigencia anual, como el
Presupuesto, la traen explícita y más corta.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select


class _FakeEmbedding:
    model_name = "BAAI/bge-m3"
    dimensions = 1024

    async def embed(self, text: str) -> list[float]:
        return [0.1] * 1024


class _FakeChatbotProvider:
    async def get_retrieval_mode(self, chatbot_id: uuid.UUID) -> str:
        return "RAG"


FRONT = """---
id_publicacio: {id}
title: Norma {id}
language: ca
url_oficial: https://www.uji.es/{id}
{extra}---

# Norma {id}

##### Article 1. Objecte {{#art-1}}

Text de la norma.
"""


def _escribir(directorio, id_publicacio: str, extra: str = ""):
    ruta = directorio / f"{id_publicacio}.md"
    ruta.write_text(FRONT.format(id=id_publicacio, extra=extra), encoding="utf-8")
    return ruta


async def _cargar(session, directorio, chatbot_id):
    from server.app.modules.agents_hub.ingestion.corpus.reconciler import CorpusReconciler
    from server.app.modules.agents_hub.ingestion.corpus.source import LocalDirectorySource
    from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

    reconciler = CorpusReconciler(
        session,
        IngestionWatcher(session, _FakeEmbedding(), chatbot_provider=_FakeChatbotProvider()),
    )
    return await reconciler.reconcile(LocalDirectorySource(directorio), chatbot_id)


async def _documentos(session, chatbot_id):
    from server.app.modules.agents_hub.database.operational_models import HubDocument

    filas = await session.execute(
        select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
    )
    return {d.id_publicacio: d for d in filas.scalars().all()}


async def _findings(session, chatbot_id):
    from server.app.modules.agents_hub.database.operational_models import HubContentFinding

    filas = await session.execute(
        select(HubContentFinding)
        .where(HubContentFinding.chatbot_id == chatbot_id)
        .where(HubContentFinding.finding_type == "revisio_vencuda")
    )
    return list(filas.scalars().all())


# ───────────────────────── La fecha por defecto, al ingerir ─────────────────────────


class TestFechaDeRevision:

    @pytest.mark.asyncio
    async def test_should_default_review_date_to_one_year_on_ingest(
        self, tmp_path, db_session
    ):
        """Sin fecha no hay caducidad posible, y el corpus envejecería en silencio."""
        chatbot_id = uuid.uuid4()
        _escribir(tmp_path, "REG-1")

        await _cargar(db_session, tmp_path, chatbot_id)

        doc = (await _documentos(db_session, chatbot_id))["REG-1"]
        esperada = date.today() + timedelta(days=365)
        assert doc.data_revisio_prevista is not None
        assert abs((doc.data_revisio_prevista - esperada).days) <= 1

    @pytest.mark.asyncio
    async def test_should_respect_explicit_review_date_from_frontmatter(
        self, tmp_path, db_session
    ):
        """El Presupuesto es anual y lo dice; el default no puede pisarlo."""
        chatbot_id = uuid.uuid4()
        _escribir(tmp_path, "REG-1", extra="data_revisio_prevista: 2026-12-31\n")

        await _cargar(db_session, tmp_path, chatbot_id)

        doc = (await _documentos(db_session, chatbot_id))["REG-1"]
        assert doc.data_revisio_prevista == date(2026, 12, 31)

    @pytest.mark.asyncio
    async def test_should_not_push_the_default_forward_on_every_run(
        self, tmp_path, db_session
    ):
        """Si cada pasada renovara la fecha, nada venceria jamas.

        Es el fallo silencioso de esta funcionalidad: el detector seguiria funcionando y no
        encontraria nunca nada, que se parece mucho a que el corpus este al dia.
        """
        chatbot_id = uuid.uuid4()
        _escribir(tmp_path, "REG-1")
        await _cargar(db_session, tmp_path, chatbot_id)
        doc = (await _documentos(db_session, chatbot_id))["REG-1"]
        doc.data_revisio_prevista = date.today() - timedelta(days=10)
        await db_session.flush()

        await _cargar(db_session, tmp_path, chatbot_id)

        doc = (await _documentos(db_session, chatbot_id))["REG-1"]
        assert doc.data_revisio_prevista == date.today() - timedelta(days=10)


# ───────────────────────── El detector ─────────────────────────


class TestDetectorDeCaducidad:

    @pytest.mark.asyncio
    async def test_should_emit_finding_for_document_past_its_review_date(
        self, tmp_path, db_session
    ):
        from server.app.modules.agents_hub.ingestion.quality.staleness_detector import (
            analizar_caducidad,
        )

        chatbot_id = uuid.uuid4()
        _escribir(tmp_path, "REG-1", extra="data_revisio_prevista: 2020-01-01\n")
        await _cargar(db_session, tmp_path, chatbot_id)

        cuantos = await analizar_caducidad(db_session, chatbot_id)

        assert cuantos == 1
        hallazgos = await _findings(db_session, chatbot_id)
        assert len(hallazgos) == 1
        señal = hallazgos[0].signal_json
        assert señal["id_publicacio"] == "REG-1"
        assert señal["data_revisio_prevista"] == "2020-01-01"
        assert señal["dies_de_retard"] > 0
        assert señal["darrera_actualitzacio"], "sin la última actualización no se puede juzgar"

    @pytest.mark.asyncio
    async def test_should_not_emit_for_document_within_review_window(
        self, tmp_path, db_session
    ):
        from server.app.modules.agents_hub.ingestion.quality.staleness_detector import (
            analizar_caducidad,
        )

        chatbot_id = uuid.uuid4()
        futura = (date.today() + timedelta(days=200)).isoformat()
        _escribir(tmp_path, "REG-1", extra=f"data_revisio_prevista: {futura}\n")
        await _cargar(db_session, tmp_path, chatbot_id)

        cuantos = await analizar_caducidad(db_session, chatbot_id)

        assert cuantos == 0
        assert await _findings(db_session, chatbot_id) == []

    @pytest.mark.asyncio
    async def test_should_not_duplicate_open_finding_for_same_document(
        self, tmp_path, db_session
    ):
        """El detector corre periódicamente: sin deduplicar, la cola muere en una semana."""
        from server.app.modules.agents_hub.ingestion.quality.staleness_detector import (
            analizar_caducidad,
        )

        chatbot_id = uuid.uuid4()
        _escribir(tmp_path, "REG-1", extra="data_revisio_prevista: 2020-01-01\n")
        await _cargar(db_session, tmp_path, chatbot_id)

        await analizar_caducidad(db_session, chatbot_id)
        await analizar_caducidad(db_session, chatbot_id)
        await analizar_caducidad(db_session, chatbot_id)

        assert len(await _findings(db_session, chatbot_id)) == 1

    @pytest.mark.asyncio
    async def test_should_reopen_after_the_finding_was_resolved(
        self, tmp_path, db_session
    ):
        """Un hallazgo cerrado no bloquea uno nuevo: si sigue vencida, hay que volver a decirlo.

        Mismo criterio que RAG.14. Lo contrario convierte «resolved» en un silenciador
        permanente sobre un documento que nadie ha revisado.
        """
        from server.app.modules.agents_hub.ingestion.quality.staleness_detector import (
            analizar_caducidad,
        )

        chatbot_id = uuid.uuid4()
        _escribir(tmp_path, "REG-1", extra="data_revisio_prevista: 2020-01-01\n")
        await _cargar(db_session, tmp_path, chatbot_id)
        await analizar_caducidad(db_session, chatbot_id)

        (await _findings(db_session, chatbot_id))[0].status = "resolved"
        await db_session.flush()
        await analizar_caducidad(db_session, chatbot_id)

        assert len(await _findings(db_session, chatbot_id)) == 2

    @pytest.mark.asyncio
    async def test_should_ignore_documents_excluded_from_the_assistant(
        self, tmp_path, db_session
    ):
        """Lo que no se indexa no caduca: avisaría de algo que nadie va a leer."""
        from server.app.modules.agents_hub.ingestion.quality.staleness_detector import (
            analizar_caducidad,
        )

        chatbot_id = uuid.uuid4()
        _escribir(tmp_path, "REG-1", extra="data_revisio_prevista: 2020-01-01\n")
        await _cargar(db_session, tmp_path, chatbot_id)
        doc = (await _documentos(db_session, chatbot_id))["REG-1"]
        doc.us_assistents = "no"
        await db_session.flush()

        assert await analizar_caducidad(db_session, chatbot_id) == 0

    @pytest.mark.asyncio
    async def test_should_scope_findings_by_chatbot(self, tmp_path, db_session):
        from server.app.modules.agents_hub.ingestion.quality.staleness_detector import (
            analizar_caducidad,
        )

        uno, otro = uuid.uuid4(), uuid.uuid4()
        _escribir(tmp_path, "REG-1", extra="data_revisio_prevista: 2020-01-01\n")
        await _cargar(db_session, tmp_path, uno)
        await _cargar(db_session, tmp_path, otro)

        await analizar_caducidad(db_session, uno)

        assert len(await _findings(db_session, uno)) == 1
        assert await _findings(db_session, otro) == []

    @pytest.mark.asyncio
    async def test_should_grade_severity_by_how_late_the_review_is(
        self, tmp_path, db_session
    ):
        """Una semana de retraso y tres años no son el mismo problema."""
        from server.app.modules.agents_hub.ingestion.quality.staleness_detector import (
            analizar_caducidad,
        )

        chatbot_id = uuid.uuid4()
        reciente = (date.today() - timedelta(days=5)).isoformat()
        _escribir(tmp_path, "REG-1", extra=f"data_revisio_prevista: {reciente}\n")
        _escribir(tmp_path, "REG-2", extra="data_revisio_prevista: 2019-01-01\n")
        await _cargar(db_session, tmp_path, chatbot_id)

        await analizar_caducidad(db_session, chatbot_id)

        por_id = {f.signal_json["id_publicacio"]: f for f in await _findings(db_session, chatbot_id)}
        assert por_id["REG-1"].severity == "warning"
        assert por_id["REG-2"].severity == "critical"


# ───────────────────── La cola de revisión, con los tres tipos ─────────────────────


class TestColaDeRevision:

    @pytest.mark.asyncio
    async def test_should_keep_existing_9q_finding_tests_green(self):
        """`revisio_vencuda` entra en el contrato sin desplazar a los que ya estaban."""
        from server.app.modules.agents_hub.ingestion.quality.contracts import (
            ContentFinding,
            FindingType,
        )

        tipos = set(FindingType.__args__)
        assert {"superseded", "duplicate", "contradiction", "content_gap"} <= tipos
        assert "revisio_vencuda" in tipos

        finding = ContentFinding(
            id=uuid.uuid4(),
            chatbot_id=uuid.uuid4(),
            finding_type="revisio_vencuda",
            severity="warning",
            confidence=1.0,
            detected_at=datetime.now(timezone.utc),
        )
        assert finding.site_id is None

    @pytest.mark.asyncio
    async def test_should_expose_the_three_finding_types_in_one_queue(
        self, tmp_path, db_session
    ):
        """El admin tiene UNA cola: huecos de RAG.14, retiradas de SYNC.1 y caducidades."""
        from server.app.modules.agents_hub.database.operational_models import (
            HubContentFinding,
        )
        from server.app.modules.agents_hub.ingestion.quality.staleness_detector import (
            analizar_caducidad,
            listar_caducados,
        )

        chatbot_id = uuid.uuid4()
        _escribir(tmp_path, "REG-1", extra="data_revisio_prevista: 2020-01-01\n")
        await _cargar(db_session, tmp_path, chatbot_id)
        await analizar_caducidad(db_session, chatbot_id)
        db_session.add(
            HubContentFinding(
                chatbot_id=chatbot_id,
                finding_type="content_gap",
                severity="info",
                confidence=0.5,
                detected_at=datetime.now(timezone.utc),
                signal_json={"count": 3},
            )
        )
        await db_session.flush()

        caducados = await listar_caducados(db_session, chatbot_id)

        assert len(caducados) == 1, "listar_caducados filtra por tipo y no arrastra los huecos"
        assert caducados[0].finding_type == "revisio_vencuda"
