
import pytest
import sys
import os
from unittest.mock import MagicMock

# Ensure paths are correct for imports
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "shared"))

# MOCK DEPENDENCIES BEFORE IMPORT
mock_state = MagicMock()
mock_state.i18n.t.side_effect = lambda x, **k: x # Return key as translation
sys.modules['app.core.state'] = MagicMock(state=mock_state)

# Mock NiceGUI ui to avoid runtime issues
sys.modules['nicegui'] = MagicMock()

# Ensure paths are correct for imports
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "shared"))
from datetime import datetime, timedelta
from automatia_shared.enums import LicenseStatus
from server.app.database.models import License
from server.app.ui.admin_page import get_status_color, get_status_label, admin_page_content

def test_admin_page_importable():
    """Verify the module and main function are importable."""
    assert callable(admin_page_content)

def test_get_status_color_active():
    """Active license with plenty of time/quota should be green."""
    lic = License(
        license_id="test", client_id="c1", 
        quota_tokens=1000, consumed_tokens=100,
        valid_until=datetime.utcnow() + timedelta(days=30),
        status=LicenseStatus.ACTIVE.value
    )
    assert get_status_color(lic) == "green"
    assert get_status_label(lic) == "ACTIVE"

def test_get_status_color_expired_date():
    """Expired by date should be red."""
    lic = License(
        license_id="test", client_id="c1",
        quota_tokens=1000, consumed_tokens=100,
        valid_until=datetime.utcnow() - timedelta(days=1),
        status=LicenseStatus.ACTIVE.value
    )
    assert get_status_color(lic) == "red"
    assert get_status_label(lic) == "EXPIRED"

def test_get_status_color_quota_exceeded():
    """Quota exceeded should be red."""
    lic = License(
        license_id="test", client_id="c1",
        quota_tokens=100, consumed_tokens=100,
        valid_until=datetime.utcnow() + timedelta(days=30),
        status=LicenseStatus.ACTIVE.value
    )
    assert get_status_color(lic) == "red"
    assert get_status_label(lic) == "QUOTA_EXCEEDED"

def test_get_status_color_expiring_soon():
    """Expiring in < 15 days should be orange."""
    lic = License(
        license_id="test", client_id="c1",
        quota_tokens=1000, consumed_tokens=100,
        valid_until=datetime.utcnow() + timedelta(days=10),
        status=LicenseStatus.ACTIVE.value
    )
    assert get_status_color(lic) == "orange"
    assert "EXPIRING_SOON" in get_status_label(lic)

def test_get_status_color_inactive():
    """Inactive license should be red (or whatever logic implies)."""
    lic = License(
        license_id="test", client_id="c1", 
        quota_tokens=1000, consumed_tokens=100, 
        valid_until=datetime.utcnow() + timedelta(days=30),
        status="SUSPENDED"
    )
    assert get_status_color(lic) == "red"
    assert get_status_label(lic) == "SUSPENDED"
