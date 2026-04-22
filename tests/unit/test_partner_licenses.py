
"""
Tests para gestion de licencias del Partner.
Ejecutar: pytest tests/unit/test_partner_licenses.py -v
"""
import pytest
from datetime import datetime, timedelta
from automatia_shared.enums import LicenseStatus

# --- TEST 1: Listar licencias de clientes propios ---
@pytest.mark.asyncio
async def test_list_own_licenses(server_db_session):
    """Partner solo ve licencias de sus clientes."""
    from server.app.services.partner_license_service import PartnerLicenseService
    from server.app.database.models import PartnerAccount, ClientAccount, License
    
    # Setup
    p_a = PartnerAccount(partner_id="partner_a", name="A", email="a@a.com", is_active=True)
    p_b = PartnerAccount(partner_id="partner_b", name="B", email="b@b.com", is_active=True)
    server_db_session.add_all([p_a, p_b])
    
    c_a = ClientAccount(client_id="ca1", partner_id="partner_a", name="Client A", license_key="x")
    c_b = ClientAccount(client_id="cb1", partner_id="partner_b", name="Client B", license_key="y")
    server_db_session.add_all([c_a, c_b])
    
    l_a = License(license_id="lic_a", client_id="ca1", quota_tokens=100, consumed_tokens=0, status=LicenseStatus.ACTIVE.value, valid_until=datetime.utcnow() + timedelta(days=30))
    l_b = License(license_id="lic_b", client_id="cb1", quota_tokens=100, consumed_tokens=0, status=LicenseStatus.ACTIVE.value, valid_until=datetime.utcnow() + timedelta(days=30))
    server_db_session.add_all([l_a, l_b])
    await server_db_session.commit()

    service = PartnerLicenseService(server_db_session, partner_id="partner_a")
    licenses = await service.list_licenses()

    assert len(licenses) == 1
    assert licenses[0].license_id == "lic_a"



# --- TEST 2: Aumentar quota ---
@pytest.mark.asyncio
async def test_increase_quota(server_db_session):
    """Partner puede aumentar quota de licencia de su cliente."""
    from server.app.services.partner_license_service import PartnerLicenseService
    from server.app.database.models import PartnerAccount, ClientAccount, License
    
    # Setup dependencies
    p = PartnerAccount(partner_id="p_quota", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p)
    c = ClientAccount(client_id="c_quota", partner_id="p_quota", name="Client Q", license_key="x")
    server_db_session.add(c)
    
    # Setup license
    lic = License(license_id="lic_quota", client_id="c_quota", quota_tokens=100000, consumed_tokens=0, status=LicenseStatus.ACTIVE.value, valid_until=datetime.utcnow() + timedelta(days=30))
    server_db_session.add(lic)
    await server_db_session.commit()

    service = PartnerLicenseService(server_db_session, partner_id="p_quota")
    updated = await service.adjust_quota("lic_quota", add_tokens=50000)

    assert updated.quota_tokens == 150000


# --- TEST 3: Extender validez ---
@pytest.mark.asyncio
async def test_extend_validity(server_db_session):
    """Partner puede extender fecha de validez."""
    from server.app.services.partner_license_service import PartnerLicenseService
    from server.app.database.models import PartnerAccount, ClientAccount, License

    # Setup dependencies
    p = PartnerAccount(partner_id="p_valid", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p)
    c = ClientAccount(client_id="c_valid", partner_id="p_valid", name="Client V", license_key="x")
    server_db_session.add(c)

    today = datetime.utcnow()
    original_expiry = today + timedelta(days=30)
    lic = License(license_id="lic_valid", client_id="c_valid", quota_tokens=100, consumed_tokens=0, status=LicenseStatus.ACTIVE.value, valid_until=original_expiry)
    server_db_session.add(lic)
    await server_db_session.commit()

    service = PartnerLicenseService(server_db_session, partner_id="p_valid")
    updated = await service.extend_validity("lic_valid", add_days=90)

    assert updated.valid_until > original_expiry + timedelta(days=89)


# --- TEST 4: Suspender licencia ---
@pytest.mark.asyncio
async def test_suspend_license(server_db_session):
    """Partner puede suspender licencia."""
    from server.app.services.partner_license_service import PartnerLicenseService
    from server.app.database.models import PartnerAccount, ClientAccount, License

    # Setup dependencies
    p = PartnerAccount(partner_id="p_suspend", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p)
    c = ClientAccount(client_id="c_suspend", partner_id="p_suspend", name="Client S", license_key="x")
    server_db_session.add(c)
    
    lic = License(license_id="lic_suspend", client_id="c_suspend", quota_tokens=100, consumed_tokens=0, status=LicenseStatus.ACTIVE.value, valid_until=datetime.utcnow() + timedelta(days=30))
    server_db_session.add(lic)
    await server_db_session.commit()

    service = PartnerLicenseService(server_db_session, partner_id="p_suspend")
    result = await service.suspend_license("lic_suspend", reason="Impago")

    assert result.status == LicenseStatus.SUSPENDED.value


