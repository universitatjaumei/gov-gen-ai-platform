"""Recomendación de retrieval_mode basada en tamaño de corpus y ventana de contexto."""

from __future__ import annotations


def recommend_retrieval_mode(total_tokens: int, context_window: int = 128_000) -> tuple[str, str]:
    """Devuelve (modo_recomendado, razon).

    Reglas:
    - long_context: corpus <= 60% de context_window
    - agentic: corpus <= 16x context_window
    - vector: corpus mayor
    """
    long_ctx_limit = int(context_window * 0.6)
    agentic_limit = context_window * 16

    if total_tokens < long_ctx_limit:
        return (
            "long_context",
            (
                f"El corpus ({total_tokens:,} tokens) cabe al 60 % de la ventana del LLM "
                f"({context_window:,} tokens). Recomendado long_context: cero pérdida de "
                f"información y citas más precisas."
            ),
        )

    if total_tokens < agentic_limit:
        return (
            "agentic",
            (
                f"El corpus ({total_tokens:,} tokens) excede long_context, pero el LLM "
                f"puede seleccionar qué documentos leer. Recomendado agentic."
            ),
        )

    return (
        "vector",
        (
            f"El corpus ({total_tokens:,} tokens) requiere búsqueda vectorial para escalar "
            f"en coste y latencia. Recomendado vector."
        ),
    )