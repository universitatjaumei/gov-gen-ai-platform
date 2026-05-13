"""CRUD de clientes del Hub.

Deploy: cloud
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select, delete as sql_delete

from server.app.api.deps import require_role
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.config_models import HubChatbot, HubClient

router = APIRouter(prefix="/hub/clients", tags=["hub-clients"])

_require_admin = require_role("admin", "partner")


class ClientRead(BaseModel):
    id: uuid.UUID
    name: str
    partner_id: str
    theme_config: dict
    is_active: bool
    chatbot_count: int = 0
    default_public_graph_profile: str
    default_retrieval_mode: str
    default_language_mode: str
    default_quality_threshold: float
    default_min_retrieval_results: int
    default_min_retrieval_score: float
    default_reranker_enabled: bool
    default_answer_template: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientCreate(BaseModel):
    name: str
    partner_id: str
    theme_config: dict = {}
    is_active: bool = True
    default_public_graph_profile: str = "PUBLIC_KB_RICH"
    default_retrieval_mode: str = "RAG"
    default_language_mode: str = "prefer"
    default_quality_threshold: float = 0.6
    default_min_retrieval_results: int = 2
    default_min_retrieval_score: float = 0.25
    default_reranker_enabled: bool = True
    default_answer_template: str = "generic"


class ClientUpdate(BaseModel):
    name: str | None = None
    partner_id: str | None = None
    theme_config: dict | None = None
    is_active: bool | None = None
    default_public_graph_profile: str | None = None
    default_retrieval_mode: str | None = None
    default_language_mode: str | None = None
    default_quality_threshold: float | None = None
    default_min_retrieval_results: int | None = None
    default_min_retrieval_score: float | None = None
    default_reranker_enabled: bool | None = None
    default_answer_template: str | None = None


_count_sq = (
    select(func.count(HubChatbot.id))
    .where(HubChatbot.client_id == HubClient.id)
    .correlate(HubClient)
    .scalar_subquery()
)


@router.get("", response_model=list[ClientRead])
async def list_clients(
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    rows = (
        await session.execute(
            select(HubClient, _count_sq.label("chatbot_count")).order_by(
                HubClient.created_at.desc()
            )
        )
    ).all()
    return [
        ClientRead.model_validate(c).model_copy(update={"chatbot_count": count})
        for c, count in rows
    ]


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    client = HubClient(
        name=body.name,
        partner_id=body.partner_id,
        theme_config=body.theme_config,
        is_active=body.is_active,
        default_public_graph_profile=body.default_public_graph_profile,
        default_retrieval_mode=body.default_retrieval_mode,
        default_language_mode=body.default_language_mode,
        default_quality_threshold=body.default_quality_threshold,
        default_min_retrieval_results=body.default_min_retrieval_results,
        default_min_retrieval_score=body.default_min_retrieval_score,
        default_reranker_enabled=body.default_reranker_enabled,
        default_answer_template=body.default_answer_template,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return ClientRead.model_validate(client).model_copy(update={"chatbot_count": 0})


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    client = await session.get(HubClient, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    client.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(client)
    return ClientRead.model_validate(client).model_copy(update={"chatbot_count": 0})


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: uuid.UUID,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    client = await session.get(HubClient, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        )
    await session.execute(sql_delete(HubClient).where(HubClient.id == client_id))
    await session.commit()
