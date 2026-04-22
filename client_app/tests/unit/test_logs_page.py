import pytest
from sqlmodel import select
from app.database.models import ExtractionLog, TaskLog
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_list_extraction_logs(test_client_db):
    """Verificar que podemos listar logs de extraccion."""
    from app.database.db import client_engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    
    async with AsyncSession(client_engine) as db_session:
        # Crear log de prueba
        log = ExtractionLog(
            filename="test.pdf",
            service_used="GENERIC_LLM",
            model_used="gemini-2.0-flash",
            input_tokens=1000,
            output_tokens=500,
            estimated_cost=0.01,
            status="success",
            processing_time_seconds=5.2,
            extraction_result={"field1": "value1"}
        )
        db_session.add(log)
        await db_session.commit()

        # Listar
        result = await db_session.execute(select(ExtractionLog))
        logs = result.scalars().all()

        assert len(logs) >= 1
        assert logs[0].filename == "test.pdf"

@pytest.mark.asyncio
async def test_filter_logs_by_date(test_client_db):
    """Verificar filtrado por rango de fechas."""
    from app.database.db import client_engine
    from sqlmodel.ext.asyncio.session import AsyncSession

    async with AsyncSession(client_engine) as db_session:
        # Crear logs con diferentes fechas
        old_log = ExtractionLog(
            filename="old.pdf",
            service_used="test",
            model_used="test-model",
            input_tokens=100,
            output_tokens=50,
            status="success",
            created_at=datetime.utcnow() - timedelta(days=30),  # Note: created_at is not in the model definition in PROMPTS_MAESTROS but exists in file view? 
            # In file view `client_app/app/database/models.py`: 
            # created_at is NOT in ExtractionLog, it has `timestamp`
            timestamp=datetime.utcnow() - timedelta(days=30)
        )
        new_log = ExtractionLog(
            filename="new.pdf",
            service_used="test",
            model_used="test-model",
             input_tokens=100,
            output_tokens=50,
            status="success",
            timestamp=datetime.utcnow()
        )
        db_session.add_all([old_log, new_log])
        await db_session.commit()

        # Filtrar ultimos 7 dias
        week_ago = datetime.utcnow() - timedelta(days=7)
        result = await db_session.execute(
            select(ExtractionLog).where(ExtractionLog.timestamp >= week_ago)
        )
        recent_logs = result.scalars().all()

        assert any(l.filename == "new.pdf" for l in recent_logs)
        # Note: Depending on cleanup, old_log might be there or not 
        # But we check specific condition
        
        # Verify old log is NOT in recent logs
        assert not any(l.filename == "old.pdf" for l in recent_logs)

