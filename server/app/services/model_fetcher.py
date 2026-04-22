"""Servicio para la obtención y almacenamiento en caché de modelos de IA disponibles."""
import os
import asyncio
import subprocess
from datetime import datetime, timedelta
from typing import List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import aiohttp

from server.app.database.db import server_engine
from server.app.database.models import ModelCache

# Staleness threshold: refresh if cache is older than 24 hours
CACHE_MAX_AGE = timedelta(hours=24)

async def fetch_google_models() -> List[str]:
    """
    Consulta los modelos disponibles en la API de Google AI (Gemini).
    
    Returns:
        List[str]: Lista de identificadores de modelos (ej: 'gemini-1.5-pro').
    """
    from server.app.services.api_key_service import get_api_key

    try:
        api_key = await get_api_key('google')
        if not api_key:
            print("[Model Fetcher] Google API key not configured")
            # Return hardcoded list as fallback
            return [
                "gemini-2.5-flash",
                "gemini-3-flash-preview",
                "gemini-3.1-pro-preview",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-2.0-flash-exp"
            ]

        if api_key:
            async with aiohttp.ClientSession() as session:
                headers = {"x-goog-api-key": api_key}
                async with session.get(
                    "https://generativelanguage.googleapis.com/v1beta/models", 
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Extract model names, removing 'models/' prefix if present
                        return [
                            m["name"].replace("models/", "") 
                            for m in data.get("models", [])
                            if "gemini" in m["name"]  # Filter for Gemini models
                        ]
                    else:
                        print(f"[Model Fetcher] Google API returned status {resp.status}")

        # Fallback list (verified IDs as of Jan 2026)
        print("[Model Fetcher] Using fallback model list for Google")
        return [
            "gemini-3.1-flash-lite",
            "gemini-3.1-pro",
            "gemini-3-flash",
            "gemini-3-pro",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-1.5-flash",
            "gemini-2.0-flash-exp"
        ]
    except Exception as e:
        print(f"[Model Fetcher] Error fetching Google models: {e}")
        return []

async def fetch_openrouter_models() -> List[str]:
    """Fetch available models from OpenRouter API."""
    from server.app.services.api_key_service import get_api_key

    # Fallback list of popular OpenRouter models
    fallback_models = [
        "openai/gpt-oss-120b",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "openai/gpt-5",
        "openai/gpt-5-mini",
        "anthropic/claude-sonnet-4.5",
        "anthropic/claude-haiku-4.5",
        "anthropic/claude-sonnet-4",
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-opus",
        "google/gemini-2.5-pro",
        "google/gemini-2.5-flash",
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mistral-large",
        "deepseek/deepseek-chat-v3",
    ]

    try:
        api_key = await get_api_key('openrouter')
        if not api_key:
            print("[Model Fetcher] OpenRouter API key not configured, using fallback list")
            return fallback_models

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {api_key}"}
            async with session.get("https://openrouter.ai/api/v1/models", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Extract model IDs from response
                    models = [m["id"] for m in data.get("data", [])]
                    return models if models else fallback_models
                else:
                    print(f"[Model Fetcher] OpenRouter API returned status {resp.status}, using fallback")
                    return fallback_models
    except Exception as e:
        print(f"[Model Fetcher] Error fetching OpenRouter models: {e}")
        return fallback_models


async def refresh_model_cache():
    """
    Actualiza la caché de modelos de todos los proveedores soportados.
    
    Persiste los resultados en la base de datos local para evitar latencia en 
    consultas subsiguientes de los clientes.
    """
    print("[Model Fetcher] Refreshing model cache...")

    providers = {
        "google": fetch_google_models,
        "openrouter": fetch_openrouter_models,
    }

    async with AsyncSession(server_engine) as session:
        for provider, fetch_func in providers.items():
            try:
                models = await fetch_func()
                print(f"[Model Fetcher] {provider}: {len(models)} models found")

                # Upsert cache
                cache = await session.get(ModelCache, provider)
                if cache:
                    cache.models = models
                    cache.last_updated = datetime.utcnow()
                else:
                    cache = ModelCache(provider=provider, models=models)
                    session.add(cache)

                await session.commit()
            except Exception as e:
                print(f"[Model Fetcher] Error caching {provider} models: {e}")

async def get_models_for_provider(provider: str) -> List[str]:
    """Get models for a provider, using cache if fresh, otherwise fetch."""
    async with AsyncSession(server_engine) as session:
        cache = await session.get(ModelCache, provider)

        # Check if cache is fresh
        if cache and (datetime.utcnow() - cache.last_updated) < CACHE_MAX_AGE:
            return cache.models if cache.models else []

        # Cache stale or missing, fetch new data
        fetch_funcs = {
            "google": fetch_google_models,
            "openrouter": fetch_openrouter_models,
        }

        if provider in fetch_funcs:
            models = await fetch_funcs[provider]()

            # Re-check cache before inserting to avoid race conditions
            cache = await session.get(ModelCache, provider)

            if cache:
                cache.models = models
                cache.last_updated = datetime.utcnow()
                session.add(cache)
            else:
                cache = ModelCache(provider=provider, models=models)
                session.add(cache)

            try:
                await session.commit()
            except Exception as e:
                # If race condition occurred (Unique constraint), just ignore and return fresh models
                # The other thread won so data is there.
                print(f"[Model Fetcher] Cache update race condition ignored: {e}")
                await session.rollback()

            return models

        return []
