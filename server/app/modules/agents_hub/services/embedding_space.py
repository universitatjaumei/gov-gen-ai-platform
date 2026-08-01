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
) -> set[tuple[str, int]]:
    """Pares (modelo, dimensión) presentes en los chunks del chatbot.

    Los chunks sin procedencia —los anteriores a MOD.1— no entran: no se puede exigir un
    dato que no existía, y bloquear por eso convertiría una mejora en migración forzosa.
    """
    filas = await session.execute(
        select(HubDocumentChunk.embedding_model, HubDocumentChunk.embedding_dim)
        .where(HubDocumentChunk.chatbot_id == chatbot_id)
        .where(HubDocumentChunk.embedding_model.isnot(None))
        .distinct()
    )
    return {(modelo, int(dim or 0)) for modelo, dim in filas.all()}


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
    )
    ajenos = {espacio for espacio in presentes if espacio != activo}
    if ajenos:
        detalle = ", ".join(f"{modelo} ({dim})" for modelo, dim in sorted(ajenos))
        raise EmbeddingSpaceMismatch(
            f"El corpus del chatbot {chatbot_id} contiene vectores de {detalle}, y el "
            f"modelo activo es {activo[0]} ({activo[1]}). Misma dimensión no es el mismo "
            "espacio vectorial: re-embebe el corpus o vuelve al modelo con el que se generó."
        )
