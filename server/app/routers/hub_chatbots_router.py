"""CRUD de chatbots del Hub.

Deploy: cloud
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, delete as sql_delete

from server.app.api.deps import require_role
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.config_models import HubChatbot

router = APIRouter(prefix="/hub/chatbots", tags=["hub-chatbots"])

_require_admin = require_role("admin", "partner")


class ChatbotOut(BaseModel):
    id: uuid.UUID
    name: str
    client_id: uuid.UUID
    llm_config_id: uuid.UUID
    system_prompt: str
    sources: list[str]
    is_active: bool
    retrieval_mode: str
    retrieval_top_k: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatbotCreate(BaseModel):
    name: str
    client_id: uuid.UUID
    llm_config_id: uuid.UUID
    system_prompt: str
    sources: list[str] = []
    is_active: bool = True
    retrieval_mode: str = "vector"
    retrieval_top_k: int = 8


class ChatbotUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    sources: list[str] | None = None
    is_active: bool | None = None
    retrieval_mode: str | None = None
    retrieval_top_k: int | None = None


@router.get("", response_model=list[ChatbotOut])
async def list_chatbots(
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    result = await session.execute(
        select(HubChatbot).order_by(HubChatbot.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ChatbotOut, status_code=status.HTTP_201_CREATED)
async def create_chatbot(
    body: ChatbotCreate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    chatbot = HubChatbot(
        client_id=body.client_id,
        llm_config_id=body.llm_config_id,
        name=body.name,
        system_prompt=body.system_prompt,
        sources=body.sources,
        is_active=body.is_active,
        retrieval_mode=body.retrieval_mode,
        retrieval_top_k=body.retrieval_top_k,
    )
    session.add(chatbot)
    await session.commit()
    await session.refresh(chatbot)
    return chatbot


@router.patch("/{chatbot_id}", response_model=ChatbotOut)
async def update_chatbot(
    chatbot_id: uuid.UUID,
    body: ChatbotUpdate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    chatbot = await session.get(HubChatbot, chatbot_id)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found"
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(chatbot, field, value)
    chatbot.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(chatbot)
    return chatbot


@router.delete("/{chatbot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chatbot(
    chatbot_id: uuid.UUID,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    chatbot = await session.get(HubChatbot, chatbot_id)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found"
        )
    await session.execute(sql_delete(HubChatbot).where(HubChatbot.id == chatbot_id))
    await session.commit()
