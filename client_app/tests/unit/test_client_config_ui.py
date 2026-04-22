import pytest
from sqlmodel import select
from app.database.models import LocalCredentials, ServerConnection, SecurityPolicy
from app.modules.security.encryption_service import EncryptionService
from datetime import datetime
import json

@pytest.mark.asyncio
async def test_save_server_connection(test_client_db):
    """Verificar guardado de configuracion de conexion al Brain."""
    from app.database.db import client_engine
    from sqlmodel.ext.asyncio.session import AsyncSession

    async with AsyncSession(client_engine) as session:
        # Limpieza robusta ex-ante
        from sqlmodel import delete
        await session.execute(delete(ServerConnection))
        await session.commit()

        # Guardar configuracion
        conn = ServerConnection(
            brain_url="https://brain.test.com",
            license_key="test-license-key",
            is_active=True
        )
        session.add(conn)
        await session.commit()

        # Recuperar
        result = await session.execute(select(ServerConnection))
        saved = result.scalar_one()

        assert saved.brain_url == "https://brain.test.com"
        assert saved.license_key == "test-license-key"

@pytest.mark.asyncio
async def test_save_local_credentials_encrypted(test_client_db):
    """Verificar que las credenciales locales se guardan cifradas."""
    from app.database.db import client_engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    
    # Setup encryption
    crypto = EncryptionService()
    secret_data = {"username": "user", "password": "super-secret-password"}
    encrypted_str = crypto.encrypt(secret_data)

    async with AsyncSession(client_engine) as session:
        # Limpieza robusta ex-ante
        from sqlmodel import delete
        await session.execute(delete(LocalCredentials))
        await session.commit()

        # Guardar credencial
        cred = LocalCredentials(
            service_name="Gmail Test",
            encrypted_data=crypto.encrypt(secret_data)
        )
        session.add(cred)
        await session.commit()

        # Recuperar
        result = await session.execute(select(LocalCredentials).where(LocalCredentials.service_name == "Gmail Test"))
        saved = result.scalar_one()

        # Verificar que NO esta en texto plano en la BD (basic checks)
        assert "super-secret-password" not in saved.encrypted_data
        
        # Verificar descifrado
        decrypted = crypto.decrypt(saved.encrypted_data)
        assert decrypted == secret_data

@pytest.mark.asyncio
async def test_get_effective_security_policy(test_client_db):
    """Verificar lectura de politicas de seguridad (mock de cascading)."""
    # En este test solo verificamos que podemos leer el objeto policy por defecto
    from app.database.db import client_engine
    from sqlmodel.ext.asyncio.session import AsyncSession

    async with AsyncSession(client_engine) as session:
        # Crear policy por defecto si no existe (normalmente seed lo hace)
        policy = SecurityPolicy(
            name="Default Policy",
            allowed_domains='["example.com"]',
            max_execution_time=300
        )
        session.add(policy)
        await session.commit()

        result = await session.execute(select(SecurityPolicy))
        saved = result.scalars().first()
        
        allowed = json.loads(saved.allowed_domains)
        assert "example.com" in allowed

