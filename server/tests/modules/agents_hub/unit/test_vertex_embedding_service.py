"""PIL.1 — adaptador de Vertex AI, lote por API y propósito del embedding.

Los números que fija este fichero están **medidos contra la API real** el 2026-08-15 con el
proyecto `uji-teclab`, no leídos de la documentación:

- `gemini-embedding-001` sirve a 1024 dimensiones en `europe-southwest1`.
- Acepta **250 instancias por petición** (probado 1, 2, 16, 64 y 250).
- **NO normaliza** a 1024 dimensiones: la norma L2 medida fue 0,6225.
- Acepta `RETRIEVAL_DOCUMENT` y `RETRIEVAL_QUERY`.

El último punto es el que más cuida este fichero: embeber el corpus con un tipo de tarea y
preguntar con otro no da error, da resultados peores. Por eso el propósito viaja con la
procedencia del vector y la guarda de espacio vectorial lo compara.
"""
from __future__ import annotations

import inspect
import math
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _norma(vector: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vector))


class _ClienteFalso:
    """Doble del cliente de langchain: registra por dónde entró cada texto.

    Devuelve vectores SIN normalizar a propósito — es lo que hace la API de verdad, y un
    doble que devolviera vectores unitarios dejaría pasar la ausencia de normalización.
    """

    def __init__(self, dimensiones: int = 1024) -> None:
        self.lotes_de_documento: list[list[str]] = []
        self.consultas: list[str] = []
        self._dim = dimensiones

    @staticmethod
    def _vector_de(texto: str, dim: int) -> list[float]:
        # El primer componente identifica al texto, para poder comprobar el orden.
        semilla = float(len(texto)) + sum(ord(c) for c in texto) / 1000.0
        return [semilla] + [0.5] * (dim - 1)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        self.lotes_de_documento.append(list(texts))
        return [self._vector_de(t, self._dim) for t in texts]

    async def aembed_query(self, text: str) -> list[float]:
        self.consultas.append(text)
        return self._vector_de(text, self._dim)


def _vertex(**kwargs):
    from server.app.modules.agents_hub.services.embedding_service import (
        VertexEmbeddingService,
    )

    kwargs.setdefault("client", _ClienteFalso())
    return VertexEmbeddingService(**kwargs)


class TestAdaptadorDeVertex:

    def test_should_default_to_platform_dimension_1024(self):
        from server.app.modules.agents_hub.services.embedding_service import (
            DIMENSION_PLATAFORMA,
        )

        assert _vertex().dimensions == DIMENSION_PLATAFORMA == 1024

    def test_should_declare_the_measured_model(self):
        assert _vertex().model_name == "gemini-embedding-001"

    @pytest.mark.asyncio
    async def test_should_normalize_l2_the_returned_vector(self):
        """Medido: la API devuelve norma 0,6225 a 1024 dimensiones. Si no se normaliza
        aquí, el umbral de RAG.5 compara números incomparables y NO da error."""
        servicio = _vertex()

        vector = await servicio.embed("despeses de viatge")

        assert _norma(vector) == pytest.approx(1.0, abs=1e-9)

    @pytest.mark.asyncio
    async def test_should_normalize_every_vector_of_a_batch(self):
        servicio = _vertex()

        vectores = await servicio.embed_batch(["un", "dos", "tres"])

        assert [_norma(v) for v in vectores] == pytest.approx([1.0, 1.0, 1.0], abs=1e-9)

    def test_should_fail_with_actionable_error_when_project_missing(self, monkeypatch):
        """Sin proyecto no se puede llamar a Vertex, y el error tiene que decir qué falta.

        Se comprueba ANTES de importar el cliente: si no, quien no tenga la dependencia
        instalada recibe un ImportError que no habla del problema real.
        """
        from server.app.modules.agents_hub.services.embedding_service import (
            VertexEmbeddingService,
        )

        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

        with pytest.raises(RuntimeError) as exc:
            VertexEmbeddingService()

        assert "GOOGLE_CLOUD_PROJECT" in str(exc.value)


