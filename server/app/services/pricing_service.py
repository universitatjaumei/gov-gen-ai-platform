"""Servicio para gestionar los precios de modelos de IA vía API de OpenRouter."""
import aiohttp
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from server.app.database.db import server_engine
from server.app.database.models import ModelPricing

async def update_prices_from_openrouter():
    """
    Sincroniza los precios más recientes de los modelos desde OpenRouter hacia la BD local.
    
    Actualiza los costes de entrada y salida por millón de tokens para todos los 
    modelos soportados, creando nuevos registros si no existen.
    """
    print("Updating model prices from OpenRouter...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://openrouter.ai/api/v1/models") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models_data = data.get("data", [])

                    async with AsyncSession(server_engine) as session:
                        # Batch load existing prices
                        existing_result = await session.exec(select(ModelPricing))
                        existing_map = {m.id: m for m in existing_result.all()}

                        count_updated = 0
                        count_new = 0

                        for model_info in models_data:
                            model_id = model_info.get("id")
                            pricing = model_info.get("pricing", {})

                            prompt_price = float(pricing.get("prompt", 0)) * 1_000_000
                            completion_price = float(pricing.get("completion", 0)) * 1_000_000

                            if model_id in existing_map:
                                # Update existing
                                existing_model = existing_map[model_id]
                                if (existing_model.input_cost_per_m != prompt_price or
                                    existing_model.output_cost_per_m != completion_price):
                                    existing_model.input_cost_per_m = prompt_price
                                    existing_model.output_cost_per_m = completion_price
                                    existing_model.updated_at = datetime.utcnow()
                                    session.add(existing_model)
                                    count_updated += 1
                            else:
                                # Create new
                                new_pricing = ModelPricing(
                                    id=model_id,
                                    input_cost_per_m=prompt_price,
                                    output_cost_per_m=completion_price,
                                    updated_at=datetime.utcnow()
                                )
                                session.add(new_pricing)
                                count_new += 1

                        await session.commit()
                        print(f"Updated prices: {count_new} new, {count_updated} updated via OpenRouter")
                else:
                    print(f"Failed to fetch prices from OpenRouter: Status {resp.status}")
    except Exception as e:
        print(f"Error updating model prices: {e}")

async def calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calcula el coste real de una solicitud de IA en dólares.
    
    Normaliza el proveedor y el modelo para localizar su configuración de precio 
    en la base de datos local y aplica las fórmulas de coste por millón de tokens.

    Args:
        provider: Proveedor de la IA (Google, OpenRouter, OpenAI).
        model: Identificador del modelo utilizado.
        input_tokens: Cantidad de tokens enviados en el prompt.
        output_tokens: Cantidad de tokens generados en la respuesta.

    Returns:
        float: Coste total calculado en USD.
    """
    # Normalize provider
    provider_lower = provider.lower()

    # Determine the model ID to look up in ModelPricing
    lookup_id = model

    # If Google, we need to find the equivalent OpenRouter ID (usually "google/model-name")
    if provider_lower == "google":
        # Heuristic: try prepending "google/" if not present
        if not model.startswith("google/"):
            lookup_id = f"google/{model}"

    # If OpenRouter, it's usually the full ID (e.g. "openai/gpt-4")

    async with AsyncSession(server_engine) as session:
        pricing = await session.get(ModelPricing, lookup_id)

        # Fallback: try searching by suffix if exact match fails
        if not pricing and provider_lower == "google":
             # Try to find a model that ends with the model name (e.g. 'gemini-1.5-flash' matching 'google/gemini-1.5-flash-latest' etc?)
             # For now, let's just stick to "google/" prefix or exact match.
             # Maybe the model name used in app is just "gemini-1.5-flash"
             pass

        if pricing:
            input_cost = (input_tokens / 1_000_000) * pricing.input_cost_per_m
            output_cost = (output_tokens / 1_000_000) * pricing.output_cost_per_m
            return input_cost + output_cost

        # If no pricing found, return 0.0 (or hardcoded fallback?)
        # print(f"No pricing found for {provider}/{model} (lookup: {lookup_id})")
        return 0.0
