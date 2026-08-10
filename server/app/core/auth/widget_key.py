"""Credencial de sitio para el widget público (SEC.8.5). Deploy: shared.

El widget embebía `data-token` con un JWT de sesión o un PAT completo. Está en el HTML de
la página, así que lo lee cualquiera, y como los endpoints lo resolvían como `via="session"`
arrastraba el rol y las organizaciones de su dueño: una credencial pensada para pintar un
chat abierto servía para entrar en el panel.

Esta es la credencial que faltaba. Deliberadamente **no** es un token de identidad: no lleva
rol, ni organizaciones, ni caducidad corta que renovar. Dice «soy el sitio X» y con eso solo
se puede hablar con el chatbot al que pertenece, y solo si ese chatbot es `public_anon` —lo
decide `assert_chatbot_access` con `via=VIA_WIDGET`, que ya existía desde SEC.2.1 sin nadie
que lo llamara—.

Se guarda con SHA-256 y se compara en tiempo constante, mismo tratamiento que un PAT: lo que
hay en la BD no sirve para autenticarse si alguien la lee.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

_BYTES_DE_CLAVE = 32
CABECERA = "X-Widget-Key"


def generar_clave() -> str:
    """Clave nueva en claro. Solo se ve una vez: lo que se persiste es su hash."""
    return secrets.token_urlsafe(_BYTES_DE_CLAVE)


def hash_de_clave(clave: str) -> str:
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()


def actor_anonimo_de_widget(chatbot_id: uuid.UUID):
    """El actor que representa «el público de este chatbot».

    No es una persona y no pretende serlo: sin rol, sin organizaciones y sin grupos, así
    que no abre nada por identidad. Existe porque el límite de peticiones y la cuota de
    SEC.4 se cuentan **por actor**, y sin un sujeto estable todo el tráfico anónimo de
    todos los chatbots compartiría cubo — el primer sitio con visitas dejaría sin servicio
    a los demás. Se acota al chatbot, que es la unidad que paga.
    """
    from server.app.core.auth.delegated_actor import EffectiveActor

    return EffectiveActor(
        subject_id=f"widget:{chatbot_id}",
        email="",
        role="anonymous",
        organizacion_ids=(),
        saml_groups=(),
        delegated=False,
    )


async def crear_widget_key(
    session, *, chatbot_id: uuid.UUID, name: str, created_by: str | None = None
):
    """Crea la credencial y devuelve `(clave_en_claro, fila)`.

    El plano se devuelve para enseñarlo una vez a quien la crea; no vuelve a estar
    disponible, porque en la fila solo queda el hash.
    """
    from server.app.modules.agents_hub.database.config_models import HubWidgetKey

    clave = generar_clave()
    fila = HubWidgetKey(
        id=uuid.uuid4(),
        chatbot_id=chatbot_id,
        name=name,
        key_hash=hash_de_clave(clave),
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
    )
    session.add(fila)
    await session.flush()
    return clave, fila


async def resolver_widget_key(session, clave: str | None):
    """La fila viva de esta clave, o `None`.

    Busca por hash —no por prefijo— porque el hash es la clave natural aquí: hay una fila
    por credencial y no hace falta desempatar. La comparación se hace igualmente en tiempo
    constante sobre la fila candidata: el índice acota, `compare_digest` decide.
    """
    if not clave:
        return None

    from server.app.modules.agents_hub.database.config_models import HubWidgetKey

    esperado = hash_de_clave(clave)
    filas = (
        await session.execute(
            select(HubWidgetKey).where(
                HubWidgetKey.key_hash == esperado,
                HubWidgetKey.revoked_at.is_(None),
            )
        )
    ).scalars().all()

    for fila in filas:
        if hmac.compare_digest(fila.key_hash, esperado):
            return fila
    return None
