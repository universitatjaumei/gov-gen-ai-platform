"""
Deploy: cloud
Módulo: plataforma — catálogo de la plataforma, no de un módulo.

**SEC.9.1**: este router no tenía ninguna dependencia de identidad. La visibilidad la decidían
`X-Client-Id`, `X-Partner-Id` y `X-Client-Groups` —cabeceras que pone quien llama—, así que
bastaba declarar el id del dueño para descargar el código de la automatización de otra
organización; `POST /push` publicaba un artefacto arbitrario **y el servidor lo firmaba** con la
clave de la plataforma, y `POST /sign_manifest` era un oráculo de firma abierto.

Ahora la tenencia **sale del token** y firmar es cosa del superadministrador. La guarda se declara
en el `APIRouter` y no en el docstring: el inventario de PLAT.5 se validaba leyendo docstrings y
este fichero decía «Módulo: plataforma» estando abierto de par en par.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.api.deps import get_session, require_module, require_role
from server.app.core.auth.models import UserInfo
from server.app.services.library_service import LibraryService
from server.app.services.manifest_signature_service import (
    manifest_signature_service,
    SignatureConfigError,
)
from automatia_shared.dtos import AutomationBlueprintDTO

logger = logging.getLogger(__name__)

# La guarda del router: identidad + módulo de plataforma para TODOS los endpoints. Los dos que
# firman suben además a superadministrador, en su propia dependencia.
router = APIRouter(
    prefix="/v1/library",
    tags=["library"],
    dependencies=[Depends(require_module("plataforma"))],
)

_require_admin = require_role("superadmin", "admin")
_require_superadmin = require_role("superadmin")


async def get_service(session: AsyncSession = Depends(get_session)) -> LibraryService:
    return LibraryService(session)


@router.get("/manifest")
async def get_manifest(
    user: UserInfo = Depends(_require_admin),
    service: LibraryService = Depends(get_service),
):
    """Catálogo visible para quien pregunta, acotado por las organizaciones de su token."""
    items = await service.get_visible_automations(
        client_ids=user.organizacion_ids,
        client_groups=user.saml_groups,
        is_superadmin=user.is_superadmin,
    )

    return [
        {
            "id": item.id,
            "name": item.name,
            "version": item.version,
            "updated_at": item.updated_at,
            "is_workflow": item.is_workflow,
        }
        for item in items
    ]


@router.get("/download/{item_id}", response_model=AutomationBlueprintDTO)
async def download_automation(
    item_id: str,
    user: UserInfo = Depends(_require_admin),
    service: LibraryService = Depends(get_service),
):
    item = await service.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Automation not found")

    # La visibilidad se resuelve con la MISMA consulta que el manifiesto: si se comprobara
    # aquí a mano, las dos reglas se separarían en cuanto una de las dos cambiara.
    visible = await service.get_visible_automations(
        client_ids=user.organizacion_ids,
        client_groups=user.saml_groups,
        is_superadmin=user.is_superadmin,
    )

    if not any(v.id == item_id for v in visible):
        raise HTTPException(status_code=403, detail="Access denied to this automation")

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
    dto: AutomationBlueprintDTO,
    _: UserInfo = Depends(_require_superadmin),
    service: LibraryService = Depends(get_service),
):
    """
    Publica una automatización en la biblioteca central.

    El servidor firma el manifiesto con la clave de la plataforma antes de persistirlo, así que
    **es un acto de la plataforma**: sólo el superadministrador. Abierto, era inyección firmada
    en la cadena de suministro — cualquiera dejaba un artefacto distribuible y con firma válida.
    """
    data = dto.model_dump()

    # Map DTO to Model (DTO has metadata dict, model has metadata_json)
    if "metadata" in data:
        data["metadata_json"] = data.pop("metadata")

    signable_data = manifest_signature_service.get_signable_fields(data)

    try:
        signature = manifest_signature_service.sign_manifest(signable_data)
        if signature:
            data["signature"] = signature
            logger.info("Manifiesto firmado exitosamente: %s", data.get("id"))
        else:
            # Servicio no configurado - continuar sin firma (modo desarrollo)
            logger.warning(
                "Manifiesto guardado sin firma (servicio no configurado): %s",
                data.get("id"),
            )
    except SignatureConfigError as e:
        logger.error("Error de configuración al firmar: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Error de configuración del servicio de firmas. Contacte al administrador.",
        )
    except Exception as e:
        logger.error("Error inesperado al firmar manifiesto: %s", e)
        raise HTTPException(
            status_code=500, detail="Error interno al procesar la firma del manifiesto."
        )

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
async def sign_manifest(
    request: SignManifestRequest,
    _: UserInfo = Depends(_require_superadmin),
):
    """
    Firma un manifiesto con la clave de la plataforma, sin persistir el artefacto (distribución
    P2P o validación previa).

    **Sólo superadministrador**: sin guarda, esto era un oráculo de firma — se le pasaba un JSON
    arbitrario y devolvía su firma RSA-SHA256 hecha con `AUTOMATIA_SIGNING_KEY`.

    `partner_id` sigue viniendo del cuerpo **a propósito**: es a quién va destinado el artefacto,
    no quién firma. Quien firma es la plataforma, y eso ya lo garantiza la guarda; derivarlo del
    actor exigiría una dimensión de *partner* en el principal que no existe desde ROL.1.
    """
    import json

    try:
        manifest_dict = json.loads(request.manifest_json)

        if "id" not in manifest_dict:
            raise ValueError("Manifiesto debe contener 'id'")

        # La firma vincula el contenido al destinatario declarado.
        manifest_dict["partner_id"] = request.partner_id

        signable_data = manifest_signature_service.get_signable_fields(manifest_dict)

        signature = manifest_signature_service.sign_manifest(signable_data)

        if not signature:
            return {"signature": None, "algorithm": None}

        return {
            "signature": signature,
            "algorithm": "RSA-SHA256",
            "key_id": "default",
            "partner_id": request.partner_id,
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in manifest_json")
    except SignatureConfigError as e:
        logger.error("Error configuration signing: %s", e)
        raise HTTPException(
            status_code=500, detail="Signature service configuration error"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error signing manifest: %s", e)
        raise HTTPException(status_code=500, detail="Error interno al firmar el manifiesto")
