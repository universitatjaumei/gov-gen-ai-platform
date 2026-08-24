"""`_get_workspace` debe reconocer al propietario aunque su `user_id` no sea un UUID.

Hallazgo de la verificación manual del Camino 3 de MAN.2 (2026-08-14): SuperAdmin y Admin
de desarrollo tienen `user_id` no-UUID (`"1"`, `"admin_dev"`); `HubWorkspace.owner_id` se
escribe con `user_to_uuid(user.user_id)` (ver `_actor.py`), pero `_get_workspace` compara
`str(workspace.owner_id) != user.user_id` — comparación literal contra el `user_id` crudo,
que nunca coincide con el uuid5 guardado. **El propio dueño de un workspace recibe 403 en
los seis endpoints que dependen de `_get_workspace`** (transición de bloques, subida de
inputs, ejecución, preview...). `es_propietario` en `_actor.py` ya existe justo para este
caso — lo usa `hub_redaccion_router.py` para la revisión de bloques — pero
`workspaces_router.py` no lo adoptó.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
    HubWorkspace,
)
from server.app.routers.redaccion._actor import user_to_uuid
from server.app.routers.redaccion.workspaces_router import _get_workspace


async def _plantilla_version(session) -> uuid.UUID:
    """Plantilla + versión mínimas para satisfacer la FK de `HubWorkspace`."""
    template = HubReportTemplate(
        name="Plantilla de prueba",
        report_profile="GENERIC_REPORT",
        owner_kind="platform",
    )
    session.add(template)
    await session.flush()

    version = HubReportTemplateVersion(
        template_id=template.id,
        version=1,
        spec_json={},
        created_by=uuid.uuid4(),
    )
    session.add(version)
    await session.flush()
    return version.id


async def test_superadmin_de_desarrollo_es_dueno_de_su_propio_workspace(db_url):
    """user_id="1" (SuperAdmin dev) debe poder leer un workspace que él mismo creó."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            user = UserInfo(user_id="1", email="fabra@uji.es", role="superadmin")
            version_id = await _plantilla_version(session)

            workspace = HubWorkspace(
                template_version_id=version_id,
                owner_id=user_to_uuid(user.user_id),
                status="draft",
            )
            session.add(workspace)
            await session.flush()
            workspace_id = workspace.id
            await session.commit()

            result = await _get_workspace(workspace_id, user, session)

            assert result.id == workspace_id
    finally:
        await engine.dispose()


async def test_otro_usuario_sigue_sin_poder_leer_el_workspace_ajeno(db_url):
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            owner = UserInfo(user_id="1", email="fabra@uji.es", role="superadmin")
            intruso = UserInfo(user_id="2", email="otro@uji.es", role="superadmin")
            version_id = await _plantilla_version(session)

            workspace = HubWorkspace(
                template_version_id=version_id,
                owner_id=user_to_uuid(owner.user_id),
                status="draft",
            )
            session.add(workspace)
            await session.flush()
            workspace_id = workspace.id
            await session.commit()

            with pytest.raises(HTTPException) as exc_info:
                await _get_workspace(workspace_id, intruso, session)

            assert exc_info.value.status_code == 403
    finally:
        await engine.dispose()
