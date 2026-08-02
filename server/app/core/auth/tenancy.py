"""Frontera entre organizaciones (SEC.2, hallazgo A2). Deploy: shared.

**Una sola capa, no una comprobación repetida en cada endpoint.** El hallazgo A2 no fue que a
un endpoint se le olvidara filtrar: fue que no había dónde hacerlo, así que ninguno filtraba.
Repartir la regla por veinte sitios habría reproducido el problema en cuanto se añadiera el
veintiuno; concentrarla aquí hace que el endpoint nuevo tenga que decidir explícitamente
saltársela, y eso se ve en una revisión.

Dos operaciones, y hacen falta las dos:

- `assert_org_access` para el acceso **a una entidad concreta** que ya se ha leído.
- `scope_query_to_orgs` para los **listados**, donde comprobar después de leer no vale:
  filtrar en memoria tras un `LIMIT` deja fuera resultados propios y sigue trayendo ajenos a
  la memoria del proceso.

**El vacío significa lo contrario según el rol.** En un superadmin es el comodín «todas»; en
cualquier otro es «ninguna». Es la asimetría de la que depende todo el módulo, y por eso está
en un test: si «vacío = todas» valiera para cualquiera, olvidarse de poblar el claim
devolvería el acceso horizontal sin que nada fallara.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status

from server.app.core.auth.models import UserInfo


def _principal(sujeto: Any) -> UserInfo:
    """Acepta un `UserInfo` o cualquier cosa que lo lleve dentro, como `PatPrincipal`."""
    return getattr(sujeto, "user_info", sujeto)


def puede_acceder(sujeto: Any, organizacion_id: Any) -> bool:
    """¿Este principal puede tocar datos de esta organización?"""
    principal = _principal(sujeto)
    if getattr(principal, "is_superadmin", False):
        return True
    if organizacion_id is None:
        # Sin organización no hay forma de decidir, y no decidir es dejar pasar.
        return False
    return str(organizacion_id) in principal.organizacion_ids


def assert_org_access(sujeto: Any, organizacion_id: Any) -> None:
    """403 si el principal no gestiona esa organización. El superadmin siempre pasa.

    Es **403 y no 404**: quien ha llegado hasta aquí está autenticado y el recurso existe;
    fingir que no existe complicaría la depuración sin ocultar gran cosa, porque los ids son
    UUID y no se adivinan.
    """
    if not puede_acceder(sujeto, organizacion_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a los datos de esta organización",
        )


def orgs_del_principal(sujeto: Any) -> tuple[uuid.UUID, ...]:
    """Los ids como UUID, descartando los que no lo sean en vez de reventar la consulta."""
    principal = _principal(sujeto)
    validos: list[uuid.UUID] = []
    for bruto in principal.organizacion_ids:
        try:
            validos.append(uuid.UUID(str(bruto)))
        except (ValueError, AttributeError, TypeError):
            continue
    return tuple(validos)


def scope_query_to_orgs(stmt, sujeto: Any, model, columna: str = "organizacion_id"):
    """Acota un SELECT a las organizaciones del principal. El superadmin no se acota.

    Un principal **sin** organizaciones recibe un `IN ()` vacío, que no devuelve nada. Es
    intencionado y es la diferencia entre «no ve nada» y «no se filtra»: devolver el listado
    entero cuando el claim viene vacío es el hallazgo A2 otra vez.
    """
    principal = _principal(sujeto)
    if getattr(principal, "is_superadmin", False):
        return stmt
    return stmt.where(getattr(model, columna).in_(orgs_del_principal(principal)))
