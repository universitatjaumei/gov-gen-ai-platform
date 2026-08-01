"""Empaquetador de contexto con presupuesto de tokens (RAG.5). Deploy: edge.

Antes de esto, el presupuesto solo lo respetaba MD_LONG_CONTEXT. En RAG, con un `top_k`
grande o documentos largos, el contexto crecía sin techo hasta que lo cortaba el proveedor
del modelo — y cuando corta el proveedor no queda traza de qué se perdió, ni el usuario sabe
que su respuesta se construyó sobre parte del fundamento.

El packer corta con criterio y dejando constancia: por score descendente y anotando cuántas
evidencias quedaron fuera. `dropped_count` es lo que RAG.11 necesita para decidir el bypass.

**Presupuesto**: el ya resuelto por el `ConfigResolver` (cascada plataforma → organización →
chatbot, columna creada en VIS.2). El default de plataforma son 128.000 tokens **con carácter
general** — decisión del usuario del 2026-08-01 —, así que este módulo lo CONSUME y no lo baja.

**Lo que este packer NO hace**: fusionar chunks adyacentes del mismo documento. El prompt lo
pedía, pero hoy ningún productor emite evidencia a nivel de chunk —`VectorRetrievalStrategy`
agrupa por documento y se queda con el mejor fragmento—, así que la fusión sería código muerto
(CLAUDE.md prohíbe el código especulativo). Cambiar esa agrupación para alimentarla duplicaría
entradas en el `sources` del evento SSE `done`, contrato que RAG.2 fijó por snapshot. Cuando
RAG.7 (parent-child) emita varios fragmentos por documento, ahí es donde toca añadirla, con su
test `should_merge_adjacent_chunks_of_same_document`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.app.modules.agents_hub.ingestion.markdown_utils import estimate_tokens


@dataclass(frozen=True)
class PackedContext:
    """Evidencia que cabe en el presupuesto, y lo que se dejó fuera."""

    items: list[Any] = field(default_factory=list)
    total_tokens: int = 0
    dropped_count: int = 0


def pack(evidences: list[Any], budget_tokens: int) -> PackedContext:
    """Ordena por score y acumula hasta el presupuesto.

    Mismo contador de tokens que usa el límite de MD_LONG_CONTEXT (`estimate_tokens`,
    4 caracteres por token): aproximado, pero **el mismo en los dos sitios**, que es lo que
    hace comparables sus presupuestos.

    Si ni la mejor evidencia cabe, entra igualmente: un contexto vacío no produce ninguna
    respuesta y uno recortado sí. Es el mismo criterio con el que VIS.2 degrada el long
    context en vez de lanzar una excepción.
    """
    if not evidences:
        return PackedContext()

    ordenadas = sorted(evidences, key=lambda e: (e.score if e.score is not None else 0.0), reverse=True)

    cabidas: list[Any] = []
    acumulado = 0
    for evidencia in ordenadas:
        coste = estimate_tokens(evidencia.content or "")
        if cabidas and acumulado + coste > budget_tokens:
            continue
        cabidas.append(evidencia)
        acumulado += coste
        if acumulado >= budget_tokens:
            break

    return PackedContext(
        items=cabidas,
        total_tokens=acumulado,
        dropped_count=len(ordenadas) - len(cabidas),
    )
