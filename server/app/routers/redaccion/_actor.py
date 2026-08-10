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
