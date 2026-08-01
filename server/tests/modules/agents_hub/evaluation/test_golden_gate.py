"""Gate de regresión del retriever sobre el corpus de fixture (Prompt RAG.1).

Este es el test que **bloquea el build** si una mejora del retriever empeora la
recuperación. Corre sobre BD desechable con 25 normas breves del corpus de fixture y un
**embedding determinista**, de modo que el resultado es reproducible entre máquinas.

Qué mide y qué no, porque confundirlo llevaría a conclusiones falsas:

- Mide el **mecanismo**: fusión híbrida, filtros, ranking, umbral. Es lo que cambian
  RAG.3–RAG.8, y por eso vive en CI.
- **No mide BGE-M3.** Con embedding determinista, la señal semántica es la que da el
  solapamiento de vocabulario. Medir el modelo real exige el corpus real y va por el CLI.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path

import pytest

CORPUS = Path(__file__).parent.parent.parent.parent / "fixtures" / "golden_corpus"
BASELINES = Path(__file__).parent / "baselines"
DATASET = Path(__file__).parent / "golden_dietes.json"

_PALABRA = re.compile(r"\w{3,}", re.UNICODE)


class DeterministicEmbedding:
    """Bolsa de palabras proyectada por hash a 1024 dimensiones, L2-normalizada.

    Determinista y sin modelo: dos textos con vocabulario compartido quedan cerca. Es
    suficiente para medir el mecanismo de recuperación y no depende de pesos descargados.
    """

    DIM = 1024
    # RAG.9: procedencia obligatoria. El dorado ingiere por el watcher, que la exige.
    model_name = "test/deterministic-bow"
    dimensions = DIM

    async def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.DIM
        for palabra in _PALABRA.findall(text.lower()):
            indice = int(hashlib.md5(palabra.encode()).hexdigest(), 16) % self.DIM
            vector[indice] += 1.0
        norma = sum(v * v for v in vector) ** 0.5
        return [v / norma for v in vector] if norma else vector


@pytest.fixture
async def corpus_ingerido(db_session):
    """Ingiere las 25 normas del fixture y devuelve (chatbot_id, hashes)."""
    from server.app.modules.agents_hub.ingestion.corpus.frontmatter import parse_frontmatter
    from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

    class _Provider:
        async def get_retrieval_mode(self, chatbot_id):
            return "RAG"

    chatbot_id = uuid.uuid4()
    watcher = IngestionWatcher(
        db_session, DeterministicEmbedding(), chatbot_provider=_Provider()
    )
    hashes = []
    for path in sorted(CORPUS.glob("*.md")):
        meta, cuerpo = parse_frontmatter(path.read_text(encoding="utf-8"))
        doc, _ = await watcher.process_source(
            source_url=meta["url_oficial"],
            chatbot_id=chatbot_id,
            language=meta["language"],
            citation_url=meta["url_oficial"],
            prefetched_content=cuerpo,
            title=meta["title"],
        )
        hashes.append(doc.content_hash)
    await db_session.commit()
    return chatbot_id, hashes


class TestCorpusDeFixture:

    def test_el_corpus_tiene_documentos_suficientes_para_discriminar(self):
        """Con pocos documentos, recall@5 se acierta por azar y no mide nada."""
        documentos = list(CORPUS.glob("*.md"))
        assert len(documentos) >= 20, f"solo {len(documentos)} documentos"

    @pytest.mark.asyncio
    async def test_el_corpus_se_ingiere_y_produce_fragmentos(self, corpus_ingerido, db_session):
        from sqlalchemy import func, select

        from server.app.modules.agents_hub.database.operational_models import (
            HubDocumentChunk,
        )

        chatbot_id, hashes = corpus_ingerido
        assert len(hashes) == 25

        total = await db_session.scalar(
            select(func.count()).select_from(HubDocumentChunk).where(
                HubDocumentChunk.chatbot_id == chatbot_id
            )
        )
        assert total >= 25, f"solo {total} fragmentos"


class TestGateDeRegresion:

    @pytest.mark.asyncio
    async def test_should_run_eval_over_fixture_corpus_and_produce_report(
        self, corpus_ingerido, db_session
    ):
        from server.app.modules.agents_hub.evaluation.golden_dataset import (
            fingerprint_matches,
            load_golden_dataset,
        )
        from server.app.modules.agents_hub.evaluation.retrieval_eval import run_golden_eval
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        chatbot_id, hashes = corpus_ingerido
        dataset = load_golden_dataset(DATASET)

        assert fingerprint_matches(dataset, hashes), (
            "el dataset dorado se midió sobre otro corpus: las cifras no comparan nada. "
            "Regenera la huella con --update-baseline si el cambio del fixture es querido."
        )

        informe = await run_golden_eval(
            HybridRetriever(db_session), DeterministicEmbedding(), dataset, chatbot_id
        )

        assert len(informe.per_query) == len(dataset.queries)
        assert 0.0 <= informe.recall_at_5 <= 1.0
        print(f"\n  {informe.render()}")

    @pytest.mark.asyncio
    async def test_should_pass_gate_when_metrics_meet_baseline(
        self, corpus_ingerido, db_session
    ):
        """EL GATE. Si esto falla, una mejora del retriever ha empeorado la recuperación."""
        from server.app.modules.agents_hub.evaluation.golden_dataset import (
            load_golden_dataset,
        )
        from server.app.modules.agents_hub.evaluation.retrieval_eval import (
            check_gate,
            run_golden_eval,
        )
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        chatbot_id, _ = corpus_ingerido
        dataset = load_golden_dataset(DATASET)
        informe = await run_golden_eval(
            HybridRetriever(db_session), DeterministicEmbedding(), dataset, chatbot_id
        )

        ruta = BASELINES / f"{dataset.name}.json"
        baseline = json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else None
        veredicto = check_gate(informe, baseline)

        assert veredicto.passed, (
            f"regresión de recuperación: {veredicto.summary}\n"
            + "\n".join(f"  - {r}" for r in veredicto.regressions)
            + f"\n  actual:   {informe.render()}"
            + f"\n  baseline: {baseline}"
        )


class TestUmbralContraElDorado:
    """RAG.5: el umbral **vigente por defecto** no puede recortar aciertos del dorado.

    El criterio de done de RAG.5 lo pedía, y la medición cambió el default: con 0,25 el
    dorado caía de recall@5 0,960 a 0,720. Ese 0,72 no prueba que 0,25 sea mal umbral en
    producción —el corpus de fixture usa un embedding determinista cuyas similitudes coseno
    son estructuralmente bajas, y BGE-M3 tiene otra distribución—, pero tampoco se deja
    activo un filtro que recorta un 24 % de recall en lo único medible. El umbral quedó
    implementado y desactivado (0,0) hasta poder medirlo con el corpus real.

    Este test lee el default de la **cascada**, no un número escrito aquí: si alguien lo
    sube sin datos que lo respalden, falla.
    """

    @pytest.mark.asyncio
    async def test_should_not_lose_golden_hits_with_the_default_threshold(
        self, corpus_ingerido, db_session
    ):
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            _PLATFORM_DEFAULTS,
        )
        from server.app.modules.agents_hub.evaluation.golden_dataset import (
            load_golden_dataset,
        )
        from server.app.modules.agents_hub.evaluation.retrieval_eval import run_golden_eval
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        chatbot_id, _ = corpus_ingerido
        dataset = load_golden_dataset(DATASET)

        class _ConUmbral:
            """Inyecta el umbral por defecto en cada consulta del dorado."""

            def __init__(self, retriever, min_score: float) -> None:
                self._retriever = retriever
                self._min_score = min_score

            async def hybrid_search(self, **kw):
                return await self._retriever.hybrid_search(**kw, min_score=self._min_score)

        sin_umbral = await run_golden_eval(
            HybridRetriever(db_session), DeterministicEmbedding(), dataset, chatbot_id
        )
        umbral = _PLATFORM_DEFAULTS.min_retrieval_score
        con_umbral = await run_golden_eval(
            _ConUmbral(HybridRetriever(db_session), umbral),
            DeterministicEmbedding(),
            dataset,
            chatbot_id,
        )

        print(
            f"\n  sin umbral: recall@5={sin_umbral.recall_at_5:.3f} mrr={sin_umbral.mrr:.3f}"
            f"\n  umbral {umbral}: recall@5={con_umbral.recall_at_5:.3f} "
            f"mrr={con_umbral.mrr:.3f}"
        )

        assert con_umbral.recall_at_5 >= sin_umbral.recall_at_5 - 0.02, (
            "el umbral por defecto recorta aciertos del dorado: ajustarlo con datos "
            "y documentar el porqué (criterio de done de RAG.5)"
        )


class TestReescrituraContraElDorado:
    """RAG.10: el criterio de done, medido sobre el subconjunto conversacional.

    **Qué se mide y qué no.** El reescritor de aquí es determinista —concatena el último
    turno del usuario con el seguimiento—, no un LLM. Es la misma postura que RAG.1 con el
    embedding y RAG.6a con el reranker: lo que se verifica es que **resolver la anáfora
    ayuda a recuperar**, no la calidad de un modelo concreto reescribiendo. Un LLM haría
    una consulta más limpia que la concatenación, así que esta cifra es un suelo, no un
    techo.

    El subconjunto vive en su propio fichero y no dentro de `golden_dietes.json`: mezclarlo
    movería la media contra la que se compararon RAG.3–RAG.9 y dejaría la línea base del
    gate midiendo otra cosa.
    """

    @pytest.mark.asyncio
    async def test_rewriting_should_improve_the_conversational_subset(
        self, corpus_ingerido, db_session
    ):
        from server.app.modules.agents_hub.evaluation.golden_dataset import (
            load_golden_dataset,
        )
        from server.app.modules.agents_hub.evaluation.retrieval_eval import run_golden_eval
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        chatbot_id, _ = corpus_ingerido
        dataset = load_golden_dataset(Path(__file__).parent / "golden_conversacional.json")

        async def _concatenar(query: str, history: list[str]) -> str:
            ultimo_usuario = next(
                (m.split(":", 1)[1].strip() for m in reversed(history)
                 if m.startswith("usuario:")),
                "",
            )
            return f"{ultimo_usuario} {query}".strip()

        apagado = await run_golden_eval(
            HybridRetriever(db_session), DeterministicEmbedding(), dataset, chatbot_id
        )
        encendido = await run_golden_eval(
            HybridRetriever(db_session), DeterministicEmbedding(), dataset, chatbot_id,
            rewriter=_concatenar,
        )

        print(
            f"\n  conversacional OFF: recall@5={apagado.recall_at_5:.3f} "
            f"recall@10={apagado.recall_at_10:.3f} mrr={apagado.mrr:.3f}"
            f"\n  conversacional ON:  recall@5={encendido.recall_at_5:.3f} "
            f"recall@10={encendido.recall_at_10:.3f} mrr={encendido.mrr:.3f}"
        )

        assert encendido.recall_at_5 > apagado.recall_at_5, (
            "resolver la anafora no mejora la recuperacion en el subconjunto "
            "conversacional: o el subconjunto no es anaforico de verdad, o la reescritura "
            "no aporta nada en este corpus. Las dos cosas hay que mirarlas antes de "
            "encender el flag."
        )
