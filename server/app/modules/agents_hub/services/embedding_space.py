"""Coherencia del espacio vectorial de un corpus (MOD.1). Deploy: edge.

Misma dimensión no significa mismo espacio. Dos modelos de 1024 producen vectores que
pgvector compara sin protestar y cuyo coseno no significa nada. El síntoma no es un error:
es un retriever que «funciona regular», que es la avería más cara de encontrar.

Esta comprobación es la que hace utilizable el interruptor de modelo: antes de re-embeber o
de servir un corpus con otro modelo activo, se dice en voz alta qué hay dentro.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk


class EmbeddingSpaceMismatch(Exception):
    """El corpus está embebido con un modelo distinto del activo."""


async def describe_corpus_embedding_space(
    session: AsyncSession, chatbot_id: uuid.UUID
) -> set[tuple[str, int, str | None]]:
    """Tripletas (modelo, dimensión, tipo de tarea) presentes en los chunks del chatbot.

    RAG.9 corre esto en cada consulta de chat, y lo hace asequible el índice
    `ix_hub_document_chunks_embedding_space`, que cubre exactamente estas tres columnas: el
    caso bueno —no hay desajuste— se resuelve sin tocar el heap.

    **El tipo de tarea entra en la tripleta desde PIL.1.** Sin él, embeber el corpus con
    `RETRIEVAL_QUERY` y servirlo con `RETRIEVAL_DOCUMENT` pasaba inadvertido: modelo y
    dimensión coinciden, y lo único que cambia es que el retriever empeora. `None` es
    legítimo y significa «este espacio no distingue propósito» —el modelo local—, así que se
    compara como un valor más y no como un comodín.
    """
    filas = await session.execute(
        select(
            HubDocumentChunk.embedding_model,
            HubDocumentChunk.embedding_dim,
            HubDocumentChunk.embedding_task_type,
        )
        .where(HubDocumentChunk.chatbot_id == chatbot_id)
        .distinct()
    )
    return {(modelo, int(dim), tarea) for modelo, dim, tarea in filas.all()}


async def assert_embedding_space_matches(
    session: AsyncSession, chatbot_id: uuid.UUID, embedding_service: Any
) -> None:
    """Lanza `EmbeddingSpaceMismatch` si el corpus no es del modelo activo.

    El mensaje nombra los dos espacios a propósito: quien lo lea necesita saber qué hay y
    contra qué se compara para decidir si re-embebe o si cambia la configuración.
    """
    presentes = await describe_corpus_embedding_space(session, chatbot_id)
    if not presentes:
        return

    activo = (
        getattr(embedding_service, "model_name", None),
        int(getattr(embedding_service, "dimensions", 0) or 0),
        getattr(embedding_service, "embedding_task_type", None),
    )
    ajenos = {espacio for espacio in presentes if espacio != activo}
    if ajenos:
        detalle = ", ".join(
            f"{modelo} ({dim}, {tarea or 'sin tipo de tarea'})"
            for modelo, dim, tarea in sorted(ajenos, key=lambda e: (e[0], e[1], e[2] or ""))
        )
        raise EmbeddingSpaceMismatch(
            f"El corpus del chatbot {chatbot_id} contiene vectores de {detalle}, y el "
            f"modelo activo es {activo[0]} ({activo[1]}, "
            f"{activo[2] or 'sin tipo de tarea'}). Misma dimensión no es el mismo espacio "
            "vectorial, y el mismo modelo con otro tipo de tarea tampoco: re-embebe el "
            "corpus o vuelve a la configuración con la que se generó."
        )
