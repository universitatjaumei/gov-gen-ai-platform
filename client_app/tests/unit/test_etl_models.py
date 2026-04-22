import pytest
from sqlmodel import select
from app.database.models import ETLJobHistory
from datetime import datetime

@pytest.mark.asyncio
async def test_etl_job_creation(db_session):
    """Verificar creación de ETLJobHistory."""
    job = ETLJobHistory(
        execution_id="etl_001",
        source_file="input.csv",
        source_format="csv",
        target_format="json",
        script_content="# test script\nimport pandas as pd\n",
        user_instructions="Renombrar columnas",
        status="draft"
    )
    db_session.add(job)
    await db_session.commit()
    
    # Verificar
    stmt = select(ETLJobHistory).where(ETLJobHistory.execution_id == "etl_001")
    result = await db_session.execute(stmt)
    saved = result.scalar_one()
    
    assert saved.source_file == "input.csv"
    assert saved.source_format == "csv"
    assert saved.target_format == "json"
    assert saved.status == "draft"
    assert saved.script_content == "# test script\nimport pandas as pd\n"
    assert saved.created_at is not None


@pytest.mark.asyncio
async def test_etl_job_update_status(db_session):
    """Verificar actualización de estado de job ETL."""
    job = ETLJobHistory(
        execution_id="etl_002",
        source_file="data.xlsx",
        source_format="excel",
        target_format="parquet",
        script_content="# conversion script",
        status="draft"
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    
    # Actualizar estado
    job.status = "validated"
    job.updated_at = datetime.utcnow()
    await db_session.commit()
    
    # Verificar
    stmt = select(ETLJobHistory).where(ETLJobHistory.execution_id == "etl_002")
    result = await db_session.execute(stmt)
    updated = result.scalar_one()
    
    assert updated.status == "validated"
    assert updated.updated_at is not None


@pytest.mark.asyncio
async def test_etl_job_with_result_summary(db_session):
    """Verificar almacenamiento de resumen de resultados."""
    import json
    
    result_summary = json.dumps({
        "rows_processed": 1000,
        "execution_time_ms": 1500,
        "output_size_bytes": 45000
    })
    
    job = ETLJobHistory(
        execution_id="etl_003",
        source_file="customers.csv",
        source_format="csv",
        target_format="json",
        script_content="# transform script",
        status="executed",
        result_summary=result_summary
    )
    db_session.add(job)
    await db_session.commit()
    
    # Verificar
    stmt = select(ETLJobHistory).where(ETLJobHistory.execution_id == "etl_003")
    result = await db_session.execute(stmt)
    saved = result.scalar_one()
    
    assert saved.result_summary is not None
    summary = json.loads(saved.result_summary)
    assert summary["rows_processed"] == 1000
    assert summary["execution_time_ms"] == 1500

