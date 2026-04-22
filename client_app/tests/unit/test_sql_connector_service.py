import pytest
import pandas as pd
from unittest.mock import patch, AsyncMock
from client_app.app.services.sql_connector_service import SQLConnectorService
from client_app.app.database.models import DatabaseCredentialConfig

@pytest.fixture
def sql_service():
    return SQLConnectorService()

@pytest.mark.asyncio
async def test_connect_sqlite_success(sql_service, db_session):
    """test_connect_sqlite_success: Conexión a SQLite funciona"""
    cred = DatabaseCredentialConfig(
        name="SQLite Test",
        db_type="sqlite",
        host="",
        database=":memory:",
        username="",
        encrypted_password=""
    )
    db_session.add(cred)
    await db_session.commit()
    await db_session.refresh(cred)
    
    success, message = await sql_service.test_connection(cred.id)
    assert success is True, f"Connection failed: {message}"
    assert "conectado" in message.lower()

@pytest.mark.asyncio
async def test_execute_select_returns_dataframe(sql_service, db_session):
    """test_execute_select_returns_dataframe: SELECT devuelve pd.DataFrame"""
    cred = DatabaseCredentialConfig(
        name="SQLite Data",
        db_type="sqlite",
        host="",
        database=":memory:",
        username="",
        encrypted_password=""
    )
    db_session.add(cred)
    await db_session.commit()
    await db_session.refresh(cred)
    
    # Create a table and data
    await sql_service.execute_query(cred.id, "CREATE TABLE test (id INT, name TEXT)", allow_write=True)
    await sql_service.execute_query(cred.id, "INSERT INTO test VALUES (1, 'Alice')", allow_write=True)
    
    df = await sql_service.execute_query(cred.id, "SELECT * FROM test")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]['name'] == 'Alice'

@pytest.mark.asyncio
async def test_execute_insert_blocked_by_default(sql_service, db_session):
    """test_execute_insert_blocked_by_default: INSERT rechazado sin autorización"""
    cred = DatabaseCredentialConfig(
        name="SQLite Security",
        db_type="sqlite",
        host="",
        database=":memory:",
        username="",
        encrypted_password=""
    )
    db_session.add(cred)
    await db_session.commit()
    await db_session.refresh(cred)
    
    with pytest.raises(PermissionError) as excinfo:
        await sql_service.execute_query(cred.id, "INSERT INTO test VALUES (2, 'Bob')")
    assert "write operations not allowed" in str(excinfo.value).lower()

@pytest.mark.asyncio
async def test_query_with_parameters(sql_service, db_session):
    """test_query_with_parameters: Queries parametrizadas funcionan"""
    cred = DatabaseCredentialConfig(
        name="SQLite Params",
        db_type="sqlite",
        host="",
        database=":memory:",
        username="",
        encrypted_password=""
    )
    db_session.add(cred)
    await db_session.commit()
    await db_session.refresh(cred)
    
    await sql_service.execute_query(cred.id, "CREATE TABLE test (id INT, name TEXT)", allow_write=True)
    await sql_service.execute_query(cred.id, "INSERT INTO test VALUES (1, 'Alice')", allow_write=True)
    
    df = await sql_service.execute_query(cred.id, "SELECT * FROM test WHERE name = :name", params={"name": "Alice"})
    assert len(df) == 1

@pytest.mark.asyncio
async def test_get_tables(sql_service, db_session):
    """test_get_tables: Lista tablas disponibles"""
    cred = DatabaseCredentialConfig(
        name="SQLite Tables",
        db_type="sqlite",
        host="",
        database=":memory:",
        username="",
        encrypted_password=""
    )
    db_session.add(cred)
    await db_session.commit()
    await db_session.refresh(cred)
    
    await sql_service.execute_query(cred.id, "CREATE TABLE table1 (id INT)", allow_write=True)
    await sql_service.execute_query(cred.id, "CREATE TABLE table2 (id INT)", allow_write=True)
    
    tables = await sql_service.get_tables(cred.id)
    assert "table1" in tables
    assert "table2" in tables
