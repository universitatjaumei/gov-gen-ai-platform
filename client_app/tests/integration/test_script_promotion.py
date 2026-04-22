
import pytest
import asyncio
import sys, os
sys.path.append(os.getcwd())

from client_app.app.services.custom_script_service import custom_script_service, PromotionResult
from automatia_shared.security.ast_validator import RiskLevel

@pytest.mark.asyncio
async def test_promote_safe_script():
    """Safe script should be promoted successfully."""
    
    safe_code = """
import pandas as pd
import json

def process_data(df):
    return df.groupby('category').sum()
"""
    
    # Create script
    script = await custom_script_service.create_script(
        name="Safe Script",
        user_prompt="Process data",
        code=safe_code,
        description="Safe data processing"
    )
    
    assert script.status == "draft"
    
    # Promote to validated
    result = await custom_script_service.promote_script(script.id, "validated")
    
    assert result.success is True
    assert result.new_status == "validated"
    assert "promoted" in result.message.lower()
    
    # Verify status changed
    updated = await custom_script_service.get_script(script.id)
    assert updated.status == "validated"
    
    # Cleanup
    await custom_script_service.delete_script(script.id)


@pytest.mark.asyncio
async def test_promote_dangerous_script_fails():
    """Script with dangerous code should fail promotion."""
    
    dangerous_code = """
import os
import subprocess

def delete_everything():
    subprocess.call(['rm', '-rf', '/'])
    os.system('echo hacked')
"""
    
    # Create script
    script = await custom_script_service.create_script(
        name="Dangerous Script",
        user_prompt="Delete files",
        code=dangerous_code,
        description="Malicious script"
    )
    
    # Attempt promotion
    result = await custom_script_service.promote_script(script.id, "validated")
    
    assert result.success is False
    assert result.new_status == "draft"  # Should remain draft
    assert result.validation_result is not None
    assert result.validation_result.is_safe is False
    assert len(result.validation_result.violations) > 0
    assert "security validation failed" in result.message.lower()
    
    # Verify status unchanged
    updated = await custom_script_service.get_script(script.id)
    assert updated.status == "draft"
    
    # Cleanup
    await custom_script_service.delete_script(script.id)


@pytest.mark.asyncio
async def test_invalid_transition_rejected():
    """Invalid status transitions should be rejected."""
    
    script = await custom_script_service.create_script(
        name="Test Script",
        user_prompt="Test",
        code="print('test')",
        description="Test"
    )
    
    # Try to go directly from draft to published (should fail)
    result = await custom_script_service.promote_script(script.id, "published")
    
    assert result.success is False
    assert "invalid transition" in result.message.lower()
    
    # Cleanup
    await custom_script_service.delete_script(script.id)


@pytest.mark.asyncio
async def test_network_imports_configurable():
    """Network imports should be allowed with flag."""
    
    network_code = """
import requests

def fetch_data(url):
    return requests.get(url).json()
"""
    
    script = await custom_script_service.create_script(
        name="Network Script",
        user_prompt="Fetch data",
        code=network_code,
        description="API client"
    )
    
    # Should fail without allow_network
    result1 = await custom_script_service.promote_script(script.id, "validated", allow_network=False)
    assert result1.success is False
    
    # Should succeed with allow_network
    result2 = await custom_script_service.promote_script(script.id, "validated", allow_network=True)
    assert result2.success is True
    
    # Cleanup
    await custom_script_service.delete_script(script.id)
