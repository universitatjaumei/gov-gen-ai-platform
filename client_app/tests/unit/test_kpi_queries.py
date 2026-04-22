import pytest
from sqlmodel import select, func
from client_app.app.database.models import (
    ExtractionLog, FlowRegistry, TaskLog, RunManifestLog, ScriptLibrary
)
from automatia_shared.core.audit_models import EnterpriseAuditLog
from datetime import datetime, timedelta
from sqlmodel.ext.asyncio.session import AsyncSession

@pytest.mark.asyncio
async def test_kpi_counting_logic(test_client_db):
    """Verifica que las consultas de KPIs cuentan correctamente los registros."""
    from client_app.app.database.db import client_engine
    
    async with AsyncSession(client_engine) as session:
        # 1. Setup Data
        # Flows & Atoms
        session.add(FlowRegistry(name="Flow 1", steps="[]"))
        session.add(ScriptLibrary(name="Atom 1", source_module="custom", script_path="path1", code_hash="h1"))
        session.add(ScriptLibrary(name="Atom 2", source_module="custom", script_path="path2", code_hash="h2"))
        
        # Success Rate
        session.add(TaskLog(execution_id="e1", step_index=0, step_name="s", status="success"))
        session.add(ExtractionLog(filename="f1", status="success", input_tokens=0, output_tokens=0, service_used="s", model_used="m"))
        session.add(ExtractionLog(filename="f2", status="error", input_tokens=0, output_tokens=0, service_used="s", model_used="m"))

        # Activity (30d)
        session.add(RunManifestLog(execution_id="r1", service_id="s1", model_used="m", created_at=datetime.utcnow()))
        session.add(RunManifestLog(execution_id="r2", service_id="s2", model_used="m", created_at=datetime.utcnow() - timedelta(days=31)))
        
        # Privacy
        session.add(EnterpriseAuditLog(action_type="anonymize", module="m", pii_protected_count=10))
        session.add(EnterpriseAuditLog(action_type="anonymize", module="m", pii_protected_count=5))
        
        await session.commit()

        # 2. Verify Queries (Matching dashboard_page.py logic)
        flows_count = (await session.execute(select(func.count(FlowRegistry.id)))).scalar_one()
        atoms_count = (await session.execute(select(func.count(ScriptLibrary.id)))).scalar_one()
        assert flows_count == 1
        assert atoms_count == 2

        task_total = (await session.execute(select(func.count(TaskLog.id)))).scalar_one()
        task_success = (await session.execute(select(func.count(TaskLog.id)).where(TaskLog.status == 'success'))).scalar_one()
        extr_total = (await session.execute(select(func.count(ExtractionLog.id)))).scalar_one()
        extr_success = (await session.execute(select(func.count(ExtractionLog.id)).where(ExtractionLog.status == 'success'))).scalar_one()
        
        total_execs = task_total + extr_total
        total_ok = task_success + extr_success
        success_rate = int((total_ok / total_execs) * 100)
        assert total_execs == 3
        assert total_ok == 2
        assert success_rate == 66

        cutoff_30d = datetime.utcnow() - timedelta(days=30)
        activity_30d = (await session.execute(select(func.count(RunManifestLog.id)).where(RunManifestLog.created_at >= cutoff_30d))).scalar_one()
        assert activity_30d == 1

        pii_protected = (await session.execute(select(func.sum(EnterpriseAuditLog.pii_protected_count)))).scalar_one()
        assert pii_protected == 15
