import sys
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

# Mock dependencies BEFORE importing the page that uses them
sys.modules["nicegui"] = MagicMock()
sys.modules["nicegui.ui"] = MagicMock()
# Mock services likely to fail or not needed for UI logic tests
sys.modules["client_app.app.services.report_analyzer_service"] = MagicMock()
sys.modules["client_app.app.modules.factory.report_factory"] = MagicMock()
# Also modules that crash if imported without environment
sys.modules["client_app.app.modules.privacy.anonymizer"] = MagicMock()

from client_app.app.ui.report_wizard_page import ReportWizardPage

# Start with a simple unit/integration test logic for the UI class logic
# Real browser E2E with Playwright might be too heavy for this step, 
# so we test the Logic of the Interface Class (ViewModel style) if possible,
# or mock the NiceGUI elements interaction.

@pytest.fixture
def mock_analyzer_service():
    with patch("client_app.app.ui.report_wizard_page.ReportAnalyzerService") as MockService:
        service_instance = MockService.return_value
        # Mock analyze_data to return a dict
        service_instance.analyze_data.return_value = {"introduction_text": "AI Generated Intro", "analysis_text": "AI Analysis"}
        yield service_instance

@pytest.fixture
def mock_report_factory():
    with patch("client_app.app.ui.report_wizard_page.ReportFactory") as MockFactory:
        factory_instance = MockFactory.return_value
        yield factory_instance

def test_wizard_step_initialization():
    """Verify wizard starts at step 1"""
    # We might need to mock nicegui.ui to instantiate the page without server
    with patch("nicegui.ui"):
        page = ReportWizardPage()
        # This assumes we check internal state or we'd need to inspect UI elements
        # For simplicity, let's assume the page has a 'current_step' logic variable
        assert page.current_step == 0 # 0-indexed usually

@pytest.mark.asyncio
async def test_wizard_run_analysis_append(mock_analyzer_service):
    """Verify that 'Append Analysis' adds text instead of replacing"""
    with patch("nicegui.ui"):
        page = ReportWizardPage()
        page.editor_content = "Existing content."
        
        # Simulate user selecting context and instructions
        page.selected_context_keys = ["table_1"]
        page.user_instructions = "More details"
        
        # Call the method triggered by "Append" button
        await page.run_analysis(append=True)
        
        # Verify service called with correct args
        mock_analyzer_service.analyze_data.assert_called_once()
        _, kwargs = mock_analyzer_service.analyze_data.call_args
        # Or args check
        
        # Verify content appended
        assert "Existing content." in page.editor_content
        assert "AI Generated Intro" in page.editor_content

@pytest.mark.asyncio
async def test_wizard_run_analysis_replace(mock_analyzer_service):
    """Verify that 'Regenerate' replaces text"""
    with patch("nicegui.ui"):
        page = ReportWizardPage()
        page.editor_content = "Existing content."
        
        await page.run_analysis(append=False)
        
        # Verify content replaced
        assert "Existing content." not in page.editor_content
        assert "AI Generated Intro" in page.editor_content

@pytest.mark.asyncio
async def test_wizard_generate_pdf(mock_report_factory):
    """Verify PDF generation call"""
    with patch("nicegui.ui"):
        page = ReportWizardPage()
        page.editor_content = "Final Report Content"
        page.selected_template = "template.html"
        
        await page.generate_report()
        
        mock_report_factory.generate_pdf.assert_called_once()
        # Check that editor content is passed in context
        call_args = mock_report_factory.generate_pdf.call_args
        context = call_args[0][1] # second arg
        assert context["introduction_text"] == "Final Report Content"
