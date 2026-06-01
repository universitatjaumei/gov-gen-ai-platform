"""Router para operaciones de agentes sobre workspaces: exportación DOCX/ODT.

Deploy: edge
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from server.app.api.deps import get_current_user
from server.app.core.auth.models import UserInfo
from server.app.core.storage import StorageService, get_storage_service
from server.app.modules.agents_hub.services.export_service import ExportService

router = APIRouter(prefix="/hub/agents", tags=["hub-agents"])


class ExportRequest(BaseModel):
    format: Literal["docx", "odt"] = "docx"


class ExportOut(BaseModel):
    download_url: str
    file_path: str
    size_bytes: int


@router.post(
    "/workspaces/{workspace_id}/export",
    response_model=ExportOut,
    operation_id="exportAgentWorkspace",
    status_code=status.HTTP_200_OK,
)
async def export_agent_workspace(
    workspace_id: str,
    body: ExportRequest,
    user: UserInfo = Depends(get_current_user),
    storage: StorageService = Depends(get_storage_service),
) -> ExportOut:
    """Exporta el final_document de un workspace de agentes a DOCX u ODT.

    Requiere que el workspace tenga un final_document generado por el grafo LangGraph.
    Deploy: edge
    """
    from server.app.modules.agents_hub.database.connection import get_async_session
    from server.app.modules.agents_hub.database.operational_models import HubInteraction
    from sqlalchemy import select

    async for session in get_async_session():
        result = await session.execute(
            select(HubInteraction).where(
                HubInteraction.user_id == user.user_id,
            ).limit(1)
        )
        interaction = result.scalar_one_or_none()
        break

    if interaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No workspace found: {workspace_id}",
        )

    final_document = interaction.assistant_message or ""

    class _SimpleManifest:
        retrieved_chunks = []

    service = ExportService(storage=storage)
    export_result = await service.export(
        workspace_id=workspace_id,
        final_document=final_document,
        run_manifest=_SimpleManifest(),
        format=body.format,
        theme=None,
    )

    return ExportOut(
        download_url=export_result.download_url,
        file_path=export_result.file_path,
        size_bytes=export_result.size_bytes,
    )
