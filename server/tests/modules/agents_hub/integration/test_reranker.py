"""Tests RAG.6a — el mecanismo del reranker, sin depender de ningún servicio externo.

RAG.6 se partió en dos el 2026-08-01. Aquí va todo lo que se puede verificar sin llamar a
nadie: el protocolo, la resolución por configuración, el pool ampliado, la sustitución del
score y el fallo explícito. El adaptador real de Vertex y la medición de si el valenciano
está entre sus 25 idiomas son RAG.6b, y van después del despliegue.

Se prueba con un **reranker determinista** —solapamiento de palabras entre consulta y
candidato— por la misma razón que RAG.1 mide el mecanismo de recuperación con un embedding
determinista: lo que se verifica aquí es la mecánica (cuántos candidatos se piden, qué score
manda, qué pasa con el flag apagado), no la calidad de un modelo.
"""
from __future__ import annotations

import re
import uuid

import pytest

from server.tests.modules.agents_hub.integration.test_metadata_filter import (
    _chunk,
    _documento,
    _emb,
)

_PALABRA = re.compile(r"\w{3,}", re.UNICODE)


class RerankerDeterminista:
    """Ordena por solapamiento de palabras. Reproducible y sin modelo."""

    def __init__(self) -> None:
        self.llamadas: list[tuple[str, int]] = []

    async def rerank(self, query: str, candidates: list[str], top_k: int):
        from server.app.modules.agents_hub.services.reranker import RerankResult

        self.llamadas.append((query, len(candidates)))
        palabras = set(_PALABRA.findall(query.lower()))
        puntuados = [
            (
                indice,
                len(palabras & set(_PALABRA.findall(texto.lower()))) / (len(palabras) or 1),
            )
            for indice, texto in enumerate(candidates)
        ]
        puntuados.sort(key=lambda p: p[1], reverse=True)
        return [RerankResult(index=i, score=s) for i, s in puntuados[:top_k]]


class _Emb:
    async def embed(self, text: str):
        return _emb(0)


class TestContrato:

    @pytest.mark.asyncio
    async def test_should_rerank_candidates_with_relevant_first(self):
        reranker = RerankerDeterminista()

        resultados = await reranker.rerank(
            "import de la dieta",
            ["Norma sobre horarios del personal", "L'import de la dieta es de 53 euros"],
            top_k=2,
        )

        assert resultados[0].index == 1
        assert resultados[0].score > resultados[1].score

    @pytest.mark.asyncio
    async def test_should_normalize_scores_to_unit_interval(self):
        """Los umbrales del packer y del quality gate operan sobre [0,1]: si el reranker
        devuelve logits crudos, sustituir el score de fusión rompe esos dos controles."""
        from server.app.modules.agents_hub.services.reranker import normalize_score

        assert normalize_score(0.0) == pytest.approx(0.5, abs=1e-6)
        assert 0.0 < normalize_score(-8.0) < 0.01
        assert 0.99 < normalize_score(8.0) < 1.0
        assert all(0.0 <= normalize_score(v) <= 1.0 for v in (-100.0, -1.0, 1.0, 100.0))


class TestResolucionPorConfiguracion:

    @pytest.mark.asyncio
    async def test_should_fail_loudly_for_an_unsupported_provider(self, db_session):
        """Sin fallback silencioso: degradar al híbrido sin avisar dejaría al admin creyendo
        que el reranker está actuando cuando no lo está."""
        from server.app.modules.agents_hub.database.config_models import (
            HubLLMConfig,
            HubProvider,
        )
        from server.app.modules.agents_hub.services.reranker import (
            RerankerProviderNotSupported,
            resolve_reranker,
        )

        await db_session.merge(
            HubProvider(id="exotico", name="Exotico", provider_type="protocolo_raro")
        )
        db_session.add(
            HubLLMConfig(
                provider="exotico", model_name="m", purpose="rerank", is_default=True
            )
        )
        await db_session.commit()

        with pytest.raises(RerankerProviderNotSupported) as error:
            await resolve_reranker(db_session)

        assert "protocolo_raro" in str(error.value)

    @pytest.mark.asyncio
    async def test_should_fail_loudly_when_enabled_without_configuration(self, db_session):
        """Activar el flag sin configurar proveedor es un error de configuración, no un
        motivo para seguir en silencio con el híbrido."""
        from server.app.modules.agents_hub.services.reranker import (
            RerankerNotConfigured,
            resolve_reranker,
        )

        with pytest.raises(RerankerNotConfigured):
            await resolve_reranker(db_session)

    @pytest.mark.asyncio
    async def test_should_ignore_configs_of_another_purpose(self, db_session):
        from server.app.modules.agents_hub.database.config_models import (
            HubLLMConfig,
            HubProvider,
        )
        from server.app.modules.agents_hub.services.reranker import (
            RerankerNotConfigured,
            resolve_reranker,
        )

        await db_session.merge(
            HubProvider(id="google", name="Google", provider_type="google_genai")
        )
        db_session.add(
            HubLLMConfig(
                provider="google", model_name="gemini-flash", purpose="chat", is_default=True
            )
        )
        await db_session.commit()

        with pytest.raises(RerankerNotConfigured):
            await resolve_reranker(db_session)


