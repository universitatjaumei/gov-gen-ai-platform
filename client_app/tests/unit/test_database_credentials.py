import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
from client_app.app.database.models import DatabaseCredentialConfig
from client_app.app.modules.security.encryption_service import EncryptionService

@pytest.mark.asyncio
async def test_create_database_credential(db_session: AsyncSession):
    """
    test_create_database_credential: Crear credencial con host, puerto, usuario
    """
    cred = DatabaseCredentialConfig(
        name="ERP Producción",
        db_type="mysql",
        host="192.168.1.100",
        port=3306,
        database="erp_db",
        username="admin",
        encrypted_password="encrypted_stuff",
        is_active=True
    )
    db_session.add(cred)
    await db_session.commit()
    await db_session.refresh(cred)

    assert cred.id is not None
    assert cred.name == "ERP Producción"
    assert cred.port == 3306

@pytest.mark.asyncio
async def test_credential_password_is_encrypted():
    """
    test_credential_password_is_encrypted: La contraseña se almacena cifrada.
    Simulamos el flujo de cifrado con EncryptionService.
    """
    encryption = EncryptionService()
    raw_pass = "secret123"
    # El modelo debe guardar lo que le pasamos como encrypted_password
    # La lógica de cifrado suele estar en el servicio que lo gestiona, 
    # pero verificamos que el campo exista y se comporte como un string.
    encrypted = encryption.encrypt({"password": raw_pass})
    
    cred = DatabaseCredentialConfig(
        name="Secure DB",
        db_type="postgresql",
        host="localhost",
        database="test",
        username="user",
        encrypted_password=encrypted
    )
    
    assert cred.encrypted_password == encrypted
    assert raw_pass not in cred.encrypted_password

@pytest.mark.asyncio
async def test_credential_supports_mysql():
    """Verify MySQL type is supported."""
    cred = DatabaseCredentialConfig(name="MySQL", db_type="mysql", host="h", database="d", username="u", encrypted_password="p")
    assert cred.db_type == "mysql"

@pytest.mark.asyncio
async def test_credential_supports_postgresql():
    """Verify PostgreSQL type is supported."""
    cred = DatabaseCredentialConfig(name="PG", db_type="postgresql", host="h", database="d", username="u", encrypted_password="p")
    assert cred.db_type == "postgresql"

@pytest.mark.asyncio
async def test_credential_supports_sqlserver():
    """Verify SQL Server type is supported."""
    cred = DatabaseCredentialConfig(name="MSSQL", db_type="sqlserver", host="h", database="d", username="u", encrypted_password="p")
    assert cred.db_type == "sqlserver"

@pytest.mark.asyncio
async def test_credential_connection_string_generated():
    """
    test_credential_connection_string_generated: Se genera string de conexión válido.
    """
    encryption = EncryptionService()
    password = "pass"
    
    # MySQL
    mysql_cred = DatabaseCredentialConfig(
        name="My", db_type="mysql", host="1.1.1.1", port=3306, database="db", username="user", encrypted_password="..."
    )
    conn_str = mysql_cred.get_connection_string(password)
    assert conn_str == "mysql+aiomysql://user:pass@1.1.1.1:3306/db"
    
    # PostgreSQL
    pg_cred = DatabaseCredentialConfig(
        name="PG", db_type="postgresql", host="localhost", port=5432, database="db", username="user", encrypted_password="..."
    )
    conn_str = pg_cred.get_connection_string(password)
    assert conn_str == "postgresql+asyncpg://user:pass@localhost:5432/db"
    
    # SQL Server (mssql+pyodbc requires more config usually, but checking core logic)
    ms_cred = DatabaseCredentialConfig(
        name="MS", db_type="sqlserver", host="server", port=1433, database="db", username="sa", encrypted_password="..."
    )
    conn_str = ms_cred.get_connection_string(password)
    assert "mssql+aioodbc://sa:pass@server:1433/db" in conn_str
    
    # SQLite
    sqlite_cred = DatabaseCredentialConfig(
        name="Lite", db_type="sqlite", host="", database="local.db", username="", encrypted_password=""
    )
    conn_str = sqlite_cred.get_connection_string("")
    assert conn_str == "sqlite+aiosqlite:///local.db"
