
import pytest
import asyncio
import sys, os
sys.path.append(os.getcwd()) # Ensure root is in path
from typing import Dict
from client_app.app.services.custom_script_service import custom_script_service
from client_app.app.database.models import CustomScript

@pytest.mark.asyncio
async def test_create_and_retrieve_script_with_contract():
    """Verifies that ui_contract is correctly persisted in the DB."""
    
    # Mock data
    dummy_contract = {
        "inputs": [
            {"name": "url", "type": "string", "label": "Target URL"},
            {"name": "retries", "type": "integer", "default": 3}
        ],
        "outputs": []
    }
    
    vis_config = {"chart_type": "bar"}
    
    # Create Script
    created_script = await custom_script_service.create_script(
        name="Integration Test Script",
        user_prompt="Test prompt",
        code="print('hello')",
        ui_contract=dummy_contract,
        execution_mode="local",
        visualization_config=vis_config
    )
    
    assert created_script.id is not None
    assert created_script.ui_contract == dummy_contract
    assert created_script.execution_mode == "local"
    
    # Retrieve Script
    retrieved_script = await custom_script_service.get_script(created_script.id)
    
    assert retrieved_script is not None
    assert retrieved_script.id == created_script.id
    # SQLAlchemy/SQLModel should deserialize JSON to dict automatically
    assert isinstance(retrieved_script.ui_contract, dict)
    assert retrieved_script.ui_contract["inputs"][0]["name"] == "url"
    assert retrieved_script.visualization_config == vis_config
    
    # Cleanup
    await custom_script_service.delete_script(created_script.id)
