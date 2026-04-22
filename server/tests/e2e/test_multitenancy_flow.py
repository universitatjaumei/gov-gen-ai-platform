import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.services.ai_brain import AIBrainService
from server.app.database.models import PartnerAccount, ClientAccount, License, LicenseStatus
from server.app.database.db import server_engine, init_db
import hashlib

@pytest.mark.asyncio
async def test_full_consumption_cycle():
    # 0. Limpiar DB para el test (o usar fixtures si estuvieran configuradas globalmente para limpiar)
    # Para E2E puro, idealmente usariamos una DB de test dedicada.
    # Asumimos que init_db maneja la creacion de tablas, pero aqui vamos a insertar datos nuevos.
    
    # 1. Crear datos base
    async with AsyncSession(server_engine) as session:
        # Limpieza previa para evitar colisiones si persistiera
        # (Opcional, depende de la config de pytest)
        
        partner = PartnerAccount(
            partner_id="partner_e2e",
            name="Partner E2E",
            email="partner@e2e.com", # Added required field
            credits_balance=200000,
            is_active=True
        )
        
        license_key_raw = "valid_key_e2e"
        license_key_hash = hashlib.sha256(license_key_raw.encode()).hexdigest()

        client = ClientAccount(
            client_id="client_e2e",
            name="Cliente E2E",
            partner_id="partner_e2e",
            license_key=license_key_hash,
            is_active=True
        )
        
        lic = License(
            license_id="lic_e2e",
            client_id="client_e2e",
            quota_tokens=100000,
            consumed_tokens=0,
            valid_until=datetime.utcnow() + timedelta(days=30),
            status=LicenseStatus.ACTIVE.value # Use value as it's a StrEnum/Enum
        )
        
        session.add(partner)
        session.add(client)
        session.add(lic)
        await session.commit()

    brain = AIBrainService()

    # 2. Validar licencia y generar texto (Mockeando solo la llamada LLM externa)
    # _validate_license TIENE que ir a base de datos real en este test E2E.
    # _call_llm se mockea para no gastar dinero/tokens reales.
    
    with patch.object(brain, "_call_llm", return_value="respuesta simulada"):
        # Simulamos que el prompt + respuesta suman X tokens
        # "hola" (4 chars) + "respuesta simulada" (18 chars) = 22 chars approx 5 tokens
        # _count_tokens es len/4.
        await brain.generate_text("hola", license_key=license_key_raw)

    # 3. Verificar consumo en DB
    async with AsyncSession(server_engine) as session:
        l2 = await session.get(License, "lic_e2e")
        assert l2.consumed_tokens > 0, "Deberia haber consumido tokens"
        
        p2 = await session.get(PartnerAccount, "partner_e2e")
        assert p2.credits_balance < 200000, "Deberia haber descontado creditos del partner"

    # 4. Agotar licencia y comprobar bloqueo
    # Forzamos consumo masivo directament en DB para simular agotamiento
    async with AsyncSession(server_engine) as session:
        lic_update = await session.get(License, "lic_e2e")
        lic_update.consumed_tokens = 100001
        session.add(lic_update)
        await session.commit()
    
    # Ahora la llamada deberia fallar
    with patch.object(brain, "_call_llm", return_value="no deberia llegar aqui"):
        with pytest.raises(ValueError, match="Cuota de tokens excedida"):
            await brain.generate_text("otro", license_key=license_key_raw)
