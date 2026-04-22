# client_app/app/services/api_key_service.py
"""
API Key Management Service for Client (On-Premise).

Stores and retrieves API keys from local SQLite database.
Falls back to .env file if not found in database.
"""
import os
from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
from dotenv import load_dotenv

from client_app.app.database.db import client_engine
from client_app.app.database.models import ProviderAPIKey

# Load .env for fallback
load_dotenv()

async def get_api_key(provider: str) -> Optional[str]:
    """Get API key from database, fallback to .env if not found."""
    async with AsyncSession(client_engine) as session:
        key_record = await session.get(ProviderAPIKey, provider)
        if key_record and key_record.api_key:
            return key_record.api_key

        # Fallback to environment variable
        env_var = f"{provider.upper()}_API_KEY"
        return os.getenv(env_var)

async def save_api_key(provider: str, api_key: str) -> None:
    """Save or update API key in database."""
    async with AsyncSession(client_engine) as session:
        key_record = await session.get(ProviderAPIKey, provider)
        if key_record:
            key_record.api_key = api_key
            key_record.updated_at = datetime.utcnow()
        else:
            key_record = ProviderAPIKey(provider=provider, api_key=api_key)
            session.add(key_record)

        await session.commit()

async def migrate_api_keys_from_env() -> None:
    """Migrate API keys from .env to database if database is empty."""
    async with AsyncSession(client_engine) as session:
        result = await session.exec(select(ProviderAPIKey))
        existing = result.all()

        if existing:
            return

        # Migrate from .env
        providers = ["google", "openrouter"]
        migrated = 0

        for provider in providers:
            env_var = f"{provider.upper()}_API_KEY"
            api_key = os.getenv(env_var)

            if api_key:
                key_record = ProviderAPIKey(provider=provider, api_key=api_key)
                session.add(key_record)
                migrated += 1

        if migrated > 0:
            await session.commit()

