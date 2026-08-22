"""
Deploy: cloud

Service Provider SAML 2.0 (AUTH.1): inicia el login contra el IdP institucional,
consume la respuesta firmada (ACS) y publica la metadata del SP. La emisión del JWT
de sesión y el provisioning de la identidad llegan en AUTH.2.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse, Response

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings

from server.app.api.deps import get_session
from server.app.core.auth import create_token
from server.app.core.auth.saml import (
    InvalidSamlConfigError,
    build_saml_settings,
    prepare_saml_request,
)
from server.app.core.auth.saml.identity_service import (
    SamlIdentityService,
    SamlMissingEmailError,
    SamlUserInactiveError,
)
from server.app.core.config import get_settings

router = APIRouter(prefix="/auth/saml", tags=["auth-saml"])


def _ensure_enabled() -> None:
    if not get_settings().saml_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SAML SSO is not enabled",
        )


async def _build_auth(request: Request) -> OneLogin_Saml2_Auth:
    req = await prepare_saml_request(request)
    return OneLogin_Saml2_Auth(req, build_saml_settings())


@router.get("/login")
async def saml_login(request: Request, relay_state: str | None = None):
    """Redirige (302) al IdP con el AuthnRequest."""
    _ensure_enabled()
    auth = await _build_auth(request)
    return RedirectResponse(url=auth.login(return_to=relay_state), status_code=302)


@router.post("/acs")
async def saml_acs(request: Request, session=Depends(get_session)):
    """Assertion Consumer Service: valida la aserción, resuelve la identidad y emite JWT."""
    _ensure_enabled()
    auth = await _build_auth(request)

    try:
        auth.process_response()
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de parseo => 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "SAML_VALIDATION_FAILED", "reason": str(exc)},
        )

    errors = auth.get_errors()
    if errors:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "SAML_VALIDATION_FAILED",
                "errors": errors,
                "reason": auth.get_last_error_reason(),
            },
        )
    if not auth.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "SAML_NOT_AUTHENTICATED"},
        )

    identity = SamlIdentityService(session)
    try:
        user_info = await identity.resolve_session(
            auth.get_nameid(), auth.get_attributes()
        )
    except SamlMissingEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "SAML_MISSING_EMAIL", "reason": str(exc)},
        )
    except SamlUserInactiveError as exc:
        # 403 y no 401: el IdP la autenticó bien, es esta plataforma la que no la deja pasar.
        # Con un 401 quien lo vea buscará el fallo en el IdP, que es donde no está.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_INACTIVE", "reason": str(exc)},
        )

    token = create_token(user_info)
    return_url = get_settings().saml_frontend_return_url
    if not return_url:
        # Sin frontend configurado (p. ej. clientes API): devolver el token directamente.
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user_info.to_dict(),
        }
    # El token viaja en el fragment para no quedar registrado en logs de servidor/proxy.
    return RedirectResponse(url=f"{return_url}#token={token}", status_code=302)


@router.get("/metadata")
async def saml_metadata():
    """Publica la metadata XML del SP."""
    _ensure_enabled()
    try:
        saml_settings = OneLogin_Saml2_Settings(
            build_saml_settings(sp_only=True), sp_validation_only=True
        )
    except InvalidSamlConfigError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    metadata = saml_settings.get_sp_metadata()
    errors = saml_settings.validate_metadata(metadata)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_SP_METADATA", "errors": errors},
        )
    return Response(content=metadata, media_type="application/xml")


@router.get("/logout")
async def saml_logout(request: Request):
    """Inicia el Single Logout si el SP tiene SLS configurado (stub mínimo)."""
    _ensure_enabled()
    if not get_settings().saml_sp_sls_url:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Single Logout (SLO) is not configured (SAML_SP_SLS_URL)",
        )
    auth = await _build_auth(request)
    return RedirectResponse(url=auth.logout(), status_code=302)
