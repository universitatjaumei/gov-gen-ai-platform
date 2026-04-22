"""
Tests unitarios para licencias multiasiento (PROMPT 08F, 8G, 8H).

TDD: Estos tests se escriben ANTES de completar la implementación.

Funcionalidades a validar:
- PROMPT 08F: Modelo License con max_seats, tabla LicenseActivation
- PROMPT 8G: Lógica verify_device_access con control de dispositivos
- PROMPT 8H: Generación de machine_fingerprint en cliente
"""
import pytest
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# =============================================================================
# PROMPT 08F: TESTS DE MODELOS (max_seats, LicenseActivation)
# =============================================================================

@pytest.mark.asyncio
async def test_license_has_max_seats_field(test_server_db):
    """License debe tener campo max_seats con valor por defecto 1"""
    from server.app.database.models import License
    from server.app.database.db import server_engine
    from sqlmodel.ext.asyncio.session import AsyncSession

    # Crear licencia sin especificar max_seats
    async with AsyncSession(server_engine) as session:
        license = License(
            license_id="lic_test_seats",
            client_id="client_test",
            quota_tokens=100000,
            consumed_tokens=0,
            valid_until=datetime.utcnow() + timedelta(days=30),
            status="active"
        )
        session.add(license)
        await session.commit()
        await session.refresh(license)

        # Verificar valor por defecto
        assert hasattr(license, 'max_seats'), "License debe tener campo max_seats"
        assert license.max_seats == 1, "max_seats debe ser 1 por defecto"


@pytest.mark.asyncio
async def test_license_activation_table_exists(test_server_db):
    """Debe existir la tabla LicenseActivation con los campos requeridos"""
    from server.app.database.models import LicenseActivation
    from server.app.database.db import server_engine
    from sqlmodel.ext.asyncio.session import AsyncSession

    async with AsyncSession(server_engine) as session:
        activation = LicenseActivation(
            license_id="lic_test",
            machine_id="machine_abc123",
            device_name="PC de Juan",
            activated_at=datetime.utcnow(),
            last_seen=datetime.utcnow()
        )
        session.add(activation)
        await session.commit()
        await session.refresh(activation)

        # Verificar campos
        assert activation.id is not None, "Debe tener id autoincremental"
        assert activation.license_id == "lic_test"
        assert activation.machine_id == "machine_abc123"
        assert activation.device_name == "PC de Juan"
        assert activation.activated_at is not None
        assert activation.last_seen is not None


# =============================================================================
# PROMPT 8G: TESTS DE LÓGICA verify_device_access
# =============================================================================

@pytest.mark.asyncio
async def test_verify_device_existing_activation_allows_access(test_server_db):
    """CASO A: Dispositivo ya activado permite acceso y actualiza last_seen"""
    from server.app.database.models import License, LicenseActivation, ClientAccount, PartnerAccount
    from server.app.database.db import server_engine
    from server.app.services.ai_brain import AIBrainService
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select

    license_key = "TEST_KEY_EXISTING"
    machine_id = "machine_existing_123"

    # Setup: crear partner, cliente, licencia y activación existente
    async with AsyncSession(server_engine) as session:
        partner = PartnerAccount(
            partner_id="partner_test_existing",
            name="Partner Test",
            email="test@test.com",
            credits_balance=100000,
            is_active=True
        )
        session.add(partner)

        key_hash = hashlib.sha256(license_key.encode()).hexdigest()
        client = ClientAccount(
            client_id="client_test_existing",
            partner_id="partner_test_existing",
            name="Client Test",
            license_key=key_hash,
            is_active=True
        )
        session.add(client)

        license = License(
            license_id="lic_test_existing",
            client_id="client_test_existing",
            quota_tokens=100000,
            consumed_tokens=0,
            valid_until=datetime.utcnow() + timedelta(days=30),
            status="active",
            max_seats=3
        )
        session.add(license)

        old_last_seen = datetime.utcnow() - timedelta(hours=1)
        activation = LicenseActivation(
            license_id="lic_test_existing",
            machine_id=machine_id,
            device_name="PC Existente",
            activated_at=datetime.utcnow() - timedelta(days=5),
            last_seen=old_last_seen
        )
        session.add(activation)
        await session.commit()

    # Test: verificar acceso
    brain = AIBrainService()
    result = await brain.verify_device_access(license_key, machine_id)

    assert result["allowed"] is True
    assert result["message"] == "Acceso permitido"

    # Verificar que last_seen se actualizó
    async with AsyncSession(server_engine) as session:
        stmt = select(LicenseActivation).where(
            LicenseActivation.license_id == "lic_test_existing",
            LicenseActivation.machine_id == machine_id
        )
        result = await session.execute(stmt)
        updated_activation = result.scalar_one()
        assert updated_activation.last_seen > old_last_seen


