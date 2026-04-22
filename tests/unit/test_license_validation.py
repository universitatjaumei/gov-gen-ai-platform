"""
Tests unitarios para validación de licencias (PROMPT 04).

TDD: Estos tests se escriben ANTES de completar la implementación.
"""
import pytest
import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_valid_license_allows_generation(test_server_db):
    """Licencia válida permite generación de texto"""
    from server.app.services.ai_brain import AIBrainService
    from server.app.database.models import License, ClientAccount, PartnerAccount
    from server.app.database.seeds import seed_multitenancy_defaults, DEV_LICENSE_KEY
    from automatia_shared.enums import LicenseStatus

    # Seed datos de desarrollo
    await seed_multitenancy_defaults()

    brain = AIBrainService()

    # Mock de _call_llm para no hacer llamadas reales
    with patch.object(brain, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Test response from LLM"

        result = await brain.generate_text(
            prompt="Test prompt",
            license_key=DEV_LICENSE_KEY
        )

        assert result == "Test response from LLM"
        mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_invalid_license_key_raises_error(test_server_db):
    """Clave de licencia inválida lanza ValueError"""
    from server.app.services.ai_brain import AIBrainService
    from server.app.database.seeds import seed_multitenancy_defaults

    await seed_multitenancy_defaults()

    brain = AIBrainService()

    with pytest.raises(ValueError, match="Licencia no encontrada"):
        await brain.generate_text(
            prompt="Test",
            license_key="invalid_key_xyz_not_exists"
        )


@pytest.mark.asyncio
async def test_expired_license_raises_error(test_server_db):
    """Licencia expirada lanza error específico"""
    from server.app.services.ai_brain import AIBrainService
    from server.app.database.models import License, ClientAccount, PartnerAccount
    from server.app.database.db import server_engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    from automatia_shared.enums import LicenseStatus
    import hashlib

    # Crear datos con licencia expirada
    async with AsyncSession(server_engine) as session:
        partner = PartnerAccount(
            partner_id="partner_expired",
            name="Partner Expired",
            email="expired@test.com",
            credits_balance=100000,
            is_active=True
        )
        session.add(partner)

        license_key = "EXPIRED_KEY_123"
        key_hash = hashlib.sha256(license_key.encode()).hexdigest()

        client = ClientAccount(
            client_id="client_expired",
            partner_id="partner_expired",
            name="Client Expired",
            license_key=key_hash,
            is_active=True
        )
        session.add(client)

        license = License(
            license_id="lic_expired",
            client_id="client_expired",
            quota_tokens=100000,
            consumed_tokens=0,
            valid_until=datetime.utcnow() - timedelta(days=1),  # EXPIRADA
            status=LicenseStatus.ACTIVE.value
        )
        session.add(license)
        await session.commit()

    brain = AIBrainService()

    with pytest.raises(ValueError, match="Licencia expirada"):
        await brain.generate_text(
            prompt="Test",
            license_key=license_key
        )


@pytest.mark.asyncio
async def test_exceeded_quota_raises_error(test_server_db):
    """Cuota excedida lanza error específico"""
    from server.app.services.ai_brain import AIBrainService
    from server.app.database.models import License, ClientAccount, PartnerAccount
    from server.app.database.db import server_engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    from automatia_shared.enums import LicenseStatus
    import hashlib

    # Crear datos con cuota excedida
    async with AsyncSession(server_engine) as session:
        partner = PartnerAccount(
            partner_id="partner_quota",
            name="Partner Quota",
            email="quota@test.com",
            credits_balance=100000,
            is_active=True
        )
        session.add(partner)

        license_key = "QUOTA_EXCEEDED_KEY"
        key_hash = hashlib.sha256(license_key.encode()).hexdigest()

        client = ClientAccount(
            client_id="client_quota",
            partner_id="partner_quota",
            name="Client Quota",
            license_key=key_hash,
            is_active=True
        )
        session.add(client)

        license = License(
            license_id="lic_quota",
            client_id="client_quota",
            quota_tokens=100000,
            consumed_tokens=100001,  # EXCEDIDA
            valid_until=datetime.utcnow() + timedelta(days=30),
            status=LicenseStatus.ACTIVE.value
        )
        session.add(license)
        await session.commit()

    brain = AIBrainService()

    with pytest.raises(ValueError, match="Cuota de tokens excedida"):
        await brain.generate_text(
            prompt="Test",
            license_key=license_key
        )


@pytest.mark.asyncio
async def test_suspended_license_raises_error(test_server_db):
    """Licencia suspendida lanza error específico"""
    from server.app.services.ai_brain import AIBrainService
    from server.app.database.models import License, ClientAccount, PartnerAccount
    from server.app.database.db import server_engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    from automatia_shared.enums import LicenseStatus
    import hashlib

    # Crear datos con licencia suspendida
    async with AsyncSession(server_engine) as session:
        partner = PartnerAccount(
            partner_id="partner_suspended",
            name="Partner Suspended",
            email="suspended@test.com",
            credits_balance=100000,
            is_active=True
        )
        session.add(partner)

        license_key = "SUSPENDED_KEY_456"
        key_hash = hashlib.sha256(license_key.encode()).hexdigest()

        client = ClientAccount(
            client_id="client_suspended",
            partner_id="partner_suspended",
            name="Client Suspended",
            license_key=key_hash,
            is_active=True
        )
        session.add(client)

        license = License(
            license_id="lic_suspended",
            client_id="client_suspended",
            quota_tokens=100000,
            consumed_tokens=0,
            valid_until=datetime.utcnow() + timedelta(days=365),
            status=LicenseStatus.SUSPENDED.value  # SUSPENDIDA
        )
        session.add(license)
        await session.commit()

    brain = AIBrainService()

    with pytest.raises(ValueError, match="Licencia en estado"):
        await brain.generate_text(
            prompt="Test",
            license_key=license_key
        )


@pytest.mark.asyncio
async def test_token_consumption_is_updated(test_server_db):
    """Verificar que el consumo de tokens se actualiza"""
    from server.app.services.ai_brain import AIBrainService
    from server.app.database.models import License
    from server.app.database.db import server_engine
    from server.app.database.seeds import seed_multitenancy_defaults, DEV_LICENSE_KEY
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    await seed_multitenancy_defaults()

    brain = AIBrainService()

    # Obtener consumo inicial
    async with AsyncSession(server_engine) as session:
        result = await session.execute(
            select(License).where(License.license_id == "lic_dev")
        )
        license_before = result.scalar_one()
        initial_consumed = license_before.consumed_tokens

    # Mock de _call_llm
    with patch.object(brain, '_call_llm', new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Short response"

        await brain.generate_text(
            prompt="Test prompt for counting",
            license_key=DEV_LICENSE_KEY
        )

    # Verificar que se actualizó el consumo
    async with AsyncSession(server_engine) as session:
        result = await session.execute(
            select(License).where(License.license_id == "lic_dev")
        )
        license_after = result.scalar_one()

        assert license_after.consumed_tokens > initial_consumed


@pytest.mark.asyncio
async def test_count_tokens_estimation():
    """Verificar estimación de tokens"""
    from server.app.services.ai_brain import AIBrainService

    brain = AIBrainService()

    # 100 caracteres = ~25 tokens (4 chars/token)
    prompt = "a" * 80
    response = "b" * 20

    tokens = brain._count_tokens(prompt, response)

    assert tokens == 25  # 100 chars / 4
