"""CRUD de organizaciones del Hub.

Deploy: cloud
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select, delete as sql_delete

from server.app.api.deps import require_role
from server.app.core.auth.models import UserInfo
from server.app.core.auth.tenancy import assert_org_access, scope_query_to_orgs
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.config_models import HubChatbot, HubOrganizacion

router = APIRouter(prefix="/hub/organizaciones", tags=["hub-organizaciones"])

_require_admin = require_role("superadmin", "admin")


class OrganizacionRead(BaseModel):
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
    # VIS.2: None = heredar el default de plataforma (128.000 tokens)
    default_context_token_budget: int | None
    # RAG.8: troceado. None = heredar (1000 / 100 / 'structural')
    default_chunk_size: int | None
    default_chunk_overlap: int | None
    default_chunking_strategy: str | None
    # RAG.10: None = heredar el default de plataforma (False)
    default_query_rewriting_enabled: bool | None
    rewrite_llm_config_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizacionCreate(BaseModel):
    name: str
    partner_id: str
    theme_config: dict = {}
    is_active: bool = True
    default_public_graph_profile: str = "PUBLIC_KB_RICH"
    default_retrieval_mode: str = "RAG"
    default_language_mode: str = "prefer"
    default_quality_threshold: float = 0.6
    default_min_retrieval_results: int = 2
    default_min_retrieval_score: float = 0.0
    default_reranker_enabled: bool = False
    default_answer_template: str = "generic"
    default_context_token_budget: int | None = None
    default_chunk_size: int | None = None
    default_chunk_overlap: int | None = None
    default_chunking_strategy: str | None = None
    default_query_rewriting_enabled: bool | None = None
    rewrite_llm_config_id: uuid.UUID | None = None


class OrganizacionUpdate(BaseModel):
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
    default_context_token_budget: int | None = None
    default_chunk_size: int | None = None
    default_chunk_overlap: int | None = None
    default_chunking_strategy: str | None = None
    default_query_rewriting_enabled: bool | None = None
    rewrite_llm_config_id: uuid.UUID | None = None


_count_sq = (
    select(func.count(HubChatbot.id))
    .where(HubChatbot.organizacion_id == HubOrganizacion.id)
    .correlate(HubOrganizacion)
    .scalar_subquery()
)


@router.get("", response_model=list[OrganizacionRead])
async def list_organizaciones(
    user: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    # SEC.8.1: la organización ES la entidad, así que se acota por su propia clave y no
    # por una columna `organizacion_id` que aquí no existe.
    consulta = scope_query_to_orgs(
        select(HubOrganizacion, _count_sq.label("chatbot_count")),
        user,
        HubOrganizacion,
        columna="id",
    ).order_by(HubOrganizacion.created_at.desc())
    rows = (await session.execute(consulta)).all()
    return [
        OrganizacionRead.model_validate(o).model_copy(update={"chatbot_count": count})
        for o, count in rows
    ]


@router.post("", response_model=OrganizacionRead, status_code=status.HTTP_201_CREATED)
async def create_organizacion(
    body: OrganizacionCreate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    organizacion = HubOrganizacion(
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
        default_context_token_budget=body.default_context_token_budget,
        default_chunk_size=body.default_chunk_size,
        default_chunk_overlap=body.default_chunk_overlap,
        default_chunking_strategy=body.default_chunking_strategy,
        default_query_rewriting_enabled=body.default_query_rewriting_enabled,
        rewrite_llm_config_id=body.rewrite_llm_config_id,
    )
    session.add(organizacion)
    await session.commit()
    await session.refresh(organizacion)
    return OrganizacionRead.model_validate(organizacion).model_copy(
        update={"chatbot_count": 0}
    )


@router.patch("/{organizacion_id}", response_model=OrganizacionRead)
async def update_organizacion(
    organizacion_id: uuid.UUID,
    body: OrganizacionUpdate,
    user: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    organizacion = await session.get(HubOrganizacion, organizacion_id)
    if not organizacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organización not found"
        )
    assert_org_access(user, organizacion.id)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(organizacion, field, value)
    organizacion.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(organizacion)
    return OrganizacionRead.model_validate(organizacion).model_copy(
        update={"chatbot_count": 0}
    )


@router.delete("/{organizacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organizacion(
    organizacion_id: uuid.UUID,
    user: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    organizacion = await session.get(HubOrganizacion, organizacion_id)
    if not organizacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organización not found"
        )
    # El borrado arrastra los chatbots por CASCADE: sin esta línea, un admin destruye los
    # datos de otra administración con un solo DELETE.
    assert_org_access(user, organizacion.id)
    await session.execute(
        sql_delete(HubOrganizacion).where(HubOrganizacion.id == organizacion_id)
    )
    await session.commit()
