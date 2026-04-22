
"""
Tests para layout del Dashboard Partner.
Ejecutar: pytest tests/unit/test_partner_layout.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import sys

# MOCK NiceGUI to avoid hanging/server start
mock_nicegui = MagicMock()
mock_ui = MagicMock()
mock_app = MagicMock()
mock_nicegui.ui = mock_ui
mock_nicegui.app = mock_app
sys.modules["nicegui"] = mock_nicegui

from server.app.ui.partner_layout import PartnerContext, get_sidebar_items, generate_breadcrumb
from server.app.database.models import PartnerAccount
@pytest.mark.asyncio
async def test_context_from_dev_mode(server_db_session):
    """from_dev_mode carga partner directamente de BD."""
    # Setup: crear partner en BD
    partner = PartnerAccount(
        partner_id="dev_partner",
        name="Dev Partner SL",
        email="dev@partner.com",
        credits_balance=0,
        is_active=True
    )
    server_db_session.add(partner)
    await server_db_session.commit()

    # Act
    ctx = await PartnerContext.from_dev_mode("dev_partner", server_db_session)

    # Assert
    assert ctx.partner_id == "dev_partner"
    assert ctx.partner_name == "Dev Partner SL"
    assert ctx.is_authenticated is True


# --- TEST 2: Contexto dev_mode con partner inexistente ---
@pytest.mark.asyncio
async def test_context_dev_mode_invalid_partner(server_db_session):
    """from_dev_mode con partner inexistente retorna None."""
    ctx = await PartnerContext.from_dev_mode("no_existe", server_db_session)

    assert ctx is None



# --- TEST 3: Menu lateral contiene items correctos ---
def test_sidebar_menu_items():
    """Menu lateral tiene todas las secciones."""
    from server.app.ui.partner_layout import get_sidebar_items

    items = get_sidebar_items()

    labels = [item["label"] for item in items]
    assert "Dashboard" in labels
    assert "Clientes" in labels
    assert "Licencias" in labels
    assert "Scripts" in labels
    assert "Facturacion" in labels


# --- TEST 4: Breadcrumb se genera correctamente ---
def test_breadcrumb_generation():
    """Breadcrumb muestra ruta correcta."""
    bc = generate_breadcrumb("/partner/clients/edit/client_001")

    assert len(bc) == 3
    assert bc[0]["label"] == "Dashboard"
    assert bc[1]["label"] == "Clientes"
    assert bc[2]["label"] == "Editar"


# --- TEST 5: Header muestra nombre del partner ---
@pytest.mark.asyncio
async def test_header_shows_partner_name(server_db_session):
    """Header debe mostrar nombre del partner."""
    partner = PartnerAccount(
        partner_id="header_test",
        name="Consultora TIC SL",
        email="tic@consultora.com",
        credits_balance=0,
        is_active=True
    )
    server_db_session.add(partner)
    await server_db_session.commit()

    ctx = await PartnerContext.from_dev_mode("header_test", server_db_session)

    header_text = ctx.get_header_text()

    assert "Consultora TIC SL" in header_text