# --- TEST 5: Reactivar licencia suspendida ---
@pytest.mark.asyncio
async def test_reactivate_license(server_db_session):
    """Partner puede reactivar licencia suspendida."""
    from server.app.services.partner_license_service import PartnerLicenseService
    from server.app.database.models import PartnerAccount, ClientAccount, License

    # Setup dependencies
    p = PartnerAccount(partner_id="p_react", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p)
    c = ClientAccount(client_id="c_react", partner_id="p_react", name="Client R", license_key="x")
    server_db_session.add(c)

    # Initial state suspended
    lic = License(license_id="lic_react", client_id="c_react", quota_tokens=100, consumed_tokens=0, status=LicenseStatus.SUSPENDED.value, valid_until=datetime.utcnow() + timedelta(days=30))
    server_db_session.add(lic)
    await server_db_session.commit()

    service = PartnerLicenseService(server_db_session, partner_id="p_react")
    reactivated = await service.reactivate_license("lic_react")

    assert reactivated.status == LicenseStatus.ACTIVE.value


# --- TEST 6: Obtener licencias proximas a expirar ---
@pytest.mark.asyncio
async def test_get_expiring_soon(server_db_session):
    """Obtener licencias que expiran en X dias."""
    from server.app.services.partner_license_service import PartnerLicenseService
    from server.app.database.models import PartnerAccount, ClientAccount, License

    # Setup dependencies
    p = PartnerAccount(partner_id="p_expire", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p)
    c = ClientAccount(client_id="c_expire", partner_id="p_expire", name="Client E", license_key="x")
    server_db_session.add(c)

    # Expires in 10 days
    lic = License(license_id="lic_expire", client_id="c_expire", quota_tokens=100, consumed_tokens=0, status=LicenseStatus.ACTIVE.value, valid_until=datetime.utcnow() + timedelta(days=10))
    server_db_session.add(lic)
    await server_db_session.commit()

    service = PartnerLicenseService(server_db_session, partner_id="p_expire")
    expiring = await service.get_expiring_soon(days=15)

    assert len(expiring) == 1
    assert expiring[0].license_id == "lic_expire"


# --- TEST 7: Obtener licencias con quota baja ---
@pytest.mark.asyncio
async def test_get_low_quota(server_db_session):
    """Obtener licencias con menos del X% de quota."""
    from server.app.services.partner_license_service import PartnerLicenseService
    from server.app.database.models import PartnerAccount, ClientAccount, License

    # Setup dependencies
    p = PartnerAccount(partner_id="p_low", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p)
    c = ClientAccount(client_id="c_low", partner_id="p_low", name="Client L", license_key="x")
    server_db_session.add(c)

    # 90 consumed out of 100 = 10% remaining. Threshold 20% should catch it.
    lic = License(license_id="lic_low", client_id="c_low", quota_tokens=100, consumed_tokens=90, status=LicenseStatus.ACTIVE.value, valid_until=datetime.utcnow() + timedelta(days=30))
    server_db_session.add(lic)
    await server_db_session.commit()

    service = PartnerLicenseService(server_db_session, partner_id="p_low")
    low_quota = await service.get_low_quota(threshold_percent=20)

    assert len(low_quota) == 1
    assert low_quota[0].license_id == "lic_low"


# --- TEST 8: Historial de cambios de licencia ---
@pytest.mark.asyncio
async def test_license_audit_log(server_db_session):
    """Los cambios de licencia quedan registrados."""
    from server.app.services.partner_license_service import PartnerLicenseService
    from server.app.database.models import PartnerAccount, ClientAccount, License

    # Setup dependencies
    p = PartnerAccount(partner_id="p_audit", name="A", email="a@a.com", is_active=True)
    server_db_session.add(p)
    c = ClientAccount(client_id="c_audit", partner_id="p_audit", name="Client A", license_key="x")
    server_db_session.add(c)
    
    lic = License(license_id="lic_audit", client_id="c_audit", quota_tokens=10000, consumed_tokens=0, status=LicenseStatus.ACTIVE.value, valid_until=datetime.utcnow() + timedelta(days=30))
    server_db_session.add(lic)
    await server_db_session.commit()

    service = PartnerLicenseService(server_db_session, partner_id="p_audit")
    await service.adjust_quota("lic_audit", add_tokens=10000)

    audit = await service.get_license_audit("lic_audit")

    assert len(audit) >= 1
    assert audit[0]["performed_by"] == "p_audit"

