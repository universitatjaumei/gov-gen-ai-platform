"""Hooks utilitarios pre/post-LLM para Fase 13.

Encapsulan la decisión "¿hay que sustituir / revertir según el modo?" para no
duplicar la lógica en cada nodo o factory.
"""

from __future__ import annotations

from typing import Any

from .run_context import AnonymizationMode, RunAnonymizationContext


def apply_pre_llm(text: str, ctx: Any) -> str:
    """Sustituye PII original por sintético antes de invocar el LLM.

    En modo OFF y DETECT_ONLY devuelve `text` sin cambios. Si `ctx` es None,
    el llamador opera fuera del grafo (p.ej. Copilot translate sin workspace)
    y se devuelve el texto tal cual.
    """
    if not isinstance(ctx, RunAnonymizationContext):
        return text
    if ctx.mode in (AnonymizationMode.OFF, AnonymizationMode.DETECT_ONLY):
        return text
    return ctx.substitute(text)


def apply_post_llm(text: str, ctx: Any) -> str:
    """Revierte sintético → original tras el LLM.

    En modos OFF y DETECT_ONLY devuelve `text` sin cambios. Cadenas máscara
    (Disposición 7) permanecen enmascaradas — `reverse_map` no las incluye.
    """
    if not isinstance(ctx, RunAnonymizationContext):
        return text
    if ctx.mode in (AnonymizationMode.OFF, AnonymizationMode.DETECT_ONLY):
        return text
    return ctx.reverse(text)