class TestIntegracionConLaEstrategia:

    async def _corpus(self, db_session, cb):
        doc = await _documento(db_session, cb, language="es")
        textos = [
            "L'import de la dieta es de 53 euros per dia",
            "Norma sobre horarios del personal de administracion",
            "Procedimiento de solicitud de vacaciones anuales",
            "Regimen disciplinario del personal docente",
            "Criterios de valoracion de meritos en concursos",
        ]
        for texto in textos:
            await _chunk(db_session, cb, doc, texto, embedding=_emb(0), language="es")
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_should_retrieve_wider_pool_when_reranking(self, db_session):
        """El reranker solo puede mejorar lo que le llega: con `top_k` candidatos no tiene
        nada que reordenar. Pool = max(30, top_k*3)."""
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        cb = uuid.uuid4()
        await self._corpus(db_session, cb)
        reranker = RerankerDeterminista()

        await VectorRetrievalStrategy(
            db_session, _Emb(), top_k=2, reranker=reranker
        ).get_context(query="import dieta", chatbot_id=cb)

        assert reranker.llamadas, "no se llamo al reranker"
        _, candidatos = reranker.llamadas[0]
        assert candidatos == 5, f"se le pasaron {candidatos} candidatos, no todo el pool"

    @pytest.mark.asyncio
    async def test_should_not_call_reranker_when_flag_disabled(self, db_session):
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        cb = uuid.uuid4()
        await self._corpus(db_session, cb)
        reranker = RerankerDeterminista()

        # Sin reranker inyectado: es lo que hace el pipeline cuando el flag esta apagado
        await VectorRetrievalStrategy(db_session, _Emb(), top_k=2).get_context(
            query="import dieta", chatbot_id=cb
        )

        assert reranker.llamadas == []

    @pytest.mark.asyncio
    async def test_should_replace_fusion_score_with_rerank_score(self, db_session):
        """El score que sale es el del reranker, no el de la fusión RRF: son dos mecanismos
        distintos aunque en este corpus los dos elijan el mismo documento (buen solapamiento
        léxico + empate vectorial) y por eso terminen en una magnitud parecida.

        Antes de normalizar en `vector_strategy.py`, sin reranker el score llegaba en escala
        RRF pura (techo ~0,016, ver `RRF_MAX_SCORE`), incomparable con el [0,1] del
        reranker — que es justo lo que este test existe para impedir que se cuele.
        """
        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        cb = uuid.uuid4()
        await self._corpus(db_session, cb)

        sin_rerank = await VectorRetrievalStrategy(
            db_session, _Emb(), top_k=2
        ).get_context(query="import dieta", chatbot_id=cb)
        con_rerank = await VectorRetrievalStrategy(
            db_session, _Emb(), top_k=2, reranker=RerankerDeterminista()
        ).get_context(query="import dieta", chatbot_id=cb)

        # 1,0 = la similitud coseno del mejor fragmento: los 5 chunks comparten embedding y
        # empatan a coseno 1.0 contra la consulta.
        #
        # Aqui habia un 0,7, y ese numero era el sintoma que HIB.J vino a quitar: sin reranker
        # la nota era la fusion RRF normalizada por su techo teorico, y eso resultaba ser una
        # CONSTANTE igual a `vector_weight` —medido, 0,7 en las 25 consultas del lote—, porque
        # el techo exige que el mismo fragmento salga por las dos ramas y con troceado fino no
        # ocurre. Desde HIB.J la nota es la relevancia coseno, que es lo que `Source.score` dice
        # ser. Lo que este test vigila no cambia: la escala es [0,1] y no la RRF (~0,016).
        assert max(s.score for s in sin_rerank.sources) == pytest.approx(1.0)
        assert max(s.score for s in con_rerank.sources) > 0.4
        assert "dieta" in con_rerank.sources[0].excerpt

    @pytest.mark.asyncio
    async def test_should_log_rerank_latency(self, db_session, caplog):
        """Sin la duración registrada no se puede decidir si el reranker sale a cuenta."""
        import logging

        from server.app.modules.agents_hub.services.retrieval.vector_strategy import (
            VectorRetrievalStrategy,
        )

        cb = uuid.uuid4()
        await self._corpus(db_session, cb)

        with caplog.at_level(logging.INFO):
            await VectorRetrievalStrategy(
                db_session, _Emb(), top_k=2, reranker=RerankerDeterminista()
            ).get_context(query="import dieta", chatbot_id=cb)

        assert any("rerank" in r.message.lower() for r in caplog.records), caplog.text
