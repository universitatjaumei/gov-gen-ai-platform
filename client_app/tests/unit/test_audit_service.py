import pytest
from datetime import datetime, timedelta
import pandas as pd
from unittest.mock import AsyncMock, patch
from client_app.app.services.enterprise_audit_service import EnterpriseAuditService
from client_app.app.database.models import EnterpriseAuditLog, ActionType, RiskLevel

@pytest.fixture
def audit_service():
    return EnterpriseAuditService()

@pytest.mark.asyncio
async def test_log_extraction_event(audit_service):
    """Verifica el registro de un evento de extracción."""
    with patch('client_app.app.services.enterprise_audit_service.AsyncSession', autospec=True) as mock_session_cls:
        mock_session = mock_session_cls.return_value.__aenter__.return_value
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        await audit_service.log_event(
            action_type=ActionType.EXTRACTION,
            module="extraction_service",
            user_id="user_1",
            source_description="file.pdf"
        )
        
        assert mock_session.add.called
        args, _ = mock_session.add.call_args
        audit_entry = args[0]
        assert audit_entry.action_type == ActionType.EXTRACTION
        assert audit_entry.source_description == "file.pdf"

@pytest.mark.asyncio
async def test_log_pii_operation(audit_service):
    """Verifica el registro de una operación PII específica."""
    pii_data = {"names": 3, "dni": 1}
    with patch('client_app.app.services.enterprise_audit_service.AsyncSession', autospec=True) as mock_session_cls:
        mock_session = mock_session_cls.return_value.__aenter__.return_value
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        await audit_service.log_pii_operation(
            operation=ActionType.ANONYMIZATION,
            pii_types=pii_data,
            method="masking"
        )
        
        assert mock_session.add.called
        args, _ = mock_session.add.call_args
        audit_entry = args[0]
        assert audit_entry.action_type == ActionType.ANONYMIZATION
        assert audit_entry.pii_types == pii_data
        assert audit_entry.anonymization_method == "masking"

@pytest.mark.asyncio
async def test_query_logs_by_date_range(audit_service):
    """Verifica la consulta de logs por rango de fechas."""
    with patch('client_app.app.services.enterprise_audit_service.AsyncSession', autospec=True) as mock_session_cls:
        mock_session = mock_session_cls.return_value.__aenter__.return_value
        
        # Mock result set
        mock_results = AsyncMock()
        mock_results.all.return_value = [
            EnterpriseAuditLog(action_type="extraction"),
            EnterpriseAuditLog(action_type="export")
        ]
        mock_session.exec.return_value = mock_results
        
        start = datetime.now() - timedelta(days=1)
        end = datetime.now()
        
        logs = await audit_service.query_logs(start_date=start, end_date=end)
        
        assert len(logs) == 2
        assert mock_session.exec.called

@pytest.mark.asyncio
async def test_export_logs_to_dataframe(audit_service):
    """Verifica que los logs se conviertan correctamente a DataFrame."""
    logs = [
        EnterpriseAuditLog(id=1, action_type="extraction", module="core", risk_level="low"),
        EnterpriseAuditLog(id=2, action_type="export", module="ui", risk_level="medium")
    ]
    
    df = await audit_service.export_to_dataframe(logs)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "action_type" in df.columns
    assert df.iloc[0]["risk_level"] == "low"

@pytest.mark.asyncio
async def test_get_summary_stats(audit_service):
    """Verifica la generación de estadísticas agregadas."""
    with patch('client_app.app.services.enterprise_audit_service.AsyncSession', autospec=True) as mock_session_cls:
        mock_session = mock_session_cls.return_value.__aenter__.return_value
        
        # Mock results for stats
        mock_results = AsyncMock()
        mock_results.all.return_value = [
            EnterpriseAuditLog(risk_level=RiskLevel.HIGH.value),
            EnterpriseAuditLog(risk_level=RiskLevel.LOW.value)
        ]
        mock_session.exec.return_value = mock_results
        
        stats = await audit_service.get_summary_stats(
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now()
        )
        
        assert "total_count" in stats
        assert "high_risk_count" in stats
        assert stats["total_count"] == 2
        assert stats["high_risk_count"] == 1
