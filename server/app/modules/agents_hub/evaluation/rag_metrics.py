"""Métricas de calidad RAG con RAGAS: evaluación periódica, NUNCA un gate de CI.

`faithfulness` y `answer_relevancy` llaman a un LLM, así que cuestan dinero, tardan y no
son deterministas. Meterlas en CI daría un build lento y con falsos rojos.

La división del bloque RAG es:

- **Gate de CI**: `retrieval_metrics.py` + `retrieval_eval.py` — recall@k y MRR, funciones
  puras sin LLM, en segundos, en cada cambio del retriever.
- **Evaluación periódica manual**: este módulo, cuando se quiera saber si las respuestas
  se apoyan en el contexto. A mano o de noche, jamás bloqueando un PR.

Cuando RAGAS falla se cae a una métrica léxica de solapamiento, que es **mucho más pobre**.
Ese fallback se registra con el motivo: un número que parece una métrica y en realidad es
un solapamiento de palabras, sin dejar rastro de por qué, es peor que no tener el número.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, faithfulness

    _RAGAS_AVAILABLE = True
except ImportError:
    _RAGAS_AVAILABLE = False
    evaluate = None  # type: ignore[assignment]


async def calculate_faithfulness(answer: str, context: str) -> float:
    """Calcula la fidelidad de la respuesta al contexto.

    Args:
        answer: Respuesta generada
        context: Contexto proporcionado

    Returns:
        Score de fidelidad (0-1)
    """
    if _RAGAS_AVAILABLE and evaluate is not None:
        data = {
            "question": ["placeholder"],
            "answer": [answer],
            "contexts": [[context]],
        }
        dataset = Dataset.from_dict(data)
        try:
            result = evaluate(dataset, metrics=[faithfulness])
            return result["faithfulness"]
        except Exception as exc:
            logger.warning(
                "RAGAS faithfulness fallo (%s: %s); se degrada a solapamiento lexico, "
                "que NO es comparable con una medida de RAGAS",
                type(exc).__name__,
                exc,
            )

    # Fallback: overlap de palabras clave entre contexto y respuesta
    context_words = set(context.lower().split())
    answer_words = set(answer.lower().split())
    overlap = (
        len(context_words & answer_words) / len(context_words) if context_words else 0
    )
    return min(overlap * 2, 1.0)


async def calculate_answer_relevance(question: str, answer: str) -> float:
    """Calcula la relevancia de la respuesta a la pregunta.

    Args:
        question: Pregunta original
        answer: Respuesta generada

    Returns:
        Score de relevancia (0-1)
    """
    if _RAGAS_AVAILABLE and evaluate is not None:
        data = {
            "question": [question],
            "answer": [answer],
            "contexts": [[""]],
        }
        dataset = Dataset.from_dict(data)
        try:
            result = evaluate(dataset, metrics=[answer_relevancy])
            return result["answer_relevancy"]
        except Exception as exc:
            logger.warning(
                "RAGAS answer_relevancy fallo (%s: %s); se degrada a solapamiento "
                "lexico, que NO es comparable con una medida de RAGAS",
                type(exc).__name__,
                exc,
            )

    # Fallback: overlap de palabras significativas entre pregunta y respuesta
    import re

    stop_words = {
        "qué",
        "cómo",
        "cuál",
        "es",
        "para",
        "un",
        "una",
        "de",
        "la",
        "el",
        "en",
    }
    q_words = (
        {re.sub(r"[^\w]", "", w) for w in question.lower().split()} - stop_words - {""}
    )
    a_words = {re.sub(r"[^\w]", "", w) for w in answer.lower().split()} - {""}
    overlap = len(q_words & a_words) / len(q_words) if q_words else 0
    return min(overlap * 2, 1.0)