class TestLotePorAPI:
    """Sin lote, los ~21.400 fragmentos del piloto son 21.400 idas y vueltas de red."""

    @pytest.mark.asyncio
    async def test_should_split_a_large_batch_into_api_sized_requests(self):
        from server.app.modules.agents_hub.services.embedding_service import (
            LOTE_MAXIMO_API,
        )

        assert LOTE_MAXIMO_API == 250, "el tope medido contra la API real"
        cliente = _ClienteFalso()
        servicio = _vertex(client=cliente)

        await servicio.embed_batch([f"t{i}" for i in range(600)])

        assert [len(lote) for lote in cliente.lotes_de_documento] == [250, 250, 100]

    @pytest.mark.asyncio
    async def test_should_preserve_input_order_across_batch_boundaries(self):
        """Un lote reordenado asigna el vector al fragmento equivocado y NO da error."""
        cliente = _ClienteFalso()
        servicio = _vertex(client=cliente)
        textos = [f"texto-{i}" for i in range(600)]

        vectores = await servicio.embed_batch(textos)

        esperados = [
            _ClienteFalso._vector_de(t, 1024)[0] / _norma(_ClienteFalso._vector_de(t, 1024))
            for t in textos
        ]
        assert [v[0] for v in vectores] == pytest.approx(esperados)

    @pytest.mark.asyncio
    async def test_should_not_call_the_api_for_an_empty_batch(self):
        cliente = _ClienteFalso()
        servicio = _vertex(client=cliente)

        assert await servicio.embed_batch([]) == []
        assert cliente.lotes_de_documento == []

    def test_should_expose_embed_batch_on_both_api_adapters(self):
        from server.app.modules.agents_hub.services.embedding_service import (
            GoogleEmbeddingService,
            VertexEmbeddingService,
        )

        for clase in (GoogleEmbeddingService, VertexEmbeddingService):
            assert hasattr(clase, "embed_batch"), f"{clase.__name__} sin lote"


class TestPropositoDelEmbedding:
    """RETRIEVAL_DOCUMENT al indexar, RETRIEVAL_QUERY al preguntar (decisión 2026-08-15)."""

    @pytest.mark.asyncio
    async def test_should_send_retrieval_document_task_type_when_ingesting(self):
        from server.app.modules.agents_hub.services.embedding_service import (
            PURPOSE_DOCUMENT,
        )

        cliente = _ClienteFalso()
        servicio = _vertex(client=cliente)

        await servicio.embed("un article", purpose=PURPOSE_DOCUMENT)

        assert cliente.lotes_de_documento == [["un article"]]
        assert cliente.consultas == []

    @pytest.mark.asyncio
    async def test_should_send_retrieval_query_task_type_when_querying(self):
        cliente = _ClienteFalso()
        servicio = _vertex(client=cliente)

        await servicio.embed("com justifique una dieta?")

        assert cliente.consultas == ["com justifique una dieta?"]
        assert cliente.lotes_de_documento == []

    @pytest.mark.asyncio
    async def test_should_treat_a_batch_as_documents_by_default(self):
        cliente = _ClienteFalso()
        servicio = _vertex(client=cliente)

        await servicio.embed_batch(["a", "b"])

        assert cliente.lotes_de_documento == [["a", "b"]]
        assert cliente.consultas == []

    def test_should_declare_the_task_type_used_when_indexing(self):
        from server.app.modules.agents_hub.services.embedding_service import (
            PURPOSE_DOCUMENT,
            GoogleEmbeddingService,
            VertexEmbeddingService,
        )

        assert _vertex().embedding_task_type == PURPOSE_DOCUMENT
        assert VertexEmbeddingService.embedding_task_type is not None
        assert GoogleEmbeddingService.embedding_task_type is not None

    def test_should_accept_and_ignore_the_purpose_in_the_local_adapter(self):
        """BGE-M3 no tiene tipos de tarea y no se le va a inventar uno.

        Se comprueba por la firma y no llamando: cargar el modelo local exige el extra
        `[local-models]`, que el despliegue estándar no instala.
        """
        from server.app.modules.agents_hub.services.embedding_service import (
            LocalEmbeddingService,
        )

        for metodo in (LocalEmbeddingService.embed, LocalEmbeddingService.embed_batch):
            assert "purpose" in inspect.signature(metodo).parameters, metodo.__name__
        assert LocalEmbeddingService().embedding_task_type is None


