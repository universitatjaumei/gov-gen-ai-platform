"""CRUD de configuraciones LLM del Hub.

Deploy: cloud
"""
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from server.app.api.deps import require_role
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.config_models import HubChatbot, HubLLMConfig, HubProvider
from server.app.modules.agents_hub.services.model_factory import _build_model
from server.app.services.model_fetcher import get_models_for_provider

router = APIRouter(prefix="/hub/llm-configs", tags=["hub-llm-configs"])

_require_admin = require_role("admin", "partner")


class HubProviderOut(BaseModel):
    id: str
    name: str
    provider_type: str
    base_url: str | None
    api_key: str | None

    model_config = {"from_attributes": True}


class HubProviderCreate(BaseModel):
    id: str
    name: str
    provider_type: str
    base_url: str | None = None
    api_key: str | None = None


class HubProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    api_key: str | None = None


@router.get("/providers", response_model=list[HubProviderOut])
async def list_providers(
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    """Obtiene la lista de proveedores dinámicos."""
    result = await session.execute(select(HubProvider).order_by(HubProvider.name))
    return result.scalars().all()


@router.post("/providers", response_model=HubProviderOut, status_code=status.HTTP_201_CREATED)
async def create_provider(
    body: HubProviderCreate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    """Crea un nuevo proveedor."""
    existing = await session.get(HubProvider, body.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Ya existe un proveedor con este ID"
        )
    provider = HubProvider(**body.model_dump())
    session.add(provider)
    await session.commit()
    await session.refresh(provider)
    return provider


@router.patch("/providers/{provider_id}", response_model=HubProviderOut)
async def update_provider(
    provider_id: str,
    body: HubProviderUpdate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    """Actualiza un proveedor existente."""
    provider = await session.get(HubProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
        
    await session.commit()
    await session.refresh(provider)
    return provider


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: str,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    """Elimina un proveedor si no está en uso."""
    provider = await session.get(HubProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        
    in_use = await session.execute(
        select(HubLLMConfig).where(HubLLMConfig.provider == provider_id)
    )
    if in_use.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: hay configuraciones usando este proveedor",
        )
        
    await session.delete(provider)
    await session.commit()


@router.get("/available-models/{provider_id}")
async def list_available_models(
    provider_id: str,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    """Obtiene la lista de modelos disponibles para un proveedor (usa caché)."""
    provider = await session.get(HubProvider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
        
    models = await get_models_for_provider(provider_id) # Usamos provider_id que puede ser el tipo
    if not models:
        # Fallbacks just in case
        if provider.provider_type == "google_genai":
            models = ["gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-pro"]
        elif provider.provider_type == "openai_compatible":
            models = ["gpt-4o", "gpt-4o-mini", "llama3.2"]
    return {"ok": True, "models": models}


class LLMConfigOut(BaseModel):
    id: uuid.UUID
    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    api_key_secret_name: str | None
    tier: int
    label: str
    is_default: bool

    model_config = {"from_attributes": True}


class LLMConfigCreate(BaseModel):
    provider: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 2048
    api_key_secret_name: str | None = None
    tier: int = 1
    label: str = ""
    is_default: bool = False


class LLMConfigUpdate(BaseModel):
    label: str | None = None
    tier: int | None = None
    model_name: str | None = None
    api_key_secret_name: str | None = None
    is_default: bool | None = None
    temperature: float | None = None
    max_tokens: int | None = None


@router.get("", response_model=list[LLMConfigOut])
async def list_llm_configs(
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    result = await session.execute(
        select(HubLLMConfig).order_by(HubLLMConfig.tier, HubLLMConfig.label)
    )
    return result.scalars().all()


@router.post("", response_model=LLMConfigOut, status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    body: LLMConfigCreate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    if body.is_default:
        existing = await session.execute(
            select(HubLLMConfig).where(
                HubLLMConfig.tier == body.tier,
                HubLLMConfig.is_default.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una configuración por defecto para el tier {body.tier}",
            )

    config = HubLLMConfig(**body.model_dump())
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return config


@router.patch("/{config_id}", response_model=LLMConfigOut)
async def update_llm_config(
    config_id: uuid.UUID,
    body: LLMConfigUpdate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    config = await session.get(HubLLMConfig, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    target_tier = body.tier if body.tier is not None else config.tier
    if body.is_default is True:
        existing = await session.execute(
            select(HubLLMConfig).where(
                HubLLMConfig.tier == target_tier,
                HubLLMConfig.is_default.is_(True),
                HubLLMConfig.id != config_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una configuración por defecto para el tier {target_tier}",
            )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(config, field, value)

    await session.commit()
    await session.refresh(config)
    return config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config(
    config_id: uuid.UUID,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    config = await session.get(HubLLMConfig, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    in_use = await session.execute(
        select(HubChatbot).where(HubChatbot.llm_config_id == config_id)
    )
    if in_use.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: hay chatbots usando esta configuración",
        )

    await session.delete(config)
    await session.commit()


@router.post("/{config_id}/test")
async def test_llm_connection(
    config_id: uuid.UUID,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    result = await session.execute(
        select(HubLLMConfig)
        .options(selectinload(HubLLMConfig.provider_rel))
        .where(HubLLMConfig.id == config_id)
    )
    config = result.scalars().first()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")

    model = _build_model(config)
    t0 = time.monotonic()
    await model.ainvoke([HumanMessage(content="test")])
    latency_ms = int((time.monotonic() - t0) * 1000)

    return {"ok": True, "latency_ms": latency_ms}
