"""Tests TDD — Reconciliador de corpus (Prompt ING.0.5).

Un reconciliador, dos fuentes: aquí la carpeta local, en SYNC.1 el servicio MCP. Si
SYNC.1 acaba reimplementando emparejamiento, deltas o poda, está mal.

Lo incremental no es un modo: emerge del hash. **El censo sí es un modo, y es peligroso**:
`--prune` sobre una subcarpeta retiraría cientos de normas, así que exige que la fuente
declare corpus completo y lleva salvaguarda de proporción.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import func, select


# ───────────────────────── Fakes ─────────────────────────


class _FakeEmbedding:
    # RAG.9: la procedencia es NOT NULL, así que un doble sin declararla ya no representa
    # a ningún servicio real — el watcher lo rechaza antes de escribir un vector anónimo.
    model_name = "BAAI/bge-m3"
    dimensions = 1024

    def __init__(self) -> None:
        self.llamadas = 0

    async def embed(self, text: str) -> list[float]:
        self.llamadas += 1
        return [0.1] * 1024


class _FakeChatbotProvider:
    def __init__(self, mode: str = "RAG") -> None:
        self.mode = mode

    async def get_retrieval_mode(self, chatbot_id: uuid.UUID) -> str:
        return self.mode


FRONT = """---
id_publicacio: {id}
title: {title}
language: ca
url_oficial: https://www.uji.es/{id}
ambit_principal: administracio
submateries: [indemnitzacions-i-dietes]
{extra}---

# {title}

##### Article 1. Objecte {{#art-1}}

