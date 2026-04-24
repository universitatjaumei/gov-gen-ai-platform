"""
Seeds de multitenancy para desarrollo.

Este módulo crea los datos iniciales necesarios para desarrollo:
- Admin de desarrollo
- Partner de desarrollo
- Cliente de desarrollo
- Licencia de desarrollo con cuota amplia

Credenciales de desarrollo:
  Admin:   admin@govgenai.local  /  admin1234
  Partner: dev@automatia.local   /  (cualquiera — login partner no verifica pwd)

La clave de licencia de desarrollo es: DEV_LICENSE_KEY_12345
"""
import hashlib
from datetime import datetime, timedelta
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.database.models import AdminAccount, PartnerAccount, ClientAccount, License, ExtractionServiceConfig
from server.app.core.security import hash_password
from automatia_shared.enums import LicenseStatus


# Constante para desarrollo - usar en tests y desarrollo local
DEV_LICENSE_KEY = "DEV_LICENSE_KEY_12345"
DEV_ADMIN_EMAIL = "admin@govgenai.local"
DEV_ADMIN_PASSWORD = "admin1234"


async def seed_multitenancy_defaults():
    """
    Crea los datos de multitenancy para desarrollo.

    Esta función es IDEMPOTENTE: ejecutarla múltiples veces
    no duplicará los datos.

    Crea:
    - 1 AdminAccount  (admin@govgenai.local / admin1234)
    - 1 PartnerAccount (partner_dev)
    - 1 ClientAccount (client_dev)
    - 1 License (lic_dev) con 10M tokens de cuota
    """
    async with AsyncSession(server_engine) as session:
        # 0. Crear Admin de desarrollo
        await _seed_dev_admin(session)

        # 1. Crear Partner de desarrollo
        await _seed_dev_partner(session)

        # 2. Crear Cliente de desarrollo
        await _seed_dev_client(session)

        # 3. Crear Licencia de desarrollo
        await _seed_dev_license(session)

        await session.commit()
        print("[SEED] Multitenancy de desarrollo creado/verificado.")


async def _seed_dev_admin(session: AsyncSession):
    """Crea el AdminAccount de desarrollo si no existe."""
    result = await session.execute(
        select(AdminAccount).where(AdminAccount.email == DEV_ADMIN_EMAIL)
    )
    existing = result.scalar_one_or_none()

    if not existing:
        admin = AdminAccount(
            name="Admin Desarrollo",
            email=DEV_ADMIN_EMAIL,
            hashed_password=hash_password(DEV_ADMIN_PASSWORD),
            is_active=True,
        )
        session.add(admin)
        print(f"[SEED] Admin de desarrollo creado: {DEV_ADMIN_EMAIL}")
    else:
        print("[SEED] Admin de desarrollo ya existe.")


async def _seed_dev_partner(session: AsyncSession):
    """Crea el Partner de desarrollo si no existe."""
    result = await session.execute(
        select(PartnerAccount).where(PartnerAccount.partner_id == "partner_dev")
    )
    existing = result.scalar_one_or_none()

    if not existing:
        partner = PartnerAccount(
            partner_id="partner_dev",
            name="Partner Desarrollo",
            email="dev@automatia.local",
            credits_balance=1000000,  # 1M de créditos para desarrollo
            is_active=True
        )
        session.add(partner)
        print("[SEED] Partner de desarrollo creado: partner_dev")
    else:
        print("[SEED] Partner de desarrollo ya existe.")


async def _seed_dev_client(session: AsyncSession):
    """Crea el Cliente de desarrollo si no existe."""
    result = await session.execute(
        select(ClientAccount).where(ClientAccount.client_id == "client_dev")
    )
    existing = result.scalar_one_or_none()

    if not existing:
        # Hash de la license_key para almacenamiento seguro
        license_key_hash = hashlib.sha256(DEV_LICENSE_KEY.encode()).hexdigest()

        client = ClientAccount(
            client_id="client_dev",
            partner_id="partner_dev",
            name="Cliente Desarrollo Local",
            email="client@automatia.local",
            license_key=license_key_hash,
            is_active=True
        )
        session.add(client)
        print("[SEED] Cliente de desarrollo creado: client_dev")
    else:
        print("[SEED] Cliente de desarrollo ya existe.")


async def _seed_dev_license(session: AsyncSession):
    """Crea la Licencia de desarrollo si no existe."""
    result = await session.execute(
        select(License).where(License.license_id == "lic_dev")
    )
    existing = result.scalar_one_or_none()

    if not existing:
        license = License(
            license_id="lic_dev",
            client_id="client_dev",
            quota_tokens=10000000,  # 10M tokens para desarrollo
            consumed_tokens=0,
            valid_until=datetime.utcnow() + timedelta(days=365),  # 1 año
            status=LicenseStatus.ACTIVE.value
        )
        session.add(license)
        print("[SEED] Licencia de desarrollo creada: lic_dev")
    else:
        print("[SEED] Licencia de desarrollo ya existe.")


async def seed_prompt_tiers():
    """Asigna tiers iniciales a los prompts del sistema conocidos."""
    TIER_MAPPING = {
        # Tier 1: Extracción PDF (Flash)
        "sys_phase0_discovery": 1,
        "sys_phase1_extraction": 1,
        "sys_fallback_snippet": 1,
        "sys_pdf_extraction": 1,
        
        # Tier 2: Lógica/Navegación (Flash/Standard)
        "sys_phase1_refinement": 2,
        "sys_rpa_analysis": 2,
        "sys_rpa_vision": 2,
        "sys_utility_noise_filter": 2,
        
        # Tier 3: Supervisión (Pro)
        "sys_phase3_factory_gen": 2, # Cambiado de 3 a 2 para programación (Tier 2: Lógica)
        "sys_phase3_refinement": 3,
        "sys_phase3_audit_forensic": 3,
        "sys_script_gen": 3,  # Legacy alias
        "factory_gen": 3,     # Legacy alias
        "anchor_based": 3,    # Legacy alias
    }
    
    async with AsyncSession(server_engine) as session:
        print("[SEED] Aplicando migración de Tiers a Prompts...")
        for service_id, tier in TIER_MAPPING.items():
            prompt = await session.get(ExtractionServiceConfig, service_id)
            if prompt:
                if prompt.tier_override is None: # Solo si no tiene tier
                    prompt.tier_override = tier
                    session.add(prompt)
                    print(f"  -> Asignado Tier {tier} a {service_id}")
        
        await session.commit()

async def seed_all():
    """
    Ejecuta todos los seeds del servidor.

    Incluye:
    - Seeds de multitenancy (desarrollo)
    - Seeds de configuración AI (si existen)
    """
    from server.app.database.db import seed_server_db

    # 1. Seeds de configuración AI existentes
    await seed_server_db()

    # 2. Seeds de multitenancy
    await seed_multitenancy_defaults()

    # 3. Seeds de Prompts del Sistema (Nuevos Phase 4)
    from server.app.database.seeds_prompts import seed_system_prompts, seed_v12_system_prompts
    await seed_system_prompts()
    await seed_v12_system_prompts()

    # 4. Migración de Tiers (Legacy)
    await seed_prompt_tiers()

    print("[SEED] Todos los seeds del servidor completados.")
