"""POST /hub/redaccion/templates contra una sesión real (no mockeada).

Hallazgo de la verificación manual del Camino 3 de MAN.2 (2026-08-14): crear una
plantilla desde `/redaccion/builder` da 500 siempre. Los tests existentes de este router
mockean la sesión (`AsyncMock`/`MagicMock`), que no reproduce el `expire_on_commit=True`
por defecto de SQLAlchemy — por eso nadie lo había detectado.

Causa: `create_template` construye `TemplateOut(current_version_id=version.id, ...)`
**después** de `await session.commit()`. El commit expira los atributos de todos los
objetos de la sesión, `version` incluido; el `session.refresh(template)` posterior solo
refresca `template`. Acceder a `version.id` dispara una recarga perezosa síncrona sobre
una `AsyncSession` de asyncpg, que revienta con `MissingGreenlet` en vez de con un 500
con traza — el guardarraíl de la ruta HTTP ni siquiera deja ver la causa real.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.core.auth.models import UserInfo
from server.app.routers.redaccion.hub_redaccion_router import (
    TemplateCreateIn,
    create_template,
)


async def test_create_template_no_expira_la_version_antes_de_leerla(db_url):
    """SuperAdmin de desarrollo (user_id no-UUID) crea una plantilla sin 500."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            user = UserInfo(user_id="1", email="admin@example.local", role="superadmin")

            result = await create_template(
                body=TemplateCreateIn(name="Plantilla de prueba Camino 3"),
                user=user,
                session=session,
            )

            assert result.name == "Plantilla de prueba Camino 3"
            assert result.current_version_id is not None
    finally:
        await engine.dispose()