class TestProcedenciaDelVector:
    """El propósito viaja con el vector, o cambiarlo corrompe el índice en silencio."""

    @pytest.mark.asyncio
    async def test_should_record_the_task_type_in_the_vector_provenance(self):
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
        from server.app.modules.agents_hub.services.embedding_service import (
            PURPOSE_DOCUMENT,
        )

        session = AsyncMock()
        anadidos: list = []
        session.add = MagicMock(side_effect=anadidos.append)
        embedding = AsyncMock()
        embedding.embed_batch = AsyncMock(
            side_effect=lambda ts, **kw: [[0.1] * 1024] * len(ts)
        )
        embedding.model_name = "gemini-embedding-001"
        embedding.dimensions = 1024
        embedding.embedding_task_type = PURPOSE_DOCUMENT

        watcher = IngestionWatcher(
            session=session, embedding_service=embedding, chatbot_provider=AsyncMock()
        )
        doc = HubDocument(
            id=uuid.uuid4(), chatbot_id=uuid.uuid4(), title="Norma",
            canonical_url="https://uji.es/n",
            markdown_content="# Norma\n\n## Article 1 {#art-1}\nText de l'article.\n",
            content_hash="h" * 64, language="ca", source_kind="publicacio",
        )

        await watcher._regenerate_chunks_for_document(doc)

        assert anadidos, "no se persistio ningun fragmento"
        assert all(c.embedding_task_type == PURPOSE_DOCUMENT for c in anadidos)

    @pytest.mark.asyncio
    async def test_should_reject_a_corpus_embedded_with_a_different_task_type(self):
        """Modelo y dimensión coincidirían: sin el tipo de tarea, esto pasaría inadvertido."""
        from server.app.modules.agents_hub.services.embedding_service import (
            PURPOSE_DOCUMENT,
            PURPOSE_QUERY,
        )
        from server.app.modules.agents_hub.services.embedding_space import (
            EmbeddingSpaceMismatch,
            assert_embedding_space_matches,
        )

        session = AsyncMock()
        session.execute = AsyncMock(
            return_value=MagicMock(
                all=MagicMock(
                    return_value=[("gemini-embedding-001", 1024, PURPOSE_QUERY)]
                )
            )
        )
        activo = MagicMock()
        activo.model_name = "gemini-embedding-001"
        activo.dimensions = 1024
        activo.embedding_task_type = PURPOSE_DOCUMENT

        with pytest.raises(EmbeddingSpaceMismatch) as exc:
            await assert_embedding_space_matches(session, uuid.uuid4(), activo)

        assert PURPOSE_QUERY in str(exc.value)

    @pytest.mark.asyncio
    async def test_should_accept_a_corpus_with_the_same_task_type(self):
        from server.app.modules.agents_hub.services.embedding_service import (
            PURPOSE_DOCUMENT,
        )
        from server.app.modules.agents_hub.services.embedding_space import (
            assert_embedding_space_matches,
        )

        session = AsyncMock()
        session.execute = AsyncMock(
            return_value=MagicMock(
                all=MagicMock(
                    return_value=[("gemini-embedding-001", 1024, PURPOSE_DOCUMENT)]
                )
            )
        )
        activo = MagicMock()
        activo.model_name = "gemini-embedding-001"
        activo.dimensions = 1024
        activo.embedding_task_type = PURPOSE_DOCUMENT

        await assert_embedding_space_matches(session, uuid.uuid4(), activo)


class TestSeleccionPorConfiguracion:

    @pytest.mark.asyncio
    async def test_should_return_vertex_adapter_for_google_vertexai_provider_type(self):
        from server.app.modules.agents_hub.services.embedding_resolver import (
            resolve_embedding_service,
        )
        from server.app.modules.agents_hub.services.embedding_service import (
            VertexEmbeddingService,
        )

        config = MagicMock()
        config.provider = "vertex"
        config.model_name = "gemini-embedding-001"
        config.output_dimensionality = 1024
        proveedor = MagicMock()
        proveedor.provider_type = "google_vertexai"

        session = AsyncMock()
        session.get = AsyncMock(return_value=proveedor)
        session.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=config))
                )
            )
        )

        servicio = await resolve_embedding_service(
            session, None, client_factory=lambda: _ClienteFalso()
        )

        assert isinstance(servicio, VertexEmbeddingService)

    @pytest.mark.asyncio
    async def test_should_name_all_supported_types_in_the_unsupported_error(self):
        from server.app.modules.agents_hub.services.embedding_resolver import (
            EmbeddingProviderNotSupported,
            resolve_embedding_service,
        )

        config = MagicMock()
        config.provider = "cohere"
        proveedor = MagicMock()
        proveedor.provider_type = "cohere"

        session = AsyncMock()
        session.get = AsyncMock(return_value=proveedor)
        session.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(
                    return_value=MagicMock(first=MagicMock(return_value=config))
                )
            )
        )

        with pytest.raises(EmbeddingProviderNotSupported) as exc:
            await resolve_embedding_service(session, None)

        for tipo in ("google_vertexai", "google_genai", "local"):
            assert tipo in str(exc.value)
