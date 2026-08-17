"""Actor -> UUID para columnas de propiedad (owner_id/created_by) en redaccion.

SuperAdmin y Admin no tienen identidad UUID nativa (SuperAdminAccount.admin_id es int,
AdminAccount.partner_id es texto libre): uuid.UUID(user_id) revienta con ValueError para
ellos. uuid5 da una UUID determinista y estable por user_id sin tocar el esquema de
identidad ni requerir migracion.
"""
from __future__ import annotations

import uuid


def user_to_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, user_id)


def nombre_del_modelo(modelo) -> str:
    """El nombre del modelo, se llame como se llame el atributo en cada cliente.

    Se guarda en la plantilla propuesta y en cada bloque redactado (`model_used`), que es lo
    que permite saber con qué modelo se escribió un informe meses después. `ChatGoogleGenerativeAI`
    lo expone como `model` y no como `model_name`, así que mirar solo uno dejaba «desconocido»
    escrito en la pantalla y en el manifiesto.
    """
    for atributo in ("model_name", "model"):
        valor = getattr(modelo, atributo, None)
        if isinstance(valor, str) and valor:
            return valor
    return "desconocido"


def es_propietario(user_id: str, owner_id) -> bool:
    """¿Este `user_id` es el dueño de una fila con este `owner_id`?

    Admite las dos formas en que la propiedad quedó escrita: el `user_id` tal cual y su
    uuid5 determinista. SEC.8.1 la necesita porque varios endpoints de redacción recibían
    el usuario y **no lo miraban** —el parámetro estaba declarado y sin usar—, así que
    cualquiera con el UUID leía el contenido del workspace ajeno.
    """
    if owner_id is None:
        return False
    return str(owner_id) in (str(user_id), str(user_to_uuid(user_id)))
