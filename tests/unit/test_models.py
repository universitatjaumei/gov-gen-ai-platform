"""
Tests unitarios para modelos de jerarquía de cuentas (PROMPT 01).

TDD: Estos tests se escriben ANTES de completar la implementación.
"""
import pytest
from datetime import datetime, timedelta


def test_partner_account_creation():
    """Verificar creación de cuenta Partner"""
    from server.app.database.models import PartnerAccount

    partner = PartnerAccount(
        partner_id="partner_001",
        name="Tech Solutions SL",
        email="contact@techsolutions.es",
        credits_balance=10000,
        is_active=True
    )
    assert partner.partner_id == "partner_001"
    assert partner.name == "Tech Solutions SL"
    assert partner.email == "contact@techsolutions.es"
    assert partner.credits_balance == 10000
    assert partner.is_active is True


def test_client_account_hierarchy():
    """Verificar relación FK Partner->Cliente"""
    from server.app.database.models import ClientAccount

    client = ClientAccount(
        client_id="client_001",
        name="Ayuntamiento de Valencia",
        partner_id="partner_001",
        license_key="abc123xyz_hashed",
        is_active=True
    )
    assert client.client_id == "client_001"
    assert client.partner_id == "partner_001"
    assert client.name == "Ayuntamiento de Valencia"
    assert client.license_key == "abc123xyz_hashed"
    assert client.is_active is True


def test_license_status_enum():
    """Verificar enum LicenseStatus"""
    from automatia_shared.enums import LicenseStatus

    assert LicenseStatus.ACTIVE.value == "active"
    assert LicenseStatus.SUSPENDED.value == "suspended"
    assert LicenseStatus.EXPIRED.value == "expired"
    assert LicenseStatus.PENDING.value == "pending"


def test_license_validation_active():
    """Verificar lógica de validación de licencia activa"""
    from server.app.database.models import License
    from automatia_shared.enums import LicenseStatus

    license = License(
        license_id="lic_001",
        client_id="client_001",
        quota_tokens=100000,
        consumed_tokens=50000,
        valid_until=datetime.utcnow() + timedelta(days=365),
        status=LicenseStatus.ACTIVE.value
    )

    # Test lógica de negocio
    assert license.is_valid() is True


def test_license_remaining_tokens():
    """Verificar cálculo de tokens restantes"""
    from server.app.database.models import License
    from automatia_shared.enums import LicenseStatus

    license = License(
        license_id="lic_001",
        client_id="client_001",
        quota_tokens=100000,
        consumed_tokens=50000,
        valid_until=datetime.utcnow() + timedelta(days=365),
        status=LicenseStatus.ACTIVE.value
    )

    assert license.remaining_tokens == 50000


def test_license_invalid_when_quota_exceeded():
    """Test exceso de cuota invalida la licencia"""
    from server.app.database.models import License
    from automatia_shared.enums import LicenseStatus

    license = License(
        license_id="lic_002",
        client_id="client_001",
        quota_tokens=100000,
        consumed_tokens=100001,  # Excedida
        valid_until=datetime.utcnow() + timedelta(days=30),
        status=LicenseStatus.ACTIVE.value
    )

    assert license.is_valid() is False


def test_license_invalid_when_expired():
    """Test licencia expirada es inválida"""
    from server.app.database.models import License
    from automatia_shared.enums import LicenseStatus

    license = License(
        license_id="lic_003",
        client_id="client_001",
        quota_tokens=100000,
        consumed_tokens=0,
        valid_until=datetime.utcnow() - timedelta(days=1),  # Expirada
        status=LicenseStatus.ACTIVE.value
    )

    assert license.is_valid() is False


def test_license_invalid_when_suspended():
    """Test licencia suspendida es inválida"""
    from server.app.database.models import License
    from automatia_shared.enums import LicenseStatus

    license = License(
        license_id="lic_004",
        client_id="client_001",
        quota_tokens=100000,
        consumed_tokens=0,
        valid_until=datetime.utcnow() + timedelta(days=365),
        status=LicenseStatus.SUSPENDED.value
    )

    assert license.is_valid() is False


def test_license_remaining_tokens_never_negative():
    """Verificar que remaining_tokens nunca es negativo"""
    from server.app.database.models import License
    from automatia_shared.enums import LicenseStatus

    license = License(
        license_id="lic_005",
        client_id="client_001",
        quota_tokens=100000,
        consumed_tokens=150000,  # Mayor que quota
        valid_until=datetime.utcnow() + timedelta(days=365),
        status=LicenseStatus.ACTIVE.value
    )

    assert license.remaining_tokens == 0  # No debe ser -50000
