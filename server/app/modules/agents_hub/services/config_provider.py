"""Proveedor de configuración (Costura Edge-Cloud)."""

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.config_models import (
    HubChatbot,
    HubLLMConfig,
)
from server.app.modules.agents_hub.services.vocabulary_service import (
    VocabularyTermDTO,
)


class ConfigProvider(Protocol):
    """Protocolo para acceder a la configuración desde módulos edge."""

    async def get_chatbot(self, chatbot_id: uuid.UUID) -> HubChatbot | None: ...
    async def get_llm_config(self, llm_config_id: uuid.UUID) -> HubLLMConfig | None: ...
    async def get_llm_config_for_tier(self, tier: int) -> HubLLMConfig | None: ...
    async def list_active_chatbots(self, organizacion_id: uuid.UUID) -> list[HubChatbot]: ...
    async def get_retrieval_mode(self, chatbot_id: uuid.UUID) -> str: ...
    async def list_vocabulary(
        self, axis: str, organizacion_id: uuid.UUID
    ) -> list[VocabularyTermDTO]: ...


class LocalConfigProvider:
    """Implementación cloud-only: lee directamente de la base de datos."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_chatbot(self, chatbot_id: uuid.UUID) -> HubChatbot | None:
        """Obtiene un chatbot por su ID."""
        result = await self.session.execute(
            select(HubChatbot).where(HubChatbot.id == chatbot_id)
        )
        return result.scalars().first()

    async def get_llm_config(self, llm_config_id: uuid.UUID) -> HubLLMConfig | None:
        """Obtiene una configuración LLM por su ID."""
        result = await self.session.execute(
            select(HubLLMConfig)
            .options(selectinload(HubLLMConfig.provider_rel))
            .where(HubLLMConfig.id == llm_config_id)
        )
        return result.scalars().first()

    async def get_llm_config_for_tier(self, tier: int) -> HubLLMConfig | None:
        """Configuración de **conversación** marcada como default para un tier.

        El filtro por `purpose` no es defensivo: sin él, la configuración de embeddings del
        piloto —marcada por defecto en el nivel 1 al montar Vertex— se devolvía a quien pedía
        un modelo para redactar, y el fallo salía mucho más lejos y acusando al proveedor
        (`ValueError: Provider type desconocido: google_vertexai`). Lo comparten todos los
        que resuelven modelo por nivel: el analizador de HTML de la ingesta y la redacción
        de bloques.
        """
        result = await self.session.execute(
            select(HubLLMConfig)
            .options(selectinload(HubLLMConfig.provider_rel))
            .where(
                HubLLMConfig.tier == tier,
                HubLLMConfig.is_default.is_(True),
                HubLLMConfig.purpose == "chat",
            )
        )
        return result.scalars().first()

    async def list_active_chatbots(self, organizacion_id: uuid.UUID) -> list[HubChatbot]:
        """Obtiene los chatbots activos de una organización."""
        result = await self.session.execute(
            select(HubChatbot).where(
                HubChatbot.organizacion_id == organizacion_id, HubChatbot.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def get_retrieval_mode(self, chatbot_id: uuid.UUID) -> str:
        """Devuelve el retrieval_mode del chatbot (default 'RAG' si no existe)."""
        chatbot = await self.get_chatbot(chatbot_id)
        return getattr(chatbot, "retrieval_mode", "RAG") if chatbot else "RAG"

    async def list_vocabulary(
        self, axis: str, organizacion_id: uuid.UUID
    ) -> list[VocabularyTermDTO]:
        """Términos del vocabulario de un eje, para consumo desde edge (ING.0.1).

        Es la única vía por la que los módulos edge acceden al vocabulario: no pueden
        importar HubVocabularyTerm, que es configuración cloud.
        """
        from server.app.modules.agents_hub.database.config_models import (
            HubVocabularyTerm,
        )

        result = await self.session.execute(
            select(HubVocabularyTerm).where(
                HubVocabularyTerm.organizacion_id == organizacion_id,
                HubVocabularyTerm.axis == axis,
            )
        )
        return [
            VocabularyTermDTO(
                axis=row.axis,
                codi=row.codi,
                nom_primari=row.nom_primari,
                nom_secundari=row.nom_secundari,
                parent_codi=row.parent_codi,
                descripcio_router=row.descripcio_router,
                ordre=row.ordre,
                vigent=row.vigent,
                substituit_per_codi=row.substituit_per_codi,
            )
            for row in result.scalars().all()
        ]
