"""Las dos normalizaciones de identidad que comparten la autenticación y los routers (AIS.3).

**Por qué existe este fichero.** `core/` importaba estas dos funciones **de `routers/`**:

- `core/auth/saml/identity_service.py` traía `normalizar_correo` de `routers/hub_users_router.py`.
- `core/auth/modulos_service.py` traía `user_to_uuid` de `routers/redaccion/_actor.py`.

O sea que la capa de autenticación dependía de la capa HTTP de un módulo, que es la jerarquía al
revés. Y no era teórico: `core/` es justamente la capa que un fork no querría tocar, así que
arrastrar `routers.redaccion` desde ella convierte cualquier cambio en el router de un módulo en
un cambio potencial de la autenticación de todos.

Las dos son **decisiones de identidad**, no utilidades de presentación, y por eso su sitio es
`core`: si las dos formas de normalizar se separan, dos filas que son la misma persona dejan de
serlo, y eso no lo nota nadie hasta que alguien pierde sus permisos.
"""
from __future__ import annotations

import uuid


def normalizar_correo(correo: str) -> str:
    """La forma canónica de un correo, para guardarlo y para buscarlo.

    La comparten el alta manual de personas y el ACS de SAML. Si se separan, `Fabra@Ejemplo.org`
    dado de alta a mano y `fabra@ejemplo.org` que llega del IdP dejan de ser la misma persona, y
    el alta manual se convierte en una fila muerta que nadie relaciona con nadie.
    """
    return correo.strip().lower()


def user_to_uuid(user_id: str) -> uuid.UUID:
    """El `user_id` del token como UUID, sea o no un UUID de origen.

    Los identificadores de sujeto no son homogéneos —hay UUID reales, correos y claves de
    partner—, y varias tablas necesitan una clave UUID (`updated_by`, `owner_id`, el sujeto de
    una concesión). `uuid5` sobre el mismo espacio de nombres es **determinista**: el mismo
    `user_id` da siempre el mismo UUID, que es lo que permite que una fila escrita hoy siga
    reconociéndose mañana. Un `uuid4` de reserva habría creado un sujeto nuevo en cada petición.
    """
    try:
        return uuid.UUID(user_id)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