{body}
"""


def _escribir(
    directorio: Path,
    id_publicacio: str,
    *,
    title: str | None = None,
    body: str = "Text de la norma.",
    extra: str = "",
) -> Path:
    ruta = directorio / f"{id_publicacio}.md"
    ruta.write_text(
        FRONT.format(
            id=id_publicacio,
            title=title or f"Norma {id_publicacio}",
            body=body,
            extra=extra,
        ),
        encoding="utf-8",
    )
    return ruta


# ───────────────────── Las dos fuentes, la misma reconciliación ─────────────────────
#
# SYNC.1 exige que la carpeta local y el servicio de publicación den EL MISMO resultado.
# Sin esto, «no se reimplementa la reconciliación» sería una promesa: la única forma de
# comprobarlo es correr la suite entera contra las dos fuentes. La fixture es autouse y
# parametrizada, así que cada test de este fichero se ejecuta dos veces.


def _fuente_local(directorio: Path, *, census: bool):
    from server.app.modules.agents_hub.ingestion.corpus.source import LocalDirectorySource

    return LocalDirectorySource(directorio, is_census_declared=census)


class _TransporteFalso:
    """Sirve por JSON-RPC los mismos `.md` que la carpeta, sin tocar la red."""

    def __init__(self, datasets: dict[str, list[dict]]) -> None:
        self.datasets = datasets

    async def call(self, payload: dict) -> dict:
        import json

        code = payload["params"]["arguments"]["dataset_code"]
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(self.datasets[code], ensure_ascii=False),
                    }
                ]
            },
        }


def _fuente_publicacion(directorio: Path, *, census: bool):
    from server.app.modules.agents_hub.ingestion.corpus.frontmatter import (
        hash_markdown_body,
        parse_frontmatter,
    )
    from server.app.modules.agents_hub.ingestion.corpus.publication_client import (
        PublicationMcpClient,
    )
    from server.app.modules.agents_hub.ingestion.corpus.publication_source import (
        PublicationMcpSource,
    )

    indice, contenido = [], []
    for ruta in sorted(directorio.rglob("*.md")):
        texto = ruta.read_text(encoding="utf-8-sig", errors="replace")
        metadatos, cuerpo = parse_frontmatter(texto)
        relativa = ruta.relative_to(directorio).as_posix()
        indice.append({
            "id_publicacio": metadatos.get("id_publicacio"),
            "relative_path": relativa,
            # El índice declara el hash, que es lo que permite no descargar lo no cambiado.
            # Corriendo la suite con esto activado, el atajo queda cubierto por los ~22
            # tests de reconciliación y no solo por los suyos propios.
            "content_hash": hash_markdown_body(cuerpo),
            "metadades": metadatos,
        })
        contenido.append({
            "id_publicacio": metadatos.get("id_publicacio"),
            "relative_path": relativa,
            "markdown": texto,
        })

    cliente = PublicationMcpClient(
        url="https://mcp.example/rpc",
        token="tok-de-prueba",
        transport=_TransporteFalso({"IDX": indice, "CNT": contenido}),
    )
    return PublicationMcpSource(
        cliente, index_dataset="IDX", content_dataset="CNT", is_census_declared=census
    )


_FABRICAS = {"carpeta_local": _fuente_local, "servicio_mcp": _fuente_publicacion}
_FABRICA_ACTUAL = _fuente_local


@pytest.fixture(autouse=True, params=sorted(_FABRICAS))
def fuente_parametrizada(request):
    """Fija con qué `CorpusSource` corre este test. Ambas deben dar el mismo resultado."""
    global _FABRICA_ACTUAL
    _FABRICA_ACTUAL = _FABRICAS[request.param]
    yield request.param
    _FABRICA_ACTUAL = _fuente_local


async def _reconciliar(session, directorio: Path, chatbot_id, **kwargs):
    from server.app.modules.agents_hub.ingestion.corpus.reconciler import (
        CorpusReconciler,
    )
    from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

    fuente = _FABRICA_ACTUAL(directorio, census=kwargs.pop("census", False))
    watcher = IngestionWatcher(
        session,
        kwargs.pop("embedding", None) or _FakeEmbedding(),
        chatbot_provider=_FakeChatbotProvider(kwargs.pop("mode", "RAG")),
    )
    reconciler = CorpusReconciler(session, watcher)
    return await reconciler.reconcile(fuente, chatbot_id, **kwargs)


async def _chatbot(session, organizacion_id=None):
    """Un chatbot de verdad en la BD: ACT.5 necesita saber de que organizacion es.

    Se monta la cadena entera —proveedor, config de LLM, organizacion— porque las claves
    ajenas la exigen; es el mismo montaje que `test_embedding_resolution`.
    """
    from server.app.modules.agents_hub.database.config_models import (
        HubChatbot,
        HubLLMConfig,
        HubOrganizacion,
        HubProvider,
    )

    await session.merge(
        HubProvider(id="google", name="Google", provider_type="google_genai")
    )
    llm = HubLLMConfig(provider="google", model_name="gemini-flash", purpose="chat")
    session.add(llm)
    if organizacion_id is None:
        org = HubOrganizacion(name="UJI", partner_id="partner_dev")
        session.add(org)
        await session.flush()
        organizacion_id = org.id
    await session.flush()
    cb = HubChatbot(
        organizacion_id=organizacion_id, llm_config_id=llm.id,
        name=f"Chatbot {uuid.uuid4().hex[:6]}", system_prompt="x", sources=[],
    )
    session.add(cb)
    await session.flush()
    return cb.id


async def _dos_chatbots_de_la_misma_organizacion(session):
    from server.app.modules.agents_hub.database.config_models import HubOrganizacion

    org = HubOrganizacion(name="UJI", partner_id="partner_dev")
    session.add(org)
    await session.flush()
    return await _chatbot(session, org.id), await _chatbot(session, org.id)


async def _fragmentos(session, chatbot_id):
    from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk

    filas = (
        await session.execute(
            select(HubDocumentChunk).where(HubDocumentChunk.chatbot_id == chatbot_id)
        )
    ).scalars().all()
    return [
        {
            "chatbot_id": f.chatbot_id,
            "document_id": f.document_id,
            "chunk_metadata": f.chunk_metadata,
            "embedding": list(f.embedding) if f.embedding is not None else None,
            "parent_content": f.parent_content,
        }
        for f in filas
    ]


async def _documentos(session, chatbot_id):
    from server.app.modules.agents_hub.database.operational_models import HubDocument

    result = await session.execute(
        select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
    )
    return {d.id_publicacio or d.canonical_url: d for d in result.scalars().all()}


# ───────────────────────── Ingesta y idempotencia ─────────────────────────


class TestIngesta:

    @pytest.mark.asyncio
    async def test_should_ingest_markdown_passthrough_without_docling(
        self, db_session, tmp_path
    ):
        _escribir(tmp_path, "REG-001")
        chatbot_id = uuid.uuid4()

        informe = await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        assert informe.ingeridos == 1
        docs = await _documentos(db_session, chatbot_id)
        assert "REG-001" in docs
        assert "Article 1" in docs["REG-001"].markdown_content

    @pytest.mark.asyncio
    async def test_should_persist_all_metadata_fields_on_hub_document(
        self, db_session, tmp_path
    ):
        _escribir(
            tmp_path,
            "REG-002",
            extra="nivell_acces: intern\nestat_vigencia: vigent\nrang: reglament\n",
        )
        chatbot_id = uuid.uuid4()

        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        doc = (await _documentos(db_session, chatbot_id))["REG-002"]
        assert doc.ambit_principal == "administracio"
        assert doc.submateries == ["indemnitzacions-i-dietes"]
        assert doc.nivell_acces == "intern"
        assert doc.estat_vigencia == "vigent"
        assert doc.doc_metadata["rang"] == "reglament"
        assert doc.source_kind == "publicacio"
        assert doc.last_seen_at is not None

    @pytest.mark.asyncio
    async def test_should_prefer_declared_language_over_detection(
        self, db_session, tmp_path
    ):
        _escribir(tmp_path, "REG-003", body="Texto claramente en castellano y largo.")
        chatbot_id = uuid.uuid4()

        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        assert (await _documentos(db_session, chatbot_id))["REG-003"].language == "ca"

    @pytest.mark.asyncio
    async def test_should_skip_unchanged_document_by_content_hash(
        self, db_session, tmp_path
    ):
        _escribir(tmp_path, "REG-004")
        chatbot_id = uuid.uuid4()
        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        embedding = _FakeEmbedding()
        informe = await _reconciliar(
            db_session, tmp_path, chatbot_id, embedding=embedding
        )
        await db_session.commit()

        assert informe.omitidos == 1
        assert informe.ingeridos == 0 and informe.reingeridos == 0
        assert embedding.llamadas == 0, "una pasada sin cambios no debe embeber"

    @pytest.mark.asyncio
    async def test_should_update_metadata_without_rechunking_when_only_metadata_changed(
        self, db_session, tmp_path
    ):
        """La ruta que hace barata la reclasificación cuando SG revise el vocabulario."""
        from server.app.modules.agents_hub.database.operational_models import (
            HubDocumentChunk,
        )

        _escribir(tmp_path, "REG-005")
        chatbot_id = uuid.uuid4()
        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()
        chunks_antes = await db_session.scalar(
            select(func.count()).select_from(HubDocumentChunk)
        )

        _escribir(
            tmp_path,
            "REG-005",
            extra="submateries: [execucio-de-la-despesa]\n",
        )
        embedding = _FakeEmbedding()
        informe = await _reconciliar(
            db_session, tmp_path, chatbot_id, embedding=embedding
        )
        await db_session.commit()

        assert informe.metadatos_actualizados == 1
        assert informe.reingeridos == 0
        assert embedding.llamadas == 0, "reetiquetar no debe re-embeber"
        assert chunks_antes == await db_session.scalar(
            select(func.count()).select_from(HubDocumentChunk)
        )
        doc = (await _documentos(db_session, chatbot_id))["REG-005"]
        assert doc.submateries == ["execucio-de-la-despesa"]

    @pytest.mark.asyncio
    async def test_should_reingest_only_changed_document(self, db_session, tmp_path):
        _escribir(tmp_path, "REG-006")
        _escribir(tmp_path, "REG-007")
        chatbot_id = uuid.uuid4()
        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        _escribir(tmp_path, "REG-007", body="Texto corregido: 55,00 euros.")
        informe = await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        assert informe.reingeridos == 1
        assert informe.omitidos == 1
        doc = (await _documentos(db_session, chatbot_id))["REG-007"]
        assert "55,00" in doc.markdown_content


# ───────────────────────── Emparejamiento ─────────────────────────


class TestEmparejamiento:

    @pytest.mark.asyncio
    async def test_should_match_existing_document_by_id_publicacio(
        self, db_session, tmp_path
    ):
        """Aunque cambie la URL oficial, el id de publicación empareja."""
        _escribir(tmp_path, "REG-008")
        chatbot_id = uuid.uuid4()
        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        ruta = tmp_path / "REG-008.md"
        ruta.write_text(
            ruta.read_text(encoding="utf-8").replace(
                "url_oficial: https://www.uji.es/REG-008",
                "url_oficial: https://www.uji.es/nova-ruta/REG-008",
            ),
            encoding="utf-8",
        )
        informe = await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        assert informe.ingeridos == 0, "no debe crear un documento nuevo"
        total = await db_session.scalar(
            select(func.count()).select_from(
                __import__(
                    "server.app.modules.agents_hub.database.operational_models",
                    fromlist=["HubDocument"],
                ).HubDocument
            )
        )
        assert total == 1

    @pytest.mark.asyncio
    async def test_should_fall_back_to_url_and_language_when_id_publicacio_missing(
        self, db_session, tmp_path
    ):
        ruta = tmp_path / "sin-id.md"
        ruta.write_text(
            "---\nlanguage: ca\nurl_oficial: https://www.uji.es/x\n---\n\n# T\n\nText.\n",
            encoding="utf-8",
        )
        chatbot_id = uuid.uuid4()
        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        informe = await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        assert informe.omitidos == 1
        assert informe.ingeridos == 0

    @pytest.mark.asyncio
    async def test_should_stamp_last_seen_at_on_every_entry_including_unchanged(
        self, db_session, tmp_path
    ):
        _escribir(tmp_path, "REG-009")
        chatbot_id = uuid.uuid4()
        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()
        primera = (await _documentos(db_session, chatbot_id))["REG-009"].last_seen_at

        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()
        doc = (await _documentos(db_session, chatbot_id))["REG-009"]
        await db_session.refresh(doc)

        assert doc.last_seen_at >= primera


# ───────────────────────── Rechazos y omisiones ─────────────────────────


class TestRechazos:

    @pytest.mark.asyncio
    async def test_should_refuse_regulation_entry_without_review(
        self, db_session, tmp_path
    ):
        from server.app.modules.agents_hub.ingestion.corpus.manifest import (
            CorpusValidationError,
        )
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        _escribir(tmp_path, "REG-010", extra="content_class: regulation\n")
        _escribir(tmp_path, "REG-011")

        with pytest.raises(CorpusValidationError) as exc:
            await _reconciliar(db_session, tmp_path, uuid.uuid4())

        assert "revisat" in str(exc.value)
        # el paquete se rechaza ENTERO: tampoco entra el documento válido
        total = await db_session.scalar(select(func.count()).select_from(HubDocument))
        assert total == 0

    @pytest.mark.asyncio
    async def test_should_skip_documents_marked_us_assistents_no_with_reason(
        self, db_session, tmp_path
    ):
        _escribir(
            tmp_path,
            "REG-012",
            extra="us_assistents: 'no'\nmotiu_exclusio: derogat\n",
        )
        _escribir(tmp_path, "REG-013")
        chatbot_id = uuid.uuid4()

        informe = await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        assert informe.ingeridos == 1
        assert informe.omitidos == 1
        assert any("derogat" in m for m in informe.motivos_omision)
        assert "REG-012" not in await _documentos(db_session, chatbot_id)


# ───────────────────────── Censo y poda ─────────────────────────


class TestPoda:

    async def _cargar_tres(self, db_session, tmp_path, chatbot_id):
        for n in (1, 2, 3):
            _escribir(tmp_path, f"REG-10{n}")
        await _reconciliar(db_session, tmp_path, chatbot_id, census=True)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_should_not_prune_anything_without_the_prune_flag(
        self, db_session, tmp_path
    ):
        chatbot_id = uuid.uuid4()
        await self._cargar_tres(db_session, tmp_path, chatbot_id)
        (tmp_path / "REG-102.md").unlink()

        informe = await _reconciliar(db_session, tmp_path, chatbot_id, census=True)
        await db_session.commit()

        assert informe.retirados == 0
        docs = await _documentos(db_session, chatbot_id)
        assert docs["REG-102"].us_assistents == "si"

    @pytest.mark.asyncio
    async def test_should_not_prune_when_source_is_not_a_census(
        self, db_session, tmp_path
    ):
        """Un delta no distingue «retirada» de «no tocada»."""
        chatbot_id = uuid.uuid4()
        await self._cargar_tres(db_session, tmp_path, chatbot_id)
        (tmp_path / "REG-102.md").unlink()

        informe = await _reconciliar(
            db_session, tmp_path, chatbot_id, census=False, prune=True
        )
        await db_session.commit()

        assert informe.retirados == 0
        assert informe.poda_omitida_por_no_censo is True

    @pytest.mark.asyncio
    async def test_should_mark_and_emit_finding_for_pruned_document_without_deleting(
        self, db_session, tmp_path
    ):
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        chatbot_id = uuid.uuid4()
        for n in range(1, 21):
            _escribir(tmp_path, f"REG-2{n:02d}")
        await _reconciliar(db_session, tmp_path, chatbot_id, census=True)
        await db_session.commit()
        (tmp_path / "REG-205.md").unlink()

        informe = await _reconciliar(
            db_session, tmp_path, chatbot_id, census=True, prune=True
        )
        await db_session.commit()

        assert informe.retirados == 1
        total = await db_session.scalar(select(func.count()).select_from(HubDocument))
        assert total == 20, "retirada de la fuente NO es borrado"
        doc = (await _documentos(db_session, chatbot_id))["REG-205"]
        assert doc.us_assistents == "no"
        assert doc.doc_metadata["motiu_exclusio"] == "retirada_de_la_font"

    @pytest.mark.asyncio
    async def test_should_abort_prune_above_proportion_threshold(
        self, db_session, tmp_path
    ):
        """Es la red que evita convertir un --dir mal escrito en la retirada del corpus."""
        from server.app.modules.agents_hub.ingestion.corpus.reconciler import (
            PruneThresholdExceeded,
        )

        chatbot_id = uuid.uuid4()
        await self._cargar_tres(db_session, tmp_path, chatbot_id)
        (tmp_path / "REG-102.md").unlink()  # 1 de 3 = 33 % > 10 %

        with pytest.raises(PruneThresholdExceeded) as exc:
            await _reconciliar(
                db_session, tmp_path, chatbot_id, census=True, prune=True
            )
        assert "1" in str(exc.value) and "3" in str(exc.value)

    @pytest.mark.asyncio
    async def test_should_prune_above_threshold_only_with_force(
        self, db_session, tmp_path
    ):
        chatbot_id = uuid.uuid4()
        await self._cargar_tres(db_session, tmp_path, chatbot_id)
        (tmp_path / "REG-102.md").unlink()

        informe = await _reconciliar(
            db_session, tmp_path, chatbot_id, census=True, prune=True, force_prune=True
        )
        await db_session.commit()

        assert informe.retirados == 1

    @pytest.mark.asyncio
    async def test_no_vuelve_a_retirar_lo_ya_retirado(self, db_session, tmp_path):
        chatbot_id = uuid.uuid4()
        await self._cargar_tres(db_session, tmp_path, chatbot_id)
        (tmp_path / "REG-102.md").unlink()
        await _reconciliar(
            db_session, tmp_path, chatbot_id, census=True, prune=True, force_prune=True
        )
        await db_session.commit()

        informe = await _reconciliar(
            db_session, tmp_path, chatbot_id, census=True, prune=True, force_prune=True
        )
        await db_session.commit()

        assert informe.retirados == 0


# ───────────────────────── Job e informe ─────────────────────────


class TestInforme:

    @pytest.mark.asyncio
    async def test_should_record_one_ingestion_job_per_run_with_counters(
        self, db_session, tmp_path
    ):
        """Si el CLI mantiene el corpus durante meses, el historial va en la BD."""
        from server.app.modules.agents_hub.database.operational_models import (
            HubIngestionJob,
        )

        _escribir(tmp_path, "REG-301")
        chatbot_id = uuid.uuid4()
        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        jobs = (
            await db_session.execute(
                select(HubIngestionJob).where(HubIngestionJob.chatbot_id == chatbot_id)
            )
        ).scalars().all()

        assert len(jobs) == 1
        assert jobs[0].status == "completed"
        assert "ingeridos=1" in (jobs[0].error_message or "") or "ingeridos=1" in (
            jobs[0].source_url or ""
        )

    @pytest.mark.asyncio
    async def test_should_report_plan_in_dry_run_without_writing(
        self, db_session, tmp_path
    ):
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        _escribir(tmp_path, "REG-401")
        chatbot_id = uuid.uuid4()

        informe = await _reconciliar(db_session, tmp_path, chatbot_id, dry_run=True)
        await db_session.commit()

        assert informe.ingeridos == 1
        total = await db_session.scalar(select(func.count()).select_from(HubDocument))
        assert total == 0

    @pytest.mark.asyncio
    async def test_el_dry_run_reporta_lo_que_podaria(self, db_session, tmp_path):
        chatbot_id = uuid.uuid4()
        for n in range(1, 21):
            _escribir(tmp_path, f"REG-5{n:02d}")
        await _reconciliar(db_session, tmp_path, chatbot_id, census=True)
        await db_session.commit()
        (tmp_path / "REG-505.md").unlink()

        informe = await _reconciliar(
            db_session, tmp_path, chatbot_id, census=True, prune=True, dry_run=True
        )
        await db_session.commit()

        assert informe.retirados == 1
        doc = (await _documentos(db_session, chatbot_id))["REG-505"]
        assert doc.us_assistents == "si", "dry-run no escribe"


# ───────────────────────── Versión idiomática ─────────────────────────


class TestVersionIdiomatica:

    @pytest.mark.asyncio
    async def test_resuelve_la_referencia_de_version_idiomatica_a_uuid(
        self, db_session, tmp_path
    ):
        """En el .md la referencia es un id_publicacio; en la BD es un UUID."""
        _escribir(tmp_path, "REG-601")
        _escribir(
            tmp_path,
            "REG-601-es",
            extra="canonica: false\nversio_idiomatica_de: REG-601\n",
        )
        chatbot_id = uuid.uuid4()

        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        docs = await _documentos(db_session, chatbot_id)
        assert docs["REG-601-es"].versio_idiomatica_de == docs["REG-601"].id
        # `canonica` se retiro en ACT.3: lo que la recuperacion necesita es el
        # emparejamiento, no una jerarquia entre dos versiones oficiales.
        assert docs["REG-601"].versio_idiomatica_de is None


# ───────────────────── ACT.1 — el informe dice la verdad ─────────────────────
#
# Una pasada sobre un corpus SIN CAMBIOS reportaba 292 «actualizaciones de metadatos» sobre
# el corpus real. No eran cambios: la columna es `timestamp with time zone` y el front-matter
# trae fechas desnudas, así que `_difiere` comparaba un datetime *aware* contra uno *naive*,
# y en Python eso NUNCA es igual. Con ese ruido, las 24 diferencias reales no se veían.
#
# El segundo defecto es peor porque pierde trabajo humano: el panel de vigencia
# (`hub_ingestion_router.validar_vigencia`) escribe `vigencia_validada_el`, y el reconciliador
# lo pisaba con la fecha del `.md` en cada pasada.


class TestIdempotenciaDeFechas:

    @pytest.mark.asyncio
    async def test_una_segunda_pasada_sin_cambios_no_actualiza_metadatos(
        self, db_session, tmp_path
    ):
        """El invariante del bloque: reconciliar dos veces lo mismo no cambia nada."""
        _escribir(
            tmp_path,
            "REG-701",
            extra=(
                "content_class: regulation\n"
                "revisat_per: Modesto Fabra\n"
                "revisat_el: '2026-08-10'\n"
            ),
        )
        chatbot_id = uuid.uuid4()

        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        informe = await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        assert informe.metadatos_actualizados == 0, informe.detalle
        assert informe.omitidos == 1

    @pytest.mark.asyncio
    async def test_la_fecha_naive_del_md_no_difiere_de_la_aware_guardada(
        self, db_session, tmp_path
    ):
        """`revisat_el: '2026-08-10'` contra lo que la BD devuelve, que lleva zona."""
        from datetime import datetime, timezone

        from server.app.modules.agents_hub.ingestion.corpus.reconciler import _difiere
        from server.app.modules.agents_hub.ingestion.corpus.manifest import (
            CorpusDocumentEntry,
        )

        class _Doc:
            title = "Norma"
            doc_metadata: dict = {}
            ambits_secundaris: list = []
            submateries: list = []
            submateries_internes: list = []

        doc = _Doc()
        entrada = CorpusDocumentEntry(
            relative_path="x.md",
            source_url="https://www.uji.es/x",
            language="ca",
            title="Norma",
            content_class="regulation",
            revisat_per="Modesto Fabra",
            revisat_el=datetime(2026, 8, 10),
        )
        for campo in (
            "content_class", "ambit_principal", "nivell_acces", "us_assistents",
            "estat_vigencia", "revisat_per", "vigencia_validada_el",
            "data_revisio_prevista", "id_publicacio",
        ):
            setattr(doc, campo, getattr(entrada, campo))
        doc.doc_metadata = {"relative_path": "x.md"}
        # Lo que Postgres devuelve para un `timestamptz` escrito desde la fecha desnuda.
        doc.revisat_el = datetime(2026, 8, 10, tzinfo=timezone.utc)

        assert _difiere(doc, entrada, "Norma") is False

    @pytest.mark.asyncio
    async def test_no_pisa_la_validacion_que_escribio_una_persona(
        self, db_session, tmp_path
    ):
        """Sin `vigencia_validada_per` en el .md, manda lo que puso el panel."""
        from datetime import datetime, timezone

        _escribir(tmp_path, "REG-702")
        chatbot_id = uuid.uuid4()
        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        docs = await _documentos(db_session, chatbot_id)
        validado = datetime(2026, 8, 27, 6, 41, 56, tzinfo=timezone.utc)
        docs["REG-702"].vigencia_validada_el = validado
        docs["REG-702"].doc_metadata = {
            **(docs["REG-702"].doc_metadata or {}),
            "vigencia_validada_per": "Una persona, desde el panel",
        }
        await db_session.commit()

        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        docs = await _documentos(db_session, chatbot_id)
        assert docs["REG-702"].vigencia_validada_el == validado
        assert (
            docs["REG-702"].doc_metadata.get("vigencia_validada_per")
            == "Una persona, desde el panel"
        )

    @pytest.mark.asyncio
    async def test_la_validacion_que_viaja_con_el_corpus_si_manda(
        self, db_session, tmp_path
    ):
        """Si el .md la trae, es la de Secretaría General y gana."""
        _escribir(tmp_path, "REG-703")
        chatbot_id = uuid.uuid4()
        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        _escribir(
            tmp_path,
            "REG-703",
            extra=(
                "vigencia_validada_per: Secretaria General\n"
                "vigencia_validada_el: '2026-08-11'\n"
            ),
        )
        await _reconciliar(db_session, tmp_path, chatbot_id)
        await db_session.commit()

        docs = await _documentos(db_session, chatbot_id)
        assert docs["REG-703"].vigencia_validada_el is not None
        assert docs["REG-703"].vigencia_validada_el.date().isoformat() == "2026-08-11"
        assert (
            docs["REG-703"].doc_metadata.get("vigencia_validada_per")
            == "Secretaria General"
        )


# ───────────────────── ACT.5 — copiar en vez de embeber ─────────────────────
#
# El corpus NO se comparte entre chatbots: cada uno tiene sus documentos y sus fragmentos, y es
# una decisión tomada. Pero cuando dos chatbots tienen el MISMO documento —mismo
# `content_hash`— el vector del fragmento es el mismo, y volver a embeberlo cuesta GPU y horas
# para obtener el mismo número.
#
# `chunk_copier.py` (HIB.N) sabía decidirlo y remapearlo desde el 2026-08-27, con tests propios,
# y **tenía cero llamadores**: el reconciliador embebía siempre. Medido sobre la actualización
# del 27-08: los 6 documentos nuevos de Gerencia son un subconjunto estricto de los 19 de
# Normativa, así que se embeberían cuatro veces.


class TestCopiarEnVezDeEmbeber:

    @pytest.mark.asyncio
    async def test_should_copy_the_chunks_from_a_twin_instead_of_embedding(
        self, db_session, tmp_path
    ):
        """El segundo chatbot no llama al servicio de embeddings ni una vez."""
        _escribir(tmp_path, "REG-801", body="El text de la norma que es repetix.")
        origen, destino = await _dos_chatbots_de_la_misma_organizacion(db_session)

        primero = _FakeEmbedding()
        await _reconciliar(db_session, tmp_path, origen, embedding=primero)
        await db_session.commit()

        segundo = _FakeEmbedding()
        informe = await _reconciliar(db_session, tmp_path, destino, embedding=segundo)
        await db_session.commit()

        assert primero.llamadas > 0, "el primero sí que embebe"
        assert segundo.llamadas == 0, (
            f"el gemelo ha llamado {segundo.llamadas} veces al embedding para obtener los "
            "mismos vectores"
        )
        assert informe.copiados == 1
        assert informe.ingeridos == 0
        assert any("copiado de" in d for d in informe.detalle), informe.detalle

    @pytest.mark.asyncio
    async def test_should_leave_the_copy_coherent(self, db_session, tmp_path):
        """La columna `document_id` y su metadato apuntan al documento del DESTINO.

        Es la lección de HIB.U: copiar sin remapear el metadato deja fragmentos que apuntan al
        documento del otro chatbot, la agrupación los junta con los del otro corpus y la cita
        sale con el título equivocado, **sin ningún error**.
        """
        from server.app.modules.agents_hub.ingestion.chunk_copier import incoherentes

        _escribir(tmp_path, "REG-802", body="Text que es copia.")
        origen, destino = await _dos_chatbots_de_la_misma_organizacion(db_session)

        await _reconciliar(db_session, tmp_path, origen)
        await db_session.commit()
        await _reconciliar(db_session, tmp_path, destino)
        await db_session.commit()

        copiados = await _fragmentos(db_session, destino)
        originales = await _fragmentos(db_session, origen)

        assert copiados, "no se ha copiado ningún fragmento"
        assert len(copiados) == len(originales)
        assert incoherentes(copiados) == []
        docs = await _documentos(db_session, destino)
        assert {str(f["document_id"]) for f in copiados} == {str(docs["REG-802"].id)}
        assert all(f["chatbot_id"] == destino for f in copiados)
        # El vector es el mismo: es justamente lo que se ahorra.
        assert [f["embedding"] for f in copiados] == [f["embedding"] for f in originales]

    @pytest.mark.asyncio
    async def test_should_embed_when_there_is_no_twin(self, db_session, tmp_path):
        """Sin gemelo no hay atajo, y el informe no habla de copias."""
        _escribir(tmp_path, "REG-803")
        _, destino = await _dos_chatbots_de_la_misma_organizacion(db_session)

        embedding = _FakeEmbedding()
        informe = await _reconciliar(db_session, tmp_path, destino, embedding=embedding)
        await db_session.commit()

        assert embedding.llamadas > 0
        assert informe.copiados == 0
        assert informe.ingeridos == 1

    @pytest.mark.asyncio
    async def test_should_not_copy_across_organisations(self, db_session, tmp_path):
        """El corpus de una organización no alimenta a otra, ni siquiera para ahorrar."""
        _escribir(tmp_path, "REG-804")
        origen, _ = await _dos_chatbots_de_la_misma_organizacion(db_session)
        ajeno = await _chatbot(db_session)  # otra organización, con su propia fila

        await _reconciliar(db_session, tmp_path, origen)
        await db_session.commit()

        embedding = _FakeEmbedding()
        informe = await _reconciliar(db_session, tmp_path, ajeno, embedding=embedding)
        await db_session.commit()

        assert informe.copiados == 0
        assert embedding.llamadas > 0
