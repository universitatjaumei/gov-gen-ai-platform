"""Tests TDD — Métricas de recuperación y dataset dorado (Prompt RAG.1).

**Medir antes de mejorar**: ninguna mejora del retriever (RAG.3–RAG.8, RAG.10) se cierra sin
comparar contra la línea base que establece este prompt.

Las métricas son **puras y sin LLM**: funciones sobre listas de identificadores. Es lo que
permite que el gate corra en segundos y que RAGAS quede para evaluación periódica.
"""
from __future__ import annotations

import json

import pytest


# ───────────────────────── recall@k y MRR ─────────────────────────


class TestRecallAtK:

    def test_should_compute_recall_at_k_for_hit_and_miss(self):
        from server.app.modules.agents_hub.evaluation.retrieval_metrics import recall_at_k

        assert recall_at_k(["a", "b", "c"], ["b"], k=3) == 1.0
        assert recall_at_k(["a", "b", "c"], ["z"], k=3) == 0.0

    def test_solo_cuenta_los_primeros_k(self):
        from server.app.modules.agents_hub.evaluation.retrieval_metrics import recall_at_k

        assert recall_at_k(["a", "b", "c"], ["c"], k=2) == 0.0
        assert recall_at_k(["a", "b", "c"], ["c"], k=3) == 1.0

    def test_es_la_fraccion_de_esperados_encontrados(self):
        from server.app.modules.agents_hub.evaluation.retrieval_metrics import recall_at_k

        assert recall_at_k(["a", "b"], ["a", "z"], k=5) == 0.5
        assert recall_at_k(["a", "b"], ["a", "b"], k=5) == 1.0

    def test_sin_esperados_no_es_puntuable(self):
        """Un caso sin objetivo no puede puntuar 1: falsearía la media."""
        from server.app.modules.agents_hub.evaluation.retrieval_metrics import recall_at_k

        assert recall_at_k(["a"], [], k=5) == 0.0

    def test_sin_recuperados_es_cero(self):
        from server.app.modules.agents_hub.evaluation.retrieval_metrics import recall_at_k

        assert recall_at_k([], ["a"], k=5) == 0.0

    def test_ignora_duplicados_en_lo_recuperado(self):
        from server.app.modules.agents_hub.evaluation.retrieval_metrics import recall_at_k

        assert recall_at_k(["a", "a", "a"], ["a", "b"], k=3) == 0.5


class TestMRR:

    def test_should_compute_mrr_with_first_relevant_position(self):
        from server.app.modules.agents_hub.evaluation.retrieval_metrics import mrr

        assert mrr(["a", "b", "c"], ["a"]) == 1.0
        assert mrr(["a", "b", "c"], ["b"]) == pytest.approx(0.5)
        assert mrr(["a", "b", "c"], ["c"]) == pytest.approx(1 / 3)

    def test_cuenta_la_primera_coincidencia_no_la_mejor(self):
        from server.app.modules.agents_hub.evaluation.retrieval_metrics import mrr

        assert mrr(["z", "a", "b"], ["a", "b"]) == pytest.approx(0.5)

    def test_sin_coincidencia_es_cero(self):
        from server.app.modules.agents_hub.evaluation.retrieval_metrics import mrr

        assert mrr(["a", "b"], ["z"]) == 0.0
        assert mrr([], ["a"]) == 0.0


# ───────────────────────── Dataset dorado ─────────────────────────


def _consulta(**kwargs):
    from server.app.modules.agents_hub.evaluation.golden_dataset import GoldenQuery

    defaults = dict(
        query="quant cobro de dieta per anar a Madrid?",
        language="ca",
        expected_canonical_urls=("https://www.uji.es/REG-020",),
    )
    defaults.update(kwargs)
    return GoldenQuery(**defaults)