@pytest.mark.asyncio
async def test_verify_device_new_activation_within_seats_limit(test_server_db):
    """CASO B.1: Nuevo dispositivo con puestos disponibles registra y permite"""
    from server.app.database.models import License, LicenseActivation, ClientAccount, PartnerAccount
    from server.app.database.db import server_engine
    from server.app.services.ai_brain import AIBrainService
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select

    license_key = "TEST_KEY_NEW_SEAT"
    machine_id = "machine_new_456"

    # Setup: licencia con 3 puestos, 1 ya ocupado
    async with AsyncSession(server_engine) as session:
        partner = PartnerAccount(
            partner_id="partner_test_new",
            name="Partner Test",
            email="test@test.com",
            credits_balance=100000,
            is_active=True
        )
        session.add(partner)

        key_hash = hashlib.sha256(license_key.encode()).hexdigest()
        client = ClientAccount(
            client_id="client_test_new",
            partner_id="partner_test_new",
            name="Client Test",
            license_key=key_hash,
            is_active=True
        )
        session.add(client)

        license = License(
            license_id="lic_test_new",
            client_id="client_test_new",
            quota_tokens=100000,
            consumed_tokens=0,
            valid_until=datetime.utcnow() + timedelta(days=30),
            status="active",
            max_seats=3  # 3 puestos máximo
        )
        session.add(license)

        # 1 activación existente (quedan 2 puestos)
        activation = LicenseActivation(
            license_id="lic_test_new",
            machine_id="machine_otro_existente",
            device_name="PC Otro",
            activated_at=datetime.utcnow() - timedelta(days=1),
            last_seen=datetime.utcnow()
        )
        session.add(activation)
        await session.commit()

    # Test: nuevo dispositivo debe poder registrarse
    brain = AIBrainService()
    result = await brain.verify_device_access(license_key, machine_id)

    assert result["allowed"] is True
    assert result["message"] == "Nuevo dispositivo registrado"

    # Verificar que se creó la activación
    async with AsyncSession(server_engine) as session:
        stmt = select(LicenseActivation).where(
            LicenseActivation.license_id == "lic_test_new",
            LicenseActivation.machine_id == machine_id
        )
        result = await session.execute(stmt)
        new_activation = result.scalar_one_or_none()
        assert new_activation is not None


@pytest.mark.asyncio
async def test_verify_device_exceeds_seats_limit_denies_access(test_server_db):
    """CASO B.2: Nuevo dispositivo sin puestos disponibles es rechazado (HTTP 403)"""
    from server.app.database.models import License, LicenseActivation, ClientAccount, PartnerAccount
    from server.app.database.db import server_engine
    from server.app.services.ai_brain import AIBrainService
    from sqlmodel.ext.asyncio.session import AsyncSession

    license_key = "TEST_KEY_FULL"
    machine_id = "machine_rejected_789"

    # Setup: licencia con 2 puestos, 2 ya ocupados
    async with AsyncSession(server_engine) as session:
        partner = PartnerAccount(
            partner_id="partner_test_full",
            name="Partner Test",
            email="test@test.com",
            credits_balance=100000,
            is_active=True
        )
        session.add(partner)

        key_hash = hashlib.sha256(license_key.encode()).hexdigest()
        client = ClientAccount(
            client_id="client_test_full",
            partner_id="partner_test_full",
            name="Client Test",
            license_key=key_hash,
            is_active=True
        )
        session.add(client)

        license = License(
            license_id="lic_test_full",
            client_id="client_test_full",
            quota_tokens=100000,
            consumed_tokens=0,
            valid_until=datetime.utcnow() + timedelta(days=30),
            status="active",
            max_seats=2  # Solo 2 puestos
        )
        session.add(license)

        # 2 activaciones existentes (0 puestos libres)
        for i in range(2):
            activation = LicenseActivation(
                license_id="lic_test_full",
                machine_id=f"machine_ocupado_{i}",
                device_name=f"PC Ocupado {i}",
                activated_at=datetime.utcnow() - timedelta(days=i+1),
                last_seen=datetime.utcnow()
            )
            session.add(activation)
        await session.commit()

    # Test: nuevo dispositivo debe ser rechazado
    brain = AIBrainService()

    with pytest.raises(PermissionError, match="Límite de puestos excedido"):
        await brain.verify_device_access(license_key, machine_id)


@pytest.mark.asyncio
async def test_verify_device_invalid_license_raises_error(test_server_db):
    """Licencia inválida lanza ValueError"""
    from server.app.services.ai_brain import AIBrainService

    brain = AIBrainService()

    with pytest.raises(ValueError, match="Licencia no encontrada"):
        await brain.verify_device_access("INVALID_LICENSE_KEY", "any_machine")


