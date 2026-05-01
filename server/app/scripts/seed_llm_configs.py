"""Seeding de configuraciones LLM según proveedores disponibles.

Idempotente: no duplica si las configs ya existen.
Ejecutar con: uv run python -m server.app.scripts.seed_llm_configs
"""
import asyncio
import os

from server.app.modules.agents_hub.database.connection import (
    create_async_engine,
    create_session_factory,
)
from server.app.modules.agents_hub.database.config_models import HubLLMConfig
from sqlalchemy import select


_CONFIGS = [
    # (provider, model_name, tier, label, is_default, api_key_env)
    ("google",      "gemini-2.5-flash",        1, "Gemini Flash 2.5", True,  "GOOGLE_API_KEY"),
    ("google",      "gemini-2.5-pro",          2, "Gemini Pro 2.5",   True,  "GOOGLE_API_KEY"),
    ("openai",      "gpt-4o-mini",             1, "GPT-4o Mini",      False, "OPENAI_API_KEY"),
    ("openai",      "gpt-4o",                  2, "GPT-4o",           False, "OPENAI_API_KEY"),
    ("ollama",      "llama3.2",                1, "Llama 3.2 Local",  False, "OLLAMA_BASE_URL"),
    ("openrouter",  "google/gemini-2.5-flash", 1, "OR Gemini Flash",  False, "OPENROUTER_API_KEY"),
    ("openrouter",  "anthropic/claude-3.5-sonnet", 2, "Claude 3.5 Sonnet", False, "OPENROUTER_API_KEY"),
]


async def _seed() -> None:
    engine = create_async_engine()
    factory = create_session_factory(engine)

    async with factory() as session:
        for provider, model_name, tier, label, is_default, env_var in _CONFIGS:
            if not os.getenv(env_var):
                print(f"[SEED] Omitiendo {label}: {env_var} no definida")
                continue

            existing = await session.execute(
                select(HubLLMConfig).where(
                    HubLLMConfig.provider == provider,
                    HubLLMConfig.model_name == model_name,
                )
            )
            if existing.scalar_one_or_none():
                print(f"[SEED] Ya existe: {label}")
                continue

            # Si is_default=True, verificar que no haya otro default para el mismo tier
            if is_default:
                dup = await session.execute(
                    select(HubLLMConfig).where(
                        HubLLMConfig.tier == tier,
                        HubLLMConfig.is_default.is_(True),
                    )
                )
                if dup.scalar_one_or_none():
                    is_default = False

            session.add(
                HubLLMConfig(
                    provider=provider,
                    model_name=model_name,
                    tier=tier,
                    label=label,
                    is_default=is_default,
                    api_key_secret_name=env_var,
                )
            )
            print(f"[SEED] Creada config: {label} (tier {tier}, default={is_default})")

        await session.commit()

    await engine.dispose()
    print("[SEED] Seeding de LLM configs completado.")


if __name__ == "__main__":
    asyncio.run(_seed())
