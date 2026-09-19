import pytest
from sqlmodel import SQLModel
from sqlmodel.pool import StaticPool

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

# Model + Service imports
from server.app.database.models import AutomationLibrary
from server.app.services.library_service import LibraryService
from automatia_shared.enums import AutomationType

@pytest.fixture(name="session")
async def session_fixture():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_partner_shared_items_are_not_visible_without_an_owner_org(session):
    """SEC.9.1 — la compartición por *partner* + `access_groups` deja de existir.

    Este test afirmaba lo contrario: que declarando `partner_id="p_master"` y el grupo
    `"Premium"` se veía el artefacto del partner. El problema no era la regla, era de dónde
    salían sus dos entradas — el router las leía de las cabeceras `X-Partner-Id` y
    `X-Client-Groups`, o sea del propio llamante, así que «pertenezco al grupo Premium» lo
    decidía quien pedía el fichero.

    Al pasar la tenencia al token, `partner_id` no tiene equivalente: ROL.1 lo retiró del
    principal. Se queda como columna del artefacto y **deja de conceder visibilidad**. Es un
    estrechamiento a propósito: nadie ve menos de lo suyo. Compartir configuración entre
    organizaciones se resuelve en MT.17–MT.21, con el criterio puesto por la plataforma.
    """
    premium_script = AutomationLibrary(
        id="prem-01",
        name="Premium Workflow",
        type=AutomationType.RPA_WEB,
        code_content="print('premium')",
        partner_id="p_master",
        access_groups=["Premium"], # stored as JSON
        is_workflow=True
    )
    propia = AutomationLibrary(
        id="mia-01",
        name="De mi organización",
        type=AutomationType.CUSTOM_SCRIPT,
        code_content="print('mia')",
        client_id="org-a",
    )
    session.add(premium_script)
    session.add(propia)
    await session.commit()

    service = LibraryService(session)

    # Declarar el grupo ya no abre nada: el artefacto no es de ninguna organización del actor.
    visible_con_grupo = await service.get_visible_automations(
        client_ids=["org-a"], client_groups=["Premium"]
    )
    assert [item.id for item in visible_con_grupo] == ["mia-01"]

    # Y sin organizaciones no se ve nada propio (sólo plantillas de sistema, que aquí no hay).
    visible_sin_orgs = await service.get_visible_automations(client_ids=[])
    assert visible_sin_orgs == []

@pytest.mark.asyncio
async def test_automation_integrity_on_retrieval(session):
    """Test GREEN: Verify signature and workflow flag integrity."""
    signed_wf = AutomationLibrary(
        id="wf-signed",
        name="Signed Process",
        type=AutomationType.WORKFLOW,
        code_content="{}",
        partner_id="p1",
        signature="sig_12345",
        is_workflow=True
    )
    session.add(signed_wf)
    await session.commit()

    service = LibraryService(session)
    res = await service.get_by_id("wf-signed")
    
    assert res.is_workflow is True
    assert res.signature == "sig_12345"

@pytest.mark.asyncio
async def test_superadmin_cross_partner_visibility(session):
    """Test superadmin visibility."""
    session.add(AutomationLibrary(id="s1", name="S1", type=AutomationType.CUSTOM_SCRIPT, partner_id="pA", code_content=""))
    session.add(AutomationLibrary(id="s2", name="S2", type=AutomationType.CUSTOM_SCRIPT, partner_id="pB", code_content=""))
    await session.commit()

    service = LibraryService(session)
    all_scripts = await service.get_visible_automations(
        client_ids=None, is_superadmin=True
    )
    
    assert len(all_scripts) == 2

@pytest.mark.asyncio
async def test_system_template_visibility(session):
    """Test system template propagation."""
    session.add(AutomationLibrary(
        id="sys-1", name="Global", type=AutomationType.CUSTOM_SCRIPT, 
        is_system_template=True, code_content=""
    ))
    await session.commit()

    service = LibraryService(session)
    # New client, no pattern, no groups
    visible = await service.get_visible_automations(
        client_ids=["new_c"], client_groups=[]
    )
    
    assert len(visible) == 1
    assert visible[0].is_system_template is True

@pytest.mark.asyncio
async def test_delete_automation_logic(session):
    """Test deletion logic."""
    # Partner creates item
    item = AutomationLibrary(
        id="del-1", name="To Delete", type=AutomationType.CUSTOM_SCRIPT,
        partner_id="p1", code_content=""
    )
    session.add(item)
    await session.commit()
    
    service = LibraryService(session)
    
    # Act: Delete
    result = await service.delete_automation("del-1", "p1")
    assert result is True
    
    # Verify gone
    assert await service.get_by_id("del-1") is None
    
    # Act: Try delete someone else's (should fail/return False or handle it)
    # For now assuming simple boolean return if not found or mismatch
    result_fail = await service.delete_automation("del-1", "p2") # Already gone, but logic applies
    assert result_fail is False

@pytest.mark.asyncio
async def test_admin_deletion_logic(session):
    """Test Superadmin deletion capabilities."""
    item = AutomationLibrary(
        id="admin-del-1", name="Admin Delete", type=AutomationType.CUSTOM_SCRIPT,
        partner_id="p1", code_content=""
    )
    session.add(item)
    await session.commit()
    
    service = LibraryService(session)
    
    # Act: Delete as Superadmin (even if not owner)
    # Note: We need to update delete_automation signature first to accept is_superadmin
    # This test assumes the signature update
    result = await service.delete_automation("admin-del-1", "any_partner", is_superadmin=True)
    assert result is True
    
    assert await service.get_by_id("admin-del-1") is None
