import pytest
from sqlmodel import select
from client_app.app.database.models import CustomScript, CustomScriptExecution
from datetime import datetime

# Fixture to provide a db_session (Assuming it relies on conftest.py configuration)
# If conftest.py is providing 'db_session' fixture properly, we can just use it.

@pytest.mark.asyncio
async def test_custom_script_creation(db_session):
    """Verificar creación de CustomScript."""
    script = CustomScript(
        name="Analisis Ventas",
        description="Analiza archivo CSV",
        user_prompt="Analizar ventas del mes",
        tags=["ventas", "csv"],
        code="import pandas as pd...",
        code_hash="sha256hash...",
        required_libraries=["pandas"],
        input_type="file",
        input_extensions=[".csv"],
        output_type="chart",
        status="draft"
    )
    db_session.add(script)
    await db_session.commit()
    
    # Verificar
    stmt = select(CustomScript).where(CustomScript.name == "Analisis Ventas")
    result = await db_session.execute(stmt)
    saved = result.scalar_one()
    
    assert saved.description == "Analiza archivo CSV"
    assert saved.tags == ["ventas", "csv"]
    assert saved.required_libraries == ["pandas"]
    assert saved.status == "draft"
    assert saved.created_at is not None
    assert saved.execution_count == 0

@pytest.mark.asyncio
async def test_custom_script_execution_creation(db_session):
    """Verificar creación de CustomScriptExecution."""
    # Primero creamos un script
    script = CustomScript(
        name="Script Test Exec",
        description="Test Execution",
        user_prompt="Run test",
        code="print('hello')",
        code_hash="hash123",
        status="published"
    )
    db_session.add(script)
    await db_session.commit()
    await db_session.refresh(script)

    # Crear ejecución
    execution = CustomScriptExecution(
        script_id=script.id,
        status="running",
        input_files=["data.csv"],
        started_at=datetime.utcnow()
    )
    db_session.add(execution)
    await db_session.commit()
    
    # Verificar
    stmt = select(CustomScriptExecution).where(CustomScriptExecution.script_id == script.id)
    result = await db_session.execute(stmt)
    saved_exec = result.scalar_one()
    
    assert saved_exec.status == "running"
    assert saved_exec.input_files == ["data.csv"]
    assert saved_exec.script_id == script.id
    assert saved_exec.duration_ms == 0

@pytest.mark.asyncio
async def test_custom_script_relationships(db_session):
    """Verificar foreign key relationship (implícito por script_id)."""
    script = CustomScript(
        name="Relational Script",
        user_prompt="Simple prompt",
        code="pass",
        code_hash="abc",
    )
    db_session.add(script)
    await db_session.commit()
    await db_session.refresh(script)
    
    execution = CustomScriptExecution(
        script_id=script.id,
        status="success"
    )
    db_session.add(execution)
    await db_session.commit()
    
    # Check retrieval
    stmt = select(CustomScriptExecution).where(CustomScriptExecution.script_id == script.id)
    result = await db_session.execute(stmt)
    execs = result.scalars().all()
    assert len(execs) == 1
    assert execs[0].status == "success"
