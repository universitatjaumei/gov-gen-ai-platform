import pytest
import sys
from unittest.mock import MagicMock, patch, AsyncMock

# Mock dependencies
sys.modules["client_app.app.modules.factory.report_factory"] = MagicMock()
sys.modules["client_app.app.services.report_analyzer_service"] = MagicMock()
sys.modules["client_app.app.core.state"] = MagicMock()
# Mock db session logic is tricky, usually done via context manager mock
# We'll patch ReportService imports directly in the test function setup 
# BUT since we use sys.modules, the imports in the service file are already mocked if we import it AFTER.
# Let's rely on patch inside test.

from client_app.app.services.report_service import ReportService
from client_app.app.database.models import ReportHistory

@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()
    # Context manager setup
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None
    
    # State db_session generator
    mock_state = sys.modules["client_app.app.core.state"].state
    mock_state.db_session.return_value = mock_session
    return mock_session

@pytest.mark.asyncio
async def test_service_generate_report_headless(mock_db_session):
    """Test full headless flow with AI analysis and persistence"""
    
    # Setup Service Mocks
    service = ReportService()
    
    # Mock Factory
    service.factory.generate_pdf = MagicMock()
    
    # Mock Analyzer
    service.analyzer.analyze_data = MagicMock(return_value={
        "introduction_text": "AI Info",
        "analysis_text": "AI Analysis"
    })
    
    context = {"title": "Test Report", "data": [1,2,3]}
    output_path = "/tmp/headless.pdf"
    
    # Execute
    result = await service.create_report_headless(
        context=context,
        template_name="template.html",
        output_path=output_path,
        run_analysis=True,
        analysis_instructions="Brief"
    )
    
    # Verifications
    
    # 1. Analysis called
    service.analyzer.analyze_data.assert_called_with(
        context=context,
        selection=None,
        user_instructions="Brief"
    )
    
    # 2. Context updated
    assert context["introduction_text"] == "AI Info"
    
    # 3. Factory called
    service.factory.generate_pdf.assert_called_with("template.html", context, output_path)
    
    # 4. Persistence
    # Check if session.add was called
    mock_db_session.add.assert_called()
    # Check return type
    assert isinstance(result, ReportHistory)
    assert result.status == "success"
