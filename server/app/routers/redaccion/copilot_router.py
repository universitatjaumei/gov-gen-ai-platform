"""Router del Copilot del DrawerHub.

Deploy: edge — el copilot consume LLM + embeddings + factories del módulo redacción.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
from server.app.modules.agents_hub.services.embedding_resolver import (
    resolve_embedding_service,
)
from server.app.modules.agents_hub.services.model_factory import get_model_for_tier
from server.app.modules.redaccion.services.copilot import (
    CopilotAnswer,
    CopilotAskRequest,
    CopilotService,
    CopilotTranslateRequest,
    CopilotTranslateResponse,
)
from server.app.modules.redaccion.services.copilot.docs_retriever import DocsRetriever


router = APIRouter(prefix="/redaccion/copilot", tags=["redaccion-copilot"])

#: El **retriever** se conserva entre peticiones, no el servicio entero: es donde vive el
#: índice, y uno nuevo por petición volvería a embeber los ~387 fragmentos de `docs/` en cada
#: pregunta. El servicio sí se construye cada vez, para que cambiar el modelo en el panel tenga
#: efecto sin reiniciar. El índice es de la documentación del proyecto, que no cambia sin un
#: despliegue; si algún día hace falta invalidarlo en caliente, será otro prompt.
_retriever: DocsRetriever | None = None


async def get_copilot_service(
    session: AsyncSession = Depends(get_session),
) -> CopilotService:
    """El copiloto con su modelo y su servicio de embeddings (PRO.6).

    Era un stub que devolvía 503 siempre, así que el panel no tenía a quién preguntar.

    El 503 dice **cuál de los dos falta**: un modelo y un servicio de embeddings son dos
    configuraciones distintas, en dos pantallas distintas, y «copilot service not configured»
    obliga a mirar el log del servidor para saber cuál mirar.
    """
    global _retriever

    try:
        modelo = await get_model_for_tier(1, LocalConfigProvider(session))
    except Exception as fallo:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "El copiloto no tiene modelo de conversación configurado (nivel 1). "
                f"Asígnale uno en Modelos IA ({fallo})."
            ),
        ) from fallo

    if _retriever is None:
        try:
            embeddings = await resolve_embedding_service(session)
        except Exception as fallo:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "El copiloto no tiene servicio de embeddings: sin él no puede buscar en "
                    f"la documentación. Configúralo en Modelos IA ({fallo})."
                ),
            ) from fallo
        _retriever = DocsRetriever(embedding_service=embeddings)

    return CopilotService(llm=modelo, retriever=_retriever)


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