class TestGoldenDataset:

    def test_should_load_and_validate_golden_dataset_schema(self, tmp_path):
        from server.app.modules.agents_hub.evaluation.golden_dataset import (
            GoldenDataset,
            load_golden_dataset,
        )

        dataset = GoldenDataset(
            name="dietes",
            documents_fingerprint="abc123",
            queries=(_consulta(), _consulta(query="qui signa un contracte menor?")),
        )
        destino = tmp_path / "dietes.json"
        destino.write_text(dataset.model_dump_json(), encoding="utf-8")

        recargado = load_golden_dataset(destino)

        assert recargado == dataset
        assert len(recargado.queries) == 2

    def test_should_reject_query_without_expected_targets(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc:
            _consulta(expected_canonical_urls=())
        assert "expected" in str(exc.value)

    def test_acepta_objetivo_por_document_id(self):
        entrada = _consulta(
            expected_canonical_urls=(), expected_document_ids=("REG-020",)
        )
        assert entrada.expected_document_ids == ("REG-020",)

    def test_rechaza_consulta_vacia(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            _consulta(query="   ")

    def test_conserva_etiquetas_e_historial(self):
        entrada = _consulta(
            tags=("sigla", "normativa"), history=("i abans?",), notes="cas de RAG.10"
        )
        assert entrada.tags == ("sigla", "normativa")
        assert entrada.history == ("i abans?",)

    def test_rechaza_dataset_con_consultas_repetidas(self):
        from pydantic import ValidationError

        from server.app.modules.agents_hub.evaluation.golden_dataset import GoldenDataset

        with pytest.raises(ValidationError):
            GoldenDataset(
                name="x", documents_fingerprint="f", queries=(_consulta(), _consulta())
            )


class TestFingerprint:

    def test_should_detect_corpus_fingerprint_mismatch(self):
        """Un dataset medido sobre otro corpus da cifras que no comparan nada."""
        from server.app.modules.agents_hub.evaluation.golden_dataset import (
            GoldenDataset,
            corpus_fingerprint,
            fingerprint_matches,
        )

        dataset = GoldenDataset(
            name="x",
            documents_fingerprint=corpus_fingerprint(["h1", "h2"]),
            queries=(_consulta(),),
        )

        assert fingerprint_matches(dataset, ["h2", "h1"]) is True, "el orden no importa"
        assert fingerprint_matches(dataset, ["h1", "h3"]) is False

    def test_el_fingerprint_es_estable_e_independiente_del_orden(self):
        from server.app.modules.agents_hub.evaluation.golden_dataset import (
            corpus_fingerprint,
        )

        assert corpus_fingerprint(["b", "a"]) == corpus_fingerprint(["a", "b"])
        assert corpus_fingerprint(["a"]) != corpus_fingerprint(["a", "b"])


# ───────────────────────── Harness y gate ─────────────────────────


class _FakeRetriever:
    """Devuelve resultados prefijados por consulta."""

    def __init__(self, por_consulta: dict[str, list[str]]) -> None:
        self.por_consulta = por_consulta

    async def hybrid_search(self, query, query_embedding, chatbot_id, top_k=5, **kw):
        from server.app.modules.agents_hub.services.retriever import SearchResult

        urls = self.por_consulta.get(query, [])[:top_k]
        return [
            SearchResult(
                id=__import__("uuid").uuid4(),
                content="",
                source_url=u,
                language="ca",
                score=1.0 - i / 100,
                metadata={},
            )
            for i, u in enumerate(urls)
        ]


class _FakeEmbedding:
    async def embed(self, text: str) -> list[float]:
        return [0.0] * 1024


class TestHarness:

    @pytest.mark.asyncio
    async def test_should_run_eval_over_fixture_corpus_and_produce_report(self):
        import uuid

        from server.app.modules.agents_hub.evaluation.golden_dataset import GoldenDataset
        from server.app.modules.agents_hub.evaluation.retrieval_eval import (
            run_golden_eval,
        )

        dataset = GoldenDataset(
            name="x",
            documents_fingerprint="f",
            queries=(
                _consulta(query="p1", expected_canonical_urls=("u1",)),
                _consulta(query="p2", expected_canonical_urls=("u9",)),
            ),
        )
        retriever = _FakeRetriever({"p1": ["u1", "u2"], "p2": ["u2", "u3"]})

        informe = await run_golden_eval(
            retriever, _FakeEmbedding(), dataset, uuid.uuid4(), top_k=10
        )

        assert len(informe.per_query) == 2
        assert informe.recall_at_5 == pytest.approx(0.5)
        assert informe.mrr == pytest.approx(0.5)
        assert informe.per_query[0].recall_at_5 == 1.0
        assert informe.per_query[1].recall_at_5 == 0.0

    @pytest.mark.asyncio
    async def test_el_informe_dice_que_se_recupero_para_poder_depurar(self):
        import uuid

        from server.app.modules.agents_hub.evaluation.golden_dataset import GoldenDataset
        from server.app.modules.agents_hub.evaluation.retrieval_eval import (
            run_golden_eval,
        )

        dataset = GoldenDataset(
            name="x",
            documents_fingerprint="f",
            queries=(_consulta(query="p1", expected_canonical_urls=("u9",)),),
        )
        informe = await run_golden_eval(
            _FakeRetriever({"p1": ["u1", "u2"]}), _FakeEmbedding(), dataset, uuid.uuid4()
        )

        assert informe.per_query[0].retrieved[:2] == ["u1", "u2"]
        assert informe.per_query[0].expected == ["u9"]


class TestGate:

    def _informe(self, recall_5: float, recall_10: float, mrr_: float):
        from server.app.modules.agents_hub.evaluation.retrieval_eval import EvalReport

        return EvalReport(
            dataset="x", per_query=(), recall_at_5=recall_5, recall_at_10=recall_10, mrr=mrr_
        )

    def test_should_pass_gate_when_metrics_meet_baseline(self):
        from server.app.modules.agents_hub.evaluation.retrieval_eval import check_gate

        base = self._informe(0.80, 0.90, 0.70)
        veredicto = check_gate(self._informe(0.80, 0.90, 0.70), base)

        assert veredicto.passed is True
        assert veredicto.regressions == []

    def test_una_mejora_pasa_el_gate(self):
        from server.app.modules.agents_hub.evaluation.retrieval_eval import check_gate

        base = self._informe(0.80, 0.90, 0.70)
        assert check_gate(self._informe(0.95, 0.98, 0.85), base).passed is True

    def test_should_fail_gate_when_recall_drops_beyond_tolerance(self):
        from server.app.modules.agents_hub.evaluation.retrieval_eval import check_gate

        base = self._informe(0.80, 0.90, 0.70)
        veredicto = check_gate(self._informe(0.70, 0.90, 0.70), base, tolerance=0.02)

        assert veredicto.passed is False
        assert any("recall_at_5" in r for r in veredicto.regressions)

    def test_una_bajada_dentro_de_la_tolerancia_pasa(self):
        """El ruido de un cambio de fusión no debe romper el build."""
        from server.app.modules.agents_hub.evaluation.retrieval_eval import check_gate

        base = self._informe(0.80, 0.90, 0.70)
        assert check_gate(self._informe(0.79, 0.89, 0.69), base, tolerance=0.02).passed

    def test_el_veredicto_nombra_todas_las_metricas_que_bajan(self):
        from server.app.modules.agents_hub.evaluation.retrieval_eval import check_gate

        base = self._informe(0.80, 0.90, 0.70)
        veredicto = check_gate(self._informe(0.50, 0.50, 0.50), base)

        assert len(veredicto.regressions) == 3

    def test_sin_baseline_no_hay_gate_pero_si_informe(self):
        """La primera ejecución no puede fallar por no tener con qué comparar."""
        from server.app.modules.agents_hub.evaluation.retrieval_eval import check_gate

        veredicto = check_gate(self._informe(0.5, 0.5, 0.5), None)
        assert veredicto.passed is True
        assert "sin baseline" in veredicto.summary.lower()


# ───────────────────────── RAGAS fuera de CI ─────────────────────────


class TestRagasFueraDeCI:

    def test_el_modulo_documenta_que_no_es_un_gate(self):
        import server.app.modules.agents_hub.evaluation.rag_metrics as mod

        doc = (mod.__doc__ or "").lower()
        assert "ci" in doc
        assert "periódica" in doc or "periodica" in doc

    def test_el_fallback_no_se_traga_el_motivo(self):
        """`except Exception: pass` esconde por qué se degradó a la métrica léxica."""
        from pathlib import Path

        import server.app.modules.agents_hub.evaluation.rag_metrics as mod

        fuente = Path(mod.__file__).read_text(encoding="utf-8")
        assert "except Exception:\n            pass" not in fuente
        assert "logger" in fuente
