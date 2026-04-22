
"""
Tests para CRUD de clientes del Partner.
Ejecutar: pytest tests/unit/test_partner_clients.py -v
"""
import pytest
from datetime import datetime, timedelta

# --- TEST 1: Listar solo clientes propios ---
@pytest.mark.asyncio
async def test_list_only_own_clients(server_db_session):
    """Partner solo ve sus propios clientes."""
    from server.app.services.partner_client_service import PartnerClientService
    from server.app.database.models import PartnerAccount, ClientAccount

    # Setup: 2 partners, cada uno con 2 clientes
    partner_a = PartnerAccount(partner_id="partner_a", name="A", email="a@a.com", is_active=True)
    partner_b = PartnerAccount(partner_id="partner_b", name="B", email="b@b.com", is_active=True)
    server_db_session.add_all([partner_a, partner_b])
    
    client_a1 = ClientAccount(client_id="a1", partner_id="partner_a", name="Client A1", license_key="hash1")
    client_a2 = ClientAccount(client_id="a2", partner_id="partner_a", name="Client A2", license_key="hash2")
    client_b1 = ClientAccount(client_id="b1", partner_id="partner_b", name="Client B1", license_key="hash3")
    server_db_session.add_all([client_a1, client_a2, client_b1])
    await server_db_session.commit()

    # Act
    service = PartnerClientService(server_db_session, partner_id="partner_a")
    clients = await service.list_clients()

    # Assert
    assert len(clients) == 2
    assert all(c.partner_id == "partner_a" for c in clients)


# --- TEST 2: Crear cliente asigna partner_id automaticamente ---
@pytest.mark.asyncio
async def test_create_client_auto_assigns_partner(server_db_session):
    """Al crear cliente, se asigna partner_id del contexto."""
    from server.app.services.partner_client_service import PartnerClientService
    # Ensure partner exists for foreign key constraint if enforced
    from server.app.database.models import PartnerAccount
    partner = PartnerAccount(partner_id="my_partner", name="My Partner", email="my@partner.com", is_active=True)
    server_db_session.add(partner)
    await server_db_session.commit()

    service = PartnerClientService(server_db_session, partner_id="my_partner")

    new_client = await service.create_client(
        client_id="new_client_001",
        name="Nuevo Cliente SA",
        license_key_raw="LIC-TEST-1234"
    )

    assert new_client.partner_id == "my_partner"
    assert new_client.client_id == "new_client_001"


# --- TEST 3: No se puede acceder a cliente de otro partner ---
@pytest.mark.asyncio
async def test_cannot_access_other_partner_client(server_db_session):
    """Intento de acceder a cliente de otro partner retorna None."""
    from server.app.services.partner_client_service import PartnerClientService
    from server.app.database.models import ClientAccount, PartnerAccount

    # Setup partners
    p_a = PartnerAccount(partner_id="partner_a", name="A", email="a@a.com", is_active=True)
    p_b = PartnerAccount(partner_id="partner_b", name="B", email="b@b.com", is_active=True)
    server_db_session.add_all([p_a, p_b])
    
    # Cliente de partner_b
    client = ClientAccount(client_id="other_client", partner_id="partner_b", name="Other", license_key="x")
    server_db_session.add(client)
    await server_db_session.commit()

    # Servicio para partner_a
    service = PartnerClientService(server_db_session, partner_id="partner_a")
    result = await service.get_client("other_client")

    assert result is None


# --- TEST 4: Actualizar cliente propio ---
@pytest.mark.asyncio
async def test_update_own_client(server_db_session):
    """Partner puede actualizar su propio cliente."""
    from server.app.services.partner_client_service import PartnerClientService
    from server.app.database.models import ClientAccount, PartnerAccount

    p_a = PartnerAccount(partner_id="partner_a", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p_a)
    client = ClientAccount(client_id="my_client", partner_id="partner_a", name="Original", license_key="x")
    server_db_session.add(client)
    await server_db_session.commit()

    service = PartnerClientService(server_db_session, partner_id="partner_a")
    updated = await service.update_client("my_client", name="Updated Name")

    assert updated is not None
    assert updated.name == "Updated Name"


# --- TEST 5: No se puede actualizar cliente de otro partner ---
@pytest.mark.asyncio
async def test_cannot_update_other_partner_client(server_db_session):
    """Intento de actualizar cliente ajeno falla."""
    from server.app.services.partner_client_service import PartnerClientService
    from server.app.database.models import ClientAccount, PartnerAccount

    p_a = PartnerAccount(partner_id="partner_a", name="A", email="a@a.com", is_active=True)
    p_b = PartnerAccount(partner_id="partner_b", name="B", email="b@b.com", is_active=True)
    server_db_session.add_all([p_a, p_b])
    client = ClientAccount(client_id="foreign", partner_id="partner_b", name="Foreign", license_key="x")
    server_db_session.add(client)
    await server_db_session.commit()

    service = PartnerClientService(server_db_session, partner_id="partner_a")
    result = await service.update_client("foreign", name="Hacked!")

    assert result is None


