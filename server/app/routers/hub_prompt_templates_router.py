"""CRUD de prompt templates por chatbot.

Deploy: cloud
"""

import uuid as _uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import require_role
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.config_models import HubPromptTemplate
from server.app.modules.agents_hub.database.connection import get_async_session

router = APIRouter(prefix="/hub/prompt-templates", tags=["hub-prompt-templates"])

_require_admin = require_role("admin", "partner")


class PromptTemplateRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    chatbot_id: UUID
    slug: str
    language: str
    template_text: str
    version: int
    default_tier: int | None
    override_tier: int | None


class PromptTemplateCreate(BaseModel):
    chatbot_id: UUID
    slug: str
    language: str
    template_text: str
    default_tier: int | None = None
    override_tier: int | None = None


class PromptTemplateUpdate(BaseModel):
    template_text: str | None = None
    default_tier: int | None = None
    override_tier: int | None = None


@router.get("/", response_model=list[PromptTemplateRead])
async def list_prompt_templates(
    chatbot_id: UUID | None = None,
    session: AsyncSession = Depends(get_async_session),
    _: UserInfo = Depends(_require_admin),
) -> list[HubPromptTemplate]:
    q = select(HubPromptTemplate).order_by(
        HubPromptTemplate.slug, HubPromptTemplate.language
    )
    if chatbot_id is not None:
        q = q.where(HubPromptTemplate.chatbot_id == chatbot_id)
    result = await session.execute(q)
    return list(result.scalars().all())


@router.post("/", response_model=PromptTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_prompt_template(
    body: PromptTemplateCreate,
    session: AsyncSession = Depends(get_async_session),
    _: UserInfo = Depends(_require_admin),
) -> HubPromptTemplate:
    template = HubPromptTemplate(
        id=_uuid.uuid4(),
        chatbot_id=body.chatbot_id,
        slug=body.slug,
        language=body.language,
        template_text=body.template_text,
        version=1,
        default_tier=body.default_tier,
        override_tier=body.override_tier,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@router.patch("/{template_id}", response_model=PromptTemplateRead)
async def update_prompt_template(
    template_id: UUID,
    body: PromptTemplateUpdate,
    session: AsyncSession = Depends(get_async_session),
    _: UserInfo = Depends(_require_admin),
) -> HubPromptTemplate:
    result = await session.execute(
        select(HubPromptTemplate).where(HubPromptTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    if body.template_text is not None:
        template.template_text = body.template_text
        template.version += 1
    if body.default_tier is not None:
        template.default_tier = body.default_tier
    if body.override_tier is not None:
        template.override_tier = body.override_tier

    await session.commit()
    await session.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    _: UserInfo = Depends(_require_admin),
) -> None:
    result = await session.execute(
        select(HubPromptTemplate).where(HubPromptTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    await session.delete(template)
    await session.commit()
