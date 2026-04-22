import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

# Mock dependencies BEFORE importing service to avoid heavy initializations
with patch.dict(sys.modules, {
    'client_app.app.services.custom_script_service': MagicMock(),
    'client_app.app.services.external_script_audit_service': MagicMock(),
    'client_app.app.services.script_adaptation_service': MagicMock(),
}):
    # Now we can safely import, but we need to make sure the mocks have the right structure
    pass

from client_app.app.services.script_ingestion_service import (
    script_ingestion_service,
    IngestionResult
)
from client_app.app.services.external_script_audit_service import (
    AuditResult, AuditFinding, FindingSeverity
)
from client_app.app.services.script_adaptation_service import AdaptationResult

@pytest.mark.asyncio
async def test_ingest_safe_script():
    """Script seguro se registra correctamente"""
    code = "import pandas as pd\ndef transform(df):\n    return df"
    
    mock_audit = AuditResult(
        is_safe=True,
        can_proceed_with_review=True,
        findings=[],
        summary="Safe"
    )
    
    with patch('client_app.app.services.script_ingestion_service.external_script_audit_service.audit_script', return_value=mock_audit), \
         patch('client_app.app.services.script_ingestion_service.custom_script_service.create_script', new_callable=AsyncMock) as mock_create:
        
        mock_create.return_value = MagicMock(id=1)
        
        result = await script_ingestion_service.ingest_external_script(
            filename="safe.py",
            code=code
        )
        
        assert result.success
        assert result.status == "registered"
        assert result.script_id == 1
        assert not result.adaptation_applied
        
        # Verify passed to create_script
        args, kwargs = mock_create.call_args
        assert kwargs['status'] == "DRAFT"
        assert kwargs['requires_review'] is False

@pytest.mark.asyncio
async def test_ingest_blocks_dangerous():
    """Script peligroso es rechazado"""
    code = "import os\nos.system('rm -rf')"
    
    mock_audit = AuditResult(
        is_safe=False,
        can_proceed_with_review=False,
        findings=[AuditFinding(1, "os.system", "Blocked", FindingSeverity.BLOCKED)],
        summary="Blocked"
    )
    
    with patch('client_app.app.services.script_ingestion_service.external_script_audit_service.audit_script', return_value=mock_audit), \
         patch('client_app.app.services.script_ingestion_service.custom_script_service.create_script', new_callable=AsyncMock) as mock_create:
        
        result = await script_ingestion_service.ingest_external_script(
            filename="dangerous.py",
            code=code
        )
        
        assert not result.success
        assert result.status == "rejected"
        assert result.script_id is None
        mock_create.assert_not_called()

@pytest.mark.asyncio
async def test_ingest_with_warnings_requires_review():
    """Script con warnings queda pendiente de revisión"""
    code = "import requests"
    
    mock_audit = AuditResult(
        is_safe=False,
        can_proceed_with_review=True,
        findings=[AuditFinding(1, "requests", "Warning", FindingSeverity.WARNING)],
        summary="Warning"
    )
    
    with patch('client_app.app.services.script_ingestion_service.external_script_audit_service.audit_script', return_value=mock_audit), \
         patch('client_app.app.services.script_ingestion_service.custom_script_service.create_script', new_callable=AsyncMock) as mock_create:
        
        mock_create.return_value = MagicMock(id=2)
        
        result = await script_ingestion_service.ingest_external_script(
            filename="warning.py",
            code=code
        )
        
        assert result.success
        assert result.status == "pending_review"
        
        # Verify passed to create_script
        args, kwargs = mock_create.call_args
        assert kwargs['status'] == "DRAFT"
        assert kwargs['requires_review'] is True

@pytest.mark.asyncio
async def test_ingest_with_adaptation():
    """Script adaptado por IA se registra"""
    code = "import pandas"
    adapted_code = "import pandas as pd\n# Adapted"
    
    mock_audit = AuditResult(is_safe=True, can_proceed_with_review=True, findings=[], summary="OK")
    mock_adaptation = AdaptationResult(success=True, adapted_code=adapted_code, preview="...")
    
    with patch('client_app.app.services.script_ingestion_service.external_script_audit_service.audit_script', return_value=mock_audit), \
         patch('client_app.app.services.script_ingestion_service.script_adaptation_service.adapt_to_platform', new_callable=AsyncMock, return_value=mock_adaptation), \
         patch('client_app.app.services.script_ingestion_service.custom_script_service.create_script', new_callable=AsyncMock) as mock_create:
        
        mock_create.return_value = MagicMock(id=3)
        
        result = await script_ingestion_service.ingest_external_script(
            filename="raw.py",
            code=code,
            auto_adapt=True
        )
        
        assert result.success
        assert result.adaptation_applied
        
        # Verify adapted code was saved
        args, kwargs = mock_create.call_args
        assert kwargs['code'] == adapted_code

@pytest.mark.asyncio
async def test_ingested_script_has_hash():
    """Script registrado tiene code_hash calculado"""
    code = "content"
    mock_audit = AuditResult(is_safe=True, can_proceed_with_review=True, findings=[], summary="OK")
    
    with patch('client_app.app.services.script_ingestion_service.external_script_audit_service.audit_script', return_value=mock_audit), \
         patch('client_app.app.services.script_ingestion_service.custom_script_service.create_script', new_callable=AsyncMock) as mock_create:
        
        await script_ingestion_service.ingest_external_script("test.py", code)
        
        args, kwargs = mock_create.call_args
        assert 'code_hash' in kwargs
        assert len(kwargs['code_hash']) == 64  # SHA256 hex length
