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


class ConfigProvider(Protocol):
    """Protocolo para acceder a la configuración desde módulos edge."""

    async def get_chatbot(self, chatbot_id: uuid.UUID) -> HubChatbot | None: ...
    async def get_llm_config(self, llm_config_id: uuid.UUID) -> HubLLMConfig | None: ...
    async def get_llm_config_for_tier(self, tier: int) -> HubLLMConfig | None: ...
    async def list_active_chatbots(self, client_id: uuid.UUID) -> list[HubChatbot]: ...
    async def get_retrieval_mode(self, chatbot_id: uuid.UUID) -> str: ...


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
        """Obtiene la configuración LLM marcada como default para un tier."""
        result = await self.session.execute(
            select(HubLLMConfig)
            .options(selectinload(HubLLMConfig.provider_rel))
            .where(
                HubLLMConfig.tier == tier,
                HubLLMConfig.is_default.is_(True),
            )
        )
        return result.scalars().first()

    async def list_active_chatbots(self, client_id: uuid.UUID) -> list[HubChatbot]:
        """Obtiene los chatbots activos de un cliente."""
        result = await self.session.execute(
            select(HubChatbot).where(
                HubChatbot.client_id == client_id, HubChatbot.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def get_retrieval_mode(self, chatbot_id: uuid.UUID) -> str:
        """Devuelve el retrieval_mode del chatbot (default 'vector' si no existe)."""
        chatbot = await self.get_chatbot(chatbot_id)
        return getattr(chatbot, "retrieval_mode", "vector") if chatbot else "vector"
