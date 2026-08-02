"""Autorización de acceso a un chatbot (SEC.2.1, Parte 1). Deploy: shared.

SEC.2 cerró el paso **entre** organizaciones. Dentro de una, todos los chatbots seguían
igual de accesibles: `is_active` dice si un chatbot funciona, no para quién. Un chatbot de
gestión interna era tan alcanzable como el que se publica en la web.

`assert_chatbot_access` es el **único** sitio donde se decide, y eso es la mitad del valor.
Repartir la decisión por el chat, el adaptador compatible-OpenAI y el endpoint del widget
garantizaría que los tres se separan: es el mismo razonamiento por el que la tenencia vive
en `tenancy.py` y no en cada endpoint.

Dos cosas que se leen mal si no están dichas:

- **`via` manda sobre la identidad.** Una API key de widget identifica un *sitio*, no a una
  persona, así que no abre un chatbot `authenticated` ni acompañada de un actor con permisos.
  El comodín del superadmin es de identidad; por ese canal no llega ninguna.
- **`restricted` con las dos listas vacías es «nadie», no «todos».** La lectura contraria
  —«no hay restricción declarada, luego no restrinjo»— convierte un descuido de
  configuración en un chatbot abierto, que es justo lo que este módulo viene a evitar.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from server.app.core.auth.delegated_actor import EffectiveActor

PUBLIC_ANON = "public_anon"
AUTHENTICATED = "authenticated"
RESTRICTED = "restricted"

MODOS = (PUBLIC_ANON, AUTHENTICATED, RESTRICTED)

VIA_SESION = "session"
VIA_WIDGET = "widget_api_key"


def _prohibido(motivo: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "ACCESS_MODE_FORBIDDEN", "reason": motivo},
    )


def _pertenece_a_la_organizacion(actor: EffectiveActor, organizacion_id) -> bool:
    from server.app.core.auth.tenancy import puede_acceder

    return puede_acceder(actor, organizacion_id)


def assert_chatbot_access(
    actor: EffectiveActor | None, chatbot, *, via: str
) -> None:
    """403 si este actor no puede conversar con este chatbot por esta vía.

    `chatbot` es cualquier cosa con `access_mode`, `organizacion_id`, `allowed_roles` y
    `allowed_saml_groups`: se tipa por atributos y no por clase para que el endpoint del
    widget (D.1) pueda pasar una proyección sin arrastrar el ORM.
    """
    modo = getattr(chatbot, "access_mode", None)
    if modo not in MODOS:
        # Un modo desconocido no se interpreta. Pasa si la BD trae un valor que este
        # despliegue todavía no entiende, y adivinar sería adivinar a favor del atacante.
        raise _prohibido(f"unknown access mode '{modo}'")

    if modo == PUBLIC_ANON:
        return

    if via == VIA_WIDGET:
        raise _prohibido(
            "the widget API key identifies a site, not a person: it cannot open a "
            f"chatbot in '{modo}' mode"
        )

    if actor is None:
        raise _prohibido("this chatbot requires an authenticated actor")

    if actor.is_superadmin:
        return

    if not _pertenece_a_la_organizacion(actor, chatbot.organizacion_id):
        raise _prohibido("the actor does not belong to this chatbot's organization")

    if modo == AUTHENTICATED:
        return

    roles = tuple(getattr(chatbot, "allowed_roles", None) or ())
    grupos = tuple(getattr(chatbot, "allowed_saml_groups", None) or ())

    if actor.role in roles:
        return
    if set(actor.saml_groups) & set(grupos):
        return

    raise _prohibido(
        "restricted chatbot: the actor holds neither an allowed role nor an allowed group"
    )
