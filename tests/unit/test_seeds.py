"""
Tests unitarios para seeds de multitenancy (PROMPT 03).

TDD: Estos tests se escriben ANTES de completar la implementación.
"""
import pytest
import hashlib
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_seed_creates_dev_partner(test_server_db):
    """Verificar que seed crea Partner de desarrollo"""
    from server.app.database.seeds import seed_multitenancy_defaults
    from server.app.database.models import PartnerAccount
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    await seed_multitenancy_defaults()

    async with AsyncSession(test_server_db) as session:
        result = await session.execute(
            select(PartnerAccount).where(PartnerAccount.partner_id == "partner_dev")
        )
        partner = result.scalar_one_or_none()

        assert partner is not None
        assert partner.name == "Partner Desarrollo"
        assert partner.email == "dev@automatia.local"
        assert partner.credits_balance >= 1000000
        assert partner.is_active is True


@pytest.mark.asyncio
async def test_seed_creates_dev_client(test_server_db):
    """Verificar que seed crea Cliente de desarrollo"""
    from server.app.database.seeds import seed_multitenancy_defaults
    from server.app.database.models import ClientAccount
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    await seed_multitenancy_defaults()

    async with AsyncSession(test_server_db) as session:
        result = await session.execute(
            select(ClientAccount).where(ClientAccount.client_id == "client_dev")
        )
        client = result.scalar_one_or_none()

        assert client is not None
        assert client.partner_id == "partner_dev"
        assert client.name == "Cliente Desarrollo Local"
        assert client.is_active is True
        # License key debe estar hasheada
        expected_hash = hashlib.sha256("DEV_LICENSE_KEY_12345".encode()).hexdigest()
        assert client.license_key == expected_hash


@pytest.mark.asyncio
async def test_seed_creates_dev_license(test_server_db):
    """Verificar que seed crea Licencia de desarrollo"""
    from server.app.database.seeds import seed_multitenancy_defaults
    from server.app.database.models import License
    from automatia_shared.enums import LicenseStatus
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    await seed_multitenancy_defaults()

    async with AsyncSession(test_server_db) as session:
        result = await session.execute(
            select(License).where(License.license_id == "lic_dev")
        )
        license = result.scalar_one_or_none()

        assert license is not None
        assert license.client_id == "client_dev"
        assert license.quota_tokens >= 10000000  # 10M tokens para dev
        assert license.consumed_tokens == 0
        assert license.status == LicenseStatus.ACTIVE.value
        assert license.is_valid() is True


@pytest.mark.asyncio
async def test_seed_is_idempotent(test_server_db):
    """Verificar que ejecutar seed múltiples veces no duplica datos"""
    from server.app.database.seeds import seed_multitenancy_defaults
    from server.app.database.models import PartnerAccount, ClientAccount, License
    from sqlmodel import select, func
    from sqlmodel.ext.asyncio.session import AsyncSession

    # Ejecutar seed 3 veces
    await seed_multitenancy_defaults()
    await seed_multitenancy_defaults()
    await seed_multitenancy_defaults()

    async with AsyncSession(test_server_db) as session:
        # Contar Partners
        result = await session.execute(
            select(func.count()).select_from(PartnerAccount)
        )
        partner_count = result.scalar()

        # Contar Clients
        result = await session.execute(
            select(func.count()).select_from(ClientAccount)
        )
        client_count = result.scalar()

        # Contar Licenses
        result = await session.execute(
            select(func.count()).select_from(License)
        )
        license_count = result.scalar()

        # Debe haber exactamente 1 de cada uno
        assert partner_count == 1
        assert client_count == 1
        assert license_count == 1


@pytest.mark.asyncio
async def test_dev_license_key_works(test_server_db):
    """Verificar que la license_key de desarrollo es verificable"""
    from server.app.database.seeds import seed_multitenancy_defaults, DEV_LICENSE_KEY
    from server.app.database.models import ClientAccount
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    await seed_multitenancy_defaults()

    # Simular verificación de license_key
    key_hash = hashlib.sha256(DEV_LICENSE_KEY.encode()).hexdigest()

    async with AsyncSession(test_server_db) as session:
        result = await session.execute(
            select(ClientAccount).where(ClientAccount.license_key == key_hash)
        )
        client = result.scalar_one_or_none()

        assert client is not None
        assert client.client_id == "client_dev"
