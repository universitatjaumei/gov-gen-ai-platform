import pytest
from unittest.mock import MagicMock, patch
import sys
from datetime import datetime

# Mock necessary modules to avoid runtime errors on import
sys.modules["nicegui"] = MagicMock()
sys.modules["nicegui.ui"] = MagicMock()
sys.modules["client_app.app.core.state"] = MagicMock()

from client_app.app.database.models import ReportHistory

def test_report_history_model():
    """Verify ReportHistory model instantiation (R-05 requirements)"""
    report = ReportHistory(
        report_name="Test Report",
        pdf_path="/tmp/test.pdf",
        template_used="basic.html",
        generated_at=datetime.utcnow()
    )
    assert report.report_name == "Test Report"
    assert report.status == "success"

def test_dashboard_import_sanity():
    """Verify dashboard_page imports without error (syntax check)"""
    try:
        from client_app.app.ui import dashboard_page
        assert True
    except ImportError as e:
        pytest.fail(f"Dashboard failed to import: {e}")

