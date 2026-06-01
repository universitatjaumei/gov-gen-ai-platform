"""Router del Copilot del DrawerHub.

Deploy: edge — el copilot consume LLM + embeddings + factories del módulo redacción.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from server.app.api.deps import get_current_user
from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.services.copilot import (
    CopilotAnswer,
    CopilotAskRequest,
    CopilotService,
    CopilotTranslateRequest,
    CopilotTranslateResponse,
)


router = APIRouter(prefix="/redaccion/copilot", tags=["redaccion-copilot"])


async def get_copilot_service() -> CopilotService:
    """Stub. Se cablea cuando el motor LLM + embeddings + factories estén listos en runtime."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Copilot service not configured.",
    )


@router.post("/ask", response_model=CopilotAnswer)
async def ask_copilot(
    body: CopilotAskRequest,
    user: UserInfo = Depends(get_current_user),
    service: CopilotService = Depends(get_copilot_service),
) -> CopilotAnswer:
    """RAG sobre la documentación interna del módulo activo + síntesis LLM con citas."""
    return await service.answer(
        question=body.question,
        module=body.module,
        top_k=body.top_k,
    )


@router.post("/translate", response_model=CopilotTranslateResponse)
async def translate_copilot(
    body: CopilotTranslateRequest,
    user: UserInfo = Depends(get_current_user),
    service: CopilotService = Depends(get_copilot_service),
) -> CopilotTranslateResponse:
    """Traduce instrucción NL a configuración estructurada (chart / ETL / script)."""
    return await service.translate_nl_to_config(
        instruction=body.instruction,
        target_kind=body.target_kind,
        sample_schema=body.sample_schema,
    )
