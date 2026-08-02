"""Identidad delegada por cabecera firmada (SEC.2.1, Parte 2). Deploy: shared.

Un cliente de confianza —el Pipe de Open WebUI, en el piloto— habla con el backend con **un
PAT de servicio**. Sin nada más, el backend solo ve al dueño de ese PAT: todas las
conversaciones quedan atribuidas a una cuenta y la cuota por usuario de SEC.4 no puede
existir. La alternativa de emitir un PAT por persona se descartó en la planificación: no
escala a cientos de usuarios ni sobrevive a las bajas.

La cabecera `X-GovGenAI-Actor` es un JWT compacto que el cliente firma con un secreto
compartido, y dice **quién pregunta**. Tres reglas la mantienen honesta:

1. **Sin el scope `chat:onbehalf`, la cabecera se ignora en silencio.** No es un error: el
   actor efectivo pasa a ser el dueño del PAT. Un PAT robado que no lleve ese scope no
   suplanta a nadie, y quien emite el token decide caso por caso quién puede delegar.
2. **Las organizaciones salen del PAT, jamás de la cabecera.** Los grupos sí vienen de la
   cabecera, porque son lo que el IdP del cliente sabe y el backend no. La diferencia separa
   «el cliente aporta lo que sabe» de «el cliente se autoconcede permisos».
3. **Ventana corta.** Una cabecera con horas de validez es un PAT encubierto, revocable por
   nadie; el contrato la limita a cinco minutos.

HS256 con secreto compartido, y no RS256, porque hoy hay **un** cliente delegante. Cuando
haya más de uno, cada uno querrá su clave y su rotación: ahí RS256 se paga solo. Decisión
documentada, no implementada.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import jwt as pyjwt
from fastapi import HTTPException, status

from server.app.core.auth.models import UserInfo
from server.app.core.auth.pat.scopes import CHAT_ONBEHALF

CABECERA_ACTOR = "X-GovGenAI-Actor"
AUDIENCIA = "govgenai-backend"
VENTANA_MAXIMA_SEGUNDOS = 300


@dataclass(frozen=True)
class EffectiveActor:
    """Quién pregunta, de verdad.

    `delegated` distingue a la persona que llega por un cliente de confianza del propio
    principal autenticado. Lo consumen la autorización por chatbot y, cuando llegue, la
    contabilidad de SEC.4: sin este campo, «quién gastó la cuota» y «con qué credencial se
    entró» serían la misma pregunta, y no lo son.
    """

    subject_id: str
    email: str
    role: str
    organizacion_ids: tuple[str, ...]
    saml_groups: tuple[str, ...]
    delegated: bool

    @property
    def is_superadmin(self) -> bool:
        return self.role == "superadmin"

    @classmethod
    def desde_principal(cls, principal: UserInfo, **cambios) -> "EffectiveActor":
        base = dict(
            subject_id=principal.user_id,
            email=principal.email,
            role=principal.role,
            organizacion_ids=tuple(principal.organizacion_ids),
            saml_groups=tuple(principal.saml_groups),
            delegated=False,
        )
        base.update(cambios)
        return cls(**base)


def _rechazar(motivo: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "ACTOR_TOKEN_INVALID", "reason": motivo},
    )


def _leer_cabecera(request) -> str | None:
    headers = getattr(request, "headers", {}) or {}
    obtener = getattr(headers, "get", None)
    return obtener(CABECERA_ACTOR) if obtener else None


def resolve_effective_actor(request, principal: UserInfo) -> EffectiveActor:
    """Resuelve el actor efectivo de la petición.

    Sin cabecera, o con un principal que no puede delegar, el actor **es** el principal.
    Con cabecera y permiso para delegar, el actor es la persona que la cabecera declara,
    pero con las organizaciones del PAT.
    """
    cabecera = _leer_cabecera(request)
    if not cabecera:
        return EffectiveActor.desde_principal(principal)

    scopes = getattr(getattr(request, "state", None), "pat_scopes", None)
    # `None` es una sesión humana: no hay PAT, así que no hay delegación que valga. Y un PAT
    # sin el scope ignora la cabecera **sin protestar**, que es lo que la hace inútil para
    # quien robe el token.
    if scopes is None or CHAT_ONBEHALF not in scopes:
        return EffectiveActor.desde_principal(principal)

    secreto = os.environ.get("DELEGATED_ACTOR_SECRET")
    if not secreto:
        # No verificar la firma equivale a aceptar cualquiera. Si alguien manda la cabecera
        # contra un despliegue sin secreto, el fallo es de configuración y se dice.
        raise _rechazar("delegation is not configured on this deployment")

    try:
        payload = pyjwt.decode(
            cabecera,
            secreto,
            algorithms=["HS256"],
            audience=AUDIENCIA,
            options={"require": ["sub", "exp", "iat", "aud"]},
        )
    except pyjwt.PyJWTError as fallo:
        raise _rechazar(str(fallo)) from fallo

    if int(payload["exp"]) - int(payload["iat"]) > VENTANA_MAXIMA_SEGUNDOS:
        raise _rechazar(
            f"actor token window exceeds {VENTANA_MAXIMA_SEGUNDOS}s; it would be a "
            "non-revocable credential"
        )

    # Las organizaciones y el rol se heredan del PAT. Lo que la cabecera diga al respecto
    # —y puede decir lo que quiera— se descarta aquí, que es el punto anti-escalada de todo
    # el módulo: el cliente delegante identifica personas, no reparte permisos.
    return EffectiveActor.desde_principal(
        principal,
        subject_id=str(payload["sub"]),
        email=str(payload.get("email") or ""),
        saml_groups=tuple(str(g) for g in (payload.get("groups") or ())),
        delegated=True,
    )