# =============================================================================
# PROMPT 8H: TESTS DE get_machine_fingerprint (CLIENTE)
# =============================================================================

def test_get_machine_fingerprint_returns_stable_id():
    """get_machine_fingerprint debe retornar un ID único y estable"""
    from client_app.app.core.hardware_fingerprint import get_machine_fingerprint

    # Obtener fingerprint dos veces
    fp1 = get_machine_fingerprint()
    fp2 = get_machine_fingerprint()

    # Debe ser estable (mismo valor)
    assert fp1 == fp2, "Fingerprint debe ser estable entre llamadas"

    # Debe ser un string no vacío
    assert isinstance(fp1, str)
    assert len(fp1) > 10, "Fingerprint debe tener longitud suficiente"


def test_get_machine_fingerprint_is_unique_per_machine():
    """El fingerprint debe ser diferente para diferentes configuraciones de hardware"""
    from client_app.app.core.hardware_fingerprint import get_machine_fingerprint, _generate_fingerprint

    # Simular diferentes MACs (uuid.getnode)
    with patch('uuid.getnode', return_value=12345678901234):
        fp1 = _generate_fingerprint()

    with patch('uuid.getnode', return_value=98765432109876):
        fp2 = _generate_fingerprint()

    assert fp1 != fp2, "Diferentes MACs deben producir diferentes fingerprints"


def test_machine_fingerprint_format_is_hex():
    """El fingerprint debe estar en formato hexadecimal"""
    from client_app.app.core.hardware_fingerprint import get_machine_fingerprint

    fp = get_machine_fingerprint()

    # Debe ser hexadecimal válido
    try:
        int(fp, 16)
        is_hex = True
    except ValueError:
        is_hex = False

    assert is_hex, "Fingerprint debe ser hexadecimal válido"


# =============================================================================
# TEST DE INTEGRACIÓN: FLUJO COMPLETO
# =============================================================================

@pytest.mark.asyncio
async def test_multiasiento_full_flow_end_to_end(test_server_db):
    """Test E2E: Partner crea licencia multiasiento, clientes se registran"""
    from server.app.database.models import License, LicenseActivation, ClientAccount, PartnerAccount
    from server.app.database.db import server_engine
    from server.app.services.ai_brain import AIBrainService
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select

    license_key = "EMPRESA_X_LICENSE_KEY"

    # 1. Setup: Partner crea licencia con 3 puestos
    async with AsyncSession(server_engine) as session:
        partner = PartnerAccount(
            partner_id="partner_e2e",
            name="Partner E2E",
            email="e2e@test.com",
            credits_balance=500000,
            is_active=True
        )
        session.add(partner)

        key_hash = hashlib.sha256(license_key.encode()).hexdigest()
        client = ClientAccount(
            client_id="client_empresa_x",
            partner_id="partner_e2e",
            name="Empresa X",
            license_key=key_hash,
            is_active=True
        )
        session.add(client)

        license = License(
            license_id="lic_empresa_x",
            client_id="client_empresa_x",
            quota_tokens=1000000,
            consumed_tokens=0,
            valid_until=datetime.utcnow() + timedelta(days=365),
            status="active",
            max_seats=3  # 3 empleados máximo
        )
        session.add(license)
        await session.commit()

    brain = AIBrainService()

    # 2. Empleado 1 se registra - OK
    result1 = await brain.verify_device_access(license_key, "pc_empleado_1")
    assert result1["allowed"] is True

    # 3. Empleado 2 se registra - OK
    result2 = await brain.verify_device_access(license_key, "pc_empleado_2")
    assert result2["allowed"] is True

    # 4. Empleado 3 se registra - OK
    result3 = await brain.verify_device_access(license_key, "pc_empleado_3")
    assert result3["allowed"] is True

    # 5. Empleado 4 intenta registrarse - RECHAZADO
    with pytest.raises(PermissionError, match="Límite de puestos excedido"):
        await brain.verify_device_access(license_key, "pc_empleado_4")

    # 6. Empleado 1 (ya registrado) puede seguir accediendo
    result1_again = await brain.verify_device_access(license_key, "pc_empleado_1")
    assert result1_again["allowed"] is True

    # 7. Verificar que hay exactamente 3 activaciones
    async with AsyncSession(server_engine) as session:
        stmt = select(LicenseActivation).where(
            LicenseActivation.license_id == "lic_empresa_x"
        )
        result = await session.execute(stmt)
        activations = result.scalars().all()
        assert len(activations) == 3
