from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel
from server.app.services.ai_brain import AIBrainService

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

class VerifyPartnerTokenRequest(BaseModel):
    token: str

@router.post("/verify_partner_token")
async def verify_partner_token(
    request: VerifyPartnerTokenRequest
):
    """
    Verifica un token de socio (Partner).
    De momento, valida que sea una licencia activa válida.
    """
    brain_service = AIBrainService()
    try:
        # Reutilizamos la lógica de validación de licencia
        # Asumiendo que el token es una clave de licencia válida
        license_obj = await brain_service._validate_license(request.token)
        
        # Opcional: Verificar si la licencia pertenece a un Partner
        # if not license_obj.partner_id:
        #     raise ValueError("Licencia no asociada a un partner")
            
        return {"valid": True, "partner_id": license_obj.partner_id}
        
    except ValueError as e:
        # Retornamos false en lugar de error 401 para este endpoint específico
        # si es lo que espera el cliente (booleano), pero el cliente espera JSON
        return {"valid": False, "error": str(e)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
