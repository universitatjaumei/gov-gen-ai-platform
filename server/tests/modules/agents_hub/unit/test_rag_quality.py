"""Tests de calidad RAG usando RAGAS."""
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestRAGQuality:

    @pytest.fixture
    def golden_qa_pairs(self):
        return [
            {
                "question": "¿Qué es Python?",
                "answer": "Python es un lenguaje de programación.",
                "context": "Python es un lenguaje de programación versátil y fácil de aprender.",
            },
            {
                "question": "¿Para qué sirve FastAPI?",
                "answer": "FastAPI es un framework para crear APIs.",
                "context": "FastAPI es un framework web moderno para construir APIs con Python.",
            },
        ]

    @pytest.mark.asyncio
    async def test_rag_faithfulness(self, golden_qa_pairs) -> None:
        """La respuesta no debe alucinar fuera del contexto."""
        from server.app.modules.agents_hub.evaluation.rag_metrics import calculate_faithfulness

        # Forzar el fallback (sin llamadas a LLM externo)
        with patch(
            'server.app.modules.agents_hub.evaluation.rag_metrics.evaluate',
            side_effect=Exception("ragas not available in test"),
        ):
            for qa in golden_qa_pairs:
                score = await calculate_faithfulness(
                    answer=qa["answer"],
                    context=qa["context"],
                )
                assert score >= 0.7, f"Faithfulness bajo para: {qa['question']}"

    @pytest.mark.asyncio
    async def test_rag_answer_relevance(self, golden_qa_pairs) -> None:
        """La respuesta debe ser relevante a la pregunta."""
        from server.app.modules.agents_hub.evaluation.rag_metrics import calculate_answer_relevance

        with patch(
            'server.app.modules.agents_hub.evaluation.rag_metrics.evaluate',
            side_effect=Exception("ragas not available in test"),
        ):
            for qa in golden_qa_pairs:
                score = await calculate_answer_relevance(
                    question=qa["question"],
                    answer=qa["answer"],
                )
                assert score >= 0.7, f"Relevancia baja para: {qa['question']}"
