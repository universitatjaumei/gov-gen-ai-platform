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


class ClientOut(BaseModel):
    id: uuid.UUID
    name: str
    partner_id: str
    theme_config: dict
    is_active: bool
    chatbot_count: int = 0
    created_at: datetime
    updated_at: datetime


class ClientCreate(BaseModel):
    name: str
    partner_id: str
    theme_config: dict = {}
    is_active: bool = True


class ClientUpdate(BaseModel):
    name: str | None = None
    partner_id: str | None = None
    theme_config: dict | None = None
    is_active: bool | None = None


_count_sq = (
    select(func.count(HubChatbot.id))
    .where(HubChatbot.client_id == HubClient.id)
    .correlate(HubClient)
    .scalar_subquery()
)


@router.get("", response_model=list[ClientOut])
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
        ClientOut(
            id=c.id,
            name=c.name,
            partner_id=c.partner_id,
            theme_config=c.theme_config,
            is_active=c.is_active,
            chatbot_count=count,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c, count in rows
    ]


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
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
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return ClientOut(
        id=client.id,
        name=client.name,
        partner_id=client.partner_id,
        theme_config=client.theme_config,
        is_active=client.is_active,
        chatbot_count=0,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


@router.patch("/{client_id}", response_model=ClientOut)
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
    return ClientOut(
        id=client.id,
        name=client.name,
        partner_id=client.partner_id,
        theme_config=client.theme_config,
        is_active=client.is_active,
        chatbot_count=0,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


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
