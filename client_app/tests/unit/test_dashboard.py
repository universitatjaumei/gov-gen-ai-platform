import pytest
from sqlmodel import select
from app.database.models import ExtractionLog
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_dashboard_recent_activity(test_client_db):
    """Verificar que el dashboard recupera la actividad reciente correctamente."""
    from app.database.db import client_engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import delete

    async with AsyncSession(client_engine) as session:
        # Limpieza previa
        await session.execute(delete(ExtractionLog))
        await session.commit()

        # Crear logs de prueba (mezclados en fechas)
        logs = []
        for i in range(10):
            logs.append(ExtractionLog(
                filename=f"doc_{i}.pdf",
                service_used="test",
                model_used="model",
                input_tokens=100,
                output_tokens=10,
                status="success",
                timestamp=datetime.utcnow() - timedelta(minutes=i*10)
            ))
        session.add_all(logs)
        await session.commit()

        # Query Simulada del Dashboard
        stmt = select(ExtractionLog).order_by(ExtractionLog.timestamp.desc()).limit(5)
        result = await session.execute(stmt)
        recent = result.scalars().all()

        assert len(recent) == 5
        # El primero debe ser el mas reciente (doc_0)
        assert recent[0].filename == "doc_0.pdf"

@pytest.mark.asyncio
async def test_dashboard_stats(test_client_db):
    """Verificar calculo de estadisticas simples."""
    from app.database.db import client_engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import delete

    async with AsyncSession(client_engine) as session:
        # Limpieza previa
        await session.execute(delete(ExtractionLog))
        await session.commit()

        # 2 Exitos, 1 Fallo
        session.add(ExtractionLog(filename="ok1.pdf", status="success", input_tokens=0, output_tokens=0, service_used="s", model_used="m"))
        session.add(ExtractionLog(filename="ok2.pdf", status="success", input_tokens=0, output_tokens=0, service_used="s", model_used="m"))
        session.add(ExtractionLog(filename="err1.pdf", status="error", input_tokens=0, output_tokens=0, service_used="s", model_used="m"))
        await session.commit()

        # Query Stats
        total_stmt = select(ExtractionLog)
        total = len((await session.execute(total_stmt)).scalars().all())

        success_stmt = select(ExtractionLog).where(ExtractionLog.status == "success")
        success = len((await session.execute(success_stmt)).scalars().all())

        assert total == 3
        assert success == 2