# --- TEST 6: Desactivar cliente ---
@pytest.mark.asyncio
async def test_deactivate_client(server_db_session):
    """Partner puede desactivar su cliente."""
    from server.app.services.partner_client_service import PartnerClientService
    from server.app.database.models import ClientAccount, PartnerAccount

    p_a = PartnerAccount(partner_id="partner_a", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p_a)
    client = ClientAccount(client_id="to_deactivate", partner_id="partner_a", name="X", license_key="x", is_active=True)
    server_db_session.add(client)
    await server_db_session.commit()

    service = PartnerClientService(server_db_session, partner_id="partner_a")
    result = await service.deactivate_client("to_deactivate")

    assert result is True

    # Verificar
    updated = await service.get_client("to_deactivate")
    assert updated.is_active is False


# --- TEST 7: Busqueda de clientes ---
@pytest.mark.asyncio
async def test_search_clients(server_db_session):
    """Buscar clientes por nombre."""
    from server.app.services.partner_client_service import PartnerClientService
    from server.app.database.models import ClientAccount, PartnerAccount

    p_a = PartnerAccount(partner_id="partner_a", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p_a)
    clients = [
        ClientAccount(client_id="c1", partner_id="partner_a", name="Ayuntamiento Valencia", license_key="x"),
        ClientAccount(client_id="c2", partner_id="partner_a", name="Ayuntamiento Barcelona", license_key="y"),
        ClientAccount(client_id="c3", partner_id="partner_a", name="Diputacion Alicante", license_key="z"),
    ]
    server_db_session.add_all(clients)
    await server_db_session.commit()

    service = PartnerClientService(server_db_session, partner_id="partner_a")
    results = await service.search_clients("Ayuntamiento")

    assert len(results) == 2


# --- TEST 8: Cliente con licencia incluida ---
@pytest.mark.asyncio
async def test_create_client_with_license(server_db_session):
    """Crear cliente genera licencia automaticamente."""
    from server.app.services.partner_client_service import PartnerClientService
    from server.app.database.models import PartnerAccount
    
    p_a = PartnerAccount(partner_id="partner_a", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p_a)
    await server_db_session.commit()

    service = PartnerClientService(server_db_session, partner_id="partner_a")

    client, license = await service.create_client_with_license(
        client_id="client_with_lic",
        name="Cliente Con Licencia",
        license_key_raw="LIC-ABC-123",
        quota_tokens=500000,
        valid_days=365
    )

    assert client is not None
    assert license is not None
    assert license.client_id == client.client_id
    assert license.quota_tokens == 500000


# --- TEST 9: Regenerar license key ---
@pytest.mark.asyncio
async def test_regenerate_license_key(server_db_session):
    """Regenerar key de un cliente existente."""
    from server.app.services.partner_client_service import PartnerClientService
    from server.app.database.models import ClientAccount, PartnerAccount

    p_a = PartnerAccount(partner_id="partner_a", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p_a)
    client = ClientAccount(client_id="regen_test", partner_id="partner_a", name="X", license_key="old_hash")
    server_db_session.add(client)
    await server_db_session.commit()

    service = PartnerClientService(server_db_session, partner_id="partner_a")
    new_key, new_hash = await service.regenerate_license_key("regen_test")

    assert new_key.startswith("LIC-")
    assert new_hash != "old_hash"


# --- TEST 10: Estadisticas de cliente ---
@pytest.mark.asyncio
async def test_get_client_stats(server_db_session):
    """Obtener estadisticas de consumo de un cliente."""
    from server.app.services.partner_client_service import PartnerClientService
    from server.app.database.models import ClientAccount, License, PartnerAccount
    from datetime import datetime

    p_a = PartnerAccount(partner_id="partner_a", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p_a)
    # Setup
    client = ClientAccount(client_id="stats_client", partner_id="partner_a", name="Stats", license_key="x")
    license = License(
        license_id="lic_stats",
        client_id="stats_client",
        quota_tokens=100000,
        consumed_tokens=25000,
        valid_until=datetime.utcnow() + timedelta(days=30),
        status="ACTIVE"
    )
    server_db_session.add_all([client, license])
    await server_db_session.commit()

    service = PartnerClientService(server_db_session, partner_id="partner_a")
    stats = await service.get_client_stats("stats_client")

    assert stats["quota_tokens"] == 100000
    assert stats["consumed_tokens"] == 25000
    assert stats["usage_percent"] == 25.0
