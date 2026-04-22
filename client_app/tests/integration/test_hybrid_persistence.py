
import pytest
import asyncio
import sys, os
from pathlib import Path
sys.path.append(os.getcwd()) # Ensure root is in path

from client_app.app.services.custom_script_service import custom_script_service, SCRIPTS_DIR, DOCS_DIR
from client_app.app.database.models import CustomScript

@pytest.mark.asyncio
async def test_hybrid_persistence():
    """Verifies that script is saved to disk and metadata to DB."""
    
    script_name = "Hybrid Test Script"
    script_code = "print('Hybrid Persistence')"
    script_desc = "Testing file separation"
    
    # Create Script
    created_script = await custom_script_service.create_script(
        name=script_name,
        user_prompt="Make hybrid",
        code=script_code,
        description=script_desc,
        execution_mode="hybrid"
    )
    
    # Verify DB
    assert created_script.id is not None
    assert created_script.script_path.endswith(".py")
    assert created_script.doc_path.endswith(".md")
    assert created_script.execution_mode == "hybrid"
    
    # Verify Disk
    py_path = SCRIPTS_DIR / created_script.script_path
    md_path = DOCS_DIR / created_script.doc_path
    
    assert py_path.exists()
    assert md_path.exists()
    
    with open(py_path, 'r') as f:
        assert f.read() == script_code
        
    with open(md_path, 'r') as f:
        content = f.read()
        assert script_name in content
        assert script_desc in content
        
    # Verify Retrieval loads form disk
    # First, modify disk content manually to prove it loads from disk
    new_code = "print('Modified on Disk')"
    with open(py_path, 'w') as f:
        f.write(new_code)
        
    retrieved = await custom_script_service.get_script(created_script.id)
    assert retrieved.code == new_code
    
    # Cleanup
    await custom_script_service.delete_script(created_script.id)
    assert not py_path.exists()
    assert not md_path.exists()
