"""
Pytest configuration for automatia-shared tests.
"""

import sys
from pathlib import Path

# Add shared package to path for testing without installation
shared_path = Path(__file__).parent.parent
sys.path.insert(0, str(shared_path))

import pytest


@pytest.fixture
def sample_flow_data():
    """Sample flow data for testing."""
    return {
        "name": "Test Flow",
        "description": "A test workflow",
        "trigger_type": "manual",
        "steps": [
            {
                "name": "Extract",
                "type": "extraction",
                "script_id": "script_001"
            }
        ]
    }


@pytest.fixture
def sample_license_data():
    """Sample license data for testing."""
    from datetime import datetime, timedelta
    return {
        "license_id": "lic_test_001",
        "client_id": "client_test",
        "partner_id": "partner_test",
        "quota_tokens": 100000,
        "consumed_tokens": 25000,
        "valid_until": datetime.utcnow() + timedelta(days=30),
        "status": "active"
    }
