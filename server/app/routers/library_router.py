"""
Deploy: cloud
"""

from typing import Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.services.library_service import LibraryService
from server.app.services.manifest_signature_service import (
    manifest_signature_service,
    SignatureConfigError,
)
from automatia_shared.dtos import AutomationBlueprintDTO

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/library", tags=["library"])


async def get_session() -> AsyncSession:
    async with AsyncSession(server_engine) as session:
        yield session


async def get_service(session: AsyncSession = Depends(get_session)) -> LibraryService:
    return LibraryService(session)


@router.get("/manifest")
async def get_manifest(
    x_client_id: Optional[str] = Header(None),
    x_partner_id: Optional[str] = Header(None),
    x_client_groups: Optional[str] = Header("[]"),  # JSON string list
    service: LibraryService = Depends(get_service),
):
    import json

    try:
        groups = json.loads(x_client_groups)
    except Exception:
        groups = []

    items = await service.get_visible_automations(
        client_id=x_client_id, partner_id=x_partner_id, client_groups=groups
    )

    # Return lightweight manifest
    manifest = []
    for item in items:
        manifest.append(
            {
                "id": item.id,
                "name": item.name,
                "version": item.version,
                "updated_at": item.updated_at,
                "is_workflow": item.is_workflow,
            }
        )
    return manifest


@router.get("/download/{item_id}", response_model=AutomationBlueprintDTO)
async def download_automation(
    item_id: str,
    x_client_id: Optional[str] = Header(None),
    x_partner_id: Optional[str] = Header(None),
    x_client_groups: Optional[str] = Header("[]"),
    service: LibraryService = Depends(get_service),
):
    # Retrieve item
    item = await service.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Automation not found")

    # Verify access (Re-use logic or check returned list)
    # Ideally reuse get_visible_automations to ensure security policies
    import json

    try:
        groups = json.loads(x_client_groups)
    except Exception:
        groups = []

    visible = await service.get_visible_automations(
        client_id=x_client_id, partner_id=x_partner_id, client_groups=groups
    )

    if not any(v.id == item_id for v in visible):
        raise HTTPException(status_code=403, detail="Access denied to this automation")

    # Map model to DTO
    return AutomationBlueprintDTO(
        id=item.id,
        name=item.name,
        type=item.type,
        code_content=item.code_content,
        version=item.version,
        updated_at=item.updated_at,
        client_id=item.client_id,
        partner_id=item.partner_id,
        is_system_template=item.is_system_template,
        signature=item.signature,
        access_groups=item.access_groups,
        is_workflow=item.is_workflow,
        metadata=item.metadata_json or {},
    )


@router.post("/push")
async def push_automation(
    dto: AutomationBlueprintDTO, service: LibraryService = Depends(get_service)
):
    """
    Publica una automatización en la biblioteca central.

    El servidor firma automáticamente el manifiesto con la clave del Partner/Sistema
    antes de persistirlo, garantizando la integridad del contenido distribuido.
    """
    data = dto.model_dump()

    # Map DTO to Model (DTO has metadata dict, model has metadata_json)
    if "metadata" in data:
        data["metadata_json"] = data.pop("metadata")

    # --- FIRMA DEL MANIFIESTO ---
    # Extraer campos relevantes para la firma (excluir metadatos volátiles)
    signable_data = manifest_signature_service.get_signable_fields(data)

    try:
        signature = manifest_signature_service.sign_manifest(signable_data)
        if signature:
            data["signature"] = signature
            logger.info(f"Manifiesto firmado exitosamente: {data.get('id')}")
        else:
            # Servicio no configurado - continuar sin firma (modo desarrollo)
            logger.warning(
                f"Manifiesto guardado sin firma (servicio no configurado): {data.get('id')}"
            )
    except SignatureConfigError as e:
        logger.error(f"Error de configuración al firmar: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error de configuración del servicio de firmas. Contacte al administrador.",
        )
    except Exception as e:
        logger.error(f"Error inesperado al firmar manifiesto: {e}")
        raise HTTPException(
            status_code=500, detail="Error interno al procesar la firma del manifiesto."
        )
    # --- FIN FIRMA ---

    saved = await service.save_master(data)

    return {
        "status": "success",
        "id": saved.id,
        "version": saved.version,
        "signed": data.get("signature") is not None,
    }


class SignManifestRequest(BaseModel):
    manifest_json: str
    partner_id: str


@router.post("/sign_manifest")
async def sign_manifest(request: SignManifestRequest):
    """
    Firma un manifiesto usando la clave privada del partner/sistema.
    Este endpoint se usa para obtener una firma sin necesariamente guardar
    el artefacto completo en la librería (útil para distribución P2P o validación previa).
    """
    import json

    try:
        manifest_dict = json.loads(request.manifest_json)

        # Validar consistencia básica
        if "id" not in manifest_dict:
            raise ValueError("Manifiesto debe contener 'id'")

        # Inyectar partner_id en el manifiesto para la firma si no está o es distinto
        # (La firma vincula el contenido al partner que firma)
        manifest_dict["partner_id"] = request.partner_id

        # Obtener campos firmables
        signable_data = manifest_signature_service.get_signable_fields(manifest_dict)

        signature = manifest_signature_service.sign_manifest(signable_data)

        if not signature:
            return {"signature": None, "algorithm": None}

        return {
            "signature": signature,
            "algorithm": "RSA-SHA256",
            "key_id": "default",  # TODO: Support multiple keys
            "partner_id": request.partner_id,
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in manifest_json")
    except SignatureConfigError as e:
        logger.error(f"Error configuration signing: {e}")
        raise HTTPException(
            status_code=500, detail="Signature service configuration error"
        )
    except Exception as e:
        logger.error(f"Error signing manifest: {e}")
        raise HTTPException(status_code=500, detail=str(e))
