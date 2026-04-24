"""Seeds de ejemplo para el módulo agents_hub."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.connection import create_async_engine, create_session_factory
from server.app.modules.agents_hub.database.config_models import HubChatbot, HubClient, HubLLMConfig

_DEV_LLM_CONFIG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_DEV_CLIENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
_DEV_CHATBOT_ID = uuid.UUID("00000000-0000-0000-0000-000000000100")


async def seed_hub_defaults() -> None:
    """Crea los datos de ejemplo mínimos para el Hub (idempotente)."""
    engine = create_async_engine()
    factory = create_session_factory(engine)

    async with factory() as session:
        await _seed_llm_config(session)
        await _seed_client(session)
        await _seed_chatbot(session)
        await session.commit()

    await engine.dispose()
    print("[SEED] Hub defaults verificados/creados.")


async def _seed_llm_config(session: AsyncSession) -> None:
    existing = await session.get(HubLLMConfig, _DEV_LLM_CONFIG_ID)
    if existing:
        return
    session.add(HubLLMConfig(
        id=_DEV_LLM_CONFIG_ID,
        provider="google",
        model_name="gemini-2.0-flash",
        temperature=0.7,
        max_tokens=2048,
    ))
    print("[SEED] HubLLMConfig de desarrollo creada.")


async def _seed_client(session: AsyncSession) -> None:
    existing = await session.get(HubClient, _DEV_CLIENT_ID)
    if existing:
        return
    session.add(HubClient(
        id=_DEV_CLIENT_ID,
        name="Cliente Demo",
        partner_id="partner_dev",
        is_active=True,
    ))
    print("[SEED] HubClient de desarrollo creado.")


async def _seed_chatbot(session: AsyncSession) -> None:
    result = await session.execute(
        select(HubChatbot).where(HubChatbot.id == _DEV_CHATBOT_ID)
    )
    if result.scalar_one_or_none():
        return
    session.add(HubChatbot(
        id=_DEV_CHATBOT_ID,
        client_id=_DEV_CLIENT_ID,
        llm_config_id=_DEV_LLM_CONFIG_ID,
        name="Chatbot Demo",
        system_prompt="Eres un asistente útil que responde preguntas basándose en los documentos proporcionados.",
        is_active=True,
    ))
    print("[SEED] HubChatbot de desarrollo creado.")
