"""El modelo por defecto de un nivel tiene que ser un modelo de **conversación**.

Encontrado al cablear la generación de informes (VER.1): `get_model_for_tier(1, ...)` moría
con `ValueError: Provider type desconocido: google_vertexai`. La causa no era Vertex: era que
la configuración marcada `is_default` para el nivel 1 en esta máquina es
`gemini-embedding-001`, **de propósito `embedding`**, creada al montar los embeddings del
piloto. `get_llm_config_for_tier` no miraba `purpose`, así que devolvía un modelo de
embeddings a quien pedía uno de redacción.

No es un problema de datos de esta máquina: `hub_llm_configs.purpose` existe desde que se
añadieron los embeddings, y nada impedía que la primera configuración marcada por defecto
fuera de cualquier propósito. Todo lo que resuelve modelo por nivel —el analizador de HTML de
la ingesta y ahora la redacción de bloques— comparte el fallo.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.modules.agents_hub.database.config_models import HubLLMConfig, HubProvider
from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider


async def _proveedor(session, tipo: str) -> str:
    proveedor = HubProvider(
        id=f"prov-{uuid.uuid4().hex[:8]}",
        provider_type=tipo,
        name=f"Proveedor {tipo}",
    )
    session.add(proveedor)
    await session.flush()
    return proveedor.id


async def _config(session, proveedor_id: str, *, purpose: str, modelo: str, tier: int = 1):
    config = HubLLMConfig(
        provider=proveedor_id,
        model_name=modelo,
        tier=tier,
        is_default=True,
        purpose=purpose,
        label=modelo,
    )
    session.add(config)
    await session.flush()
    return config


@pytest.mark.asyncio
async def test_should_ignore_an_embedding_config_marked_as_default(db_url):
    """Es el caso real: el de embeddings se marcó por defecto y se llevó por delante todo lo
    que pide modelo por nivel."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            # La BD de plantilla ya trae configuraciones sembradas; se retiran del nivel 9
            # usando un nivel propio para que este test no dependa de ellas.
            vertex = await _proveedor(session, "google_vertexai")
            genai = await _proveedor(session, "google_genai")
            await _config(session, vertex, purpose="embedding",
                          modelo="gemini-embedding-001", tier=9)
            await _config(session, genai, purpose="chat",
                          modelo="gemini-2.5-flash", tier=9)
            await session.commit()

            elegida = await LocalConfigProvider(session).get_llm_config_for_tier(9)

            assert elegida is not None
            assert elegida.purpose == "chat"
            assert elegida.model_name == "gemini-2.5-flash"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_should_return_nothing_when_the_only_default_is_not_for_chat(db_url):
    """Mejor sin modelo —el error dice que no hay configuración— que con uno de embeddings,
    que falla mucho más lejos y acusando al proveedor."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            vertex = await _proveedor(session, "google_vertexai")
            await _config(session, vertex, purpose="embedding",
                          modelo="gemini-embedding-001", tier=8)
            await session.commit()

            assert await LocalConfigProvider(session).get_llm_config_for_tier(8) is None
    finally:
        await engine.dispose()
