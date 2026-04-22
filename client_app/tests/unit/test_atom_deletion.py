"""
Unit tests for atom deletion feature with dependency checking.
Tests the get_atom_dependencies and delete_script methods.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.models import ScriptLibrary, FlowRegistry
from client_app.app.services.script_library_service import script_library_service
from client_app.app.database.db import client_engine


@pytest.fixture
async def test_script():
    """Create a test script in the library."""
    async with AsyncSession(client_engine) as session:
        script = ScriptLibrary(
            source_module="custom",
            name="Test Script",
            description="Test script for deletion",
            tags=["test"],
            script_path="test_script.py",
            doc_path="test_script.md",
            code_hash="test_hash_123",
            status="published"
        )
        session.add(script)
        await session.commit()
        await session.refresh(script)
        
        # Create physical files
        scripts_dir = Path("data/storage/scripts/src")
        docs_dir = Path("data/storage/scripts/docs")
        scripts_dir.mkdir(parents=True, exist_ok=True)
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        (scripts_dir / script.script_path).write_text("# Test script")
        (docs_dir / script.doc_path).write_text("# Test documentation")
        
        yield script
        
        # Cleanup
        try:
            (scripts_dir / script.script_path).unlink(missing_ok=True)
            (docs_dir / script.doc_path).unlink(missing_ok=True)
            await session.delete(script)
            await session.commit()
        except:
            pass


@pytest.fixture
async def test_flow_with_dependency(test_script):
    """Create a test flow that depends on the test script."""
    async with AsyncSession(client_engine) as session:
        steps = [
            {
                "name": "Test Step",
                "type": "custom_script",
                "script_id": str(test_script.id),
                "config": {}
            }
        ]
        
        flow = FlowRegistry(
            name="Test Flow",
            description="Test flow with dependency",
            version="1.0.0",
            status="PUBLISHED",
            trigger_type="manual",
            trigger_config="{}",
            steps=json.dumps(steps),
            is_active=True
        )
        session.add(flow)
        await session.commit()
        await session.refresh(flow)
        
        yield flow
        
        # Cleanup
        try:
            await session.delete(flow)
            await session.commit()
        except:
            pass


@pytest.mark.asyncio
async def test_delete_atom_no_dependencies(test_script):
    """Test deleting an atom with no dependencies."""
    # Verify script exists
    script = await script_library_service.get_script(test_script.id)
    assert script is not None
    assert script.name == "Test Script"
    
    # Check dependencies (should be none)
    deps = await script_library_service.get_atom_dependencies(test_script.id)
    assert deps['count'] == 0
    assert len(deps['flows']) == 0
    
    # Delete script
    result = await script_library_service.delete_script(test_script.id)
    assert result is True
    
    # Verify script is deleted
    script = await script_library_service.get_script(test_script.id)
    assert script is None
    
    # Verify files are deleted
    scripts_dir = Path("data/storage/scripts/src")
    docs_dir = Path("data/storage/scripts/docs")
    assert not (scripts_dir / test_script.script_path).exists()
    assert not (docs_dir / test_script.doc_path).exists()


@pytest.mark.asyncio
async def test_get_atom_dependencies_with_flows(test_script, test_flow_with_dependency):
    """Test getting dependencies when a flow uses the atom."""
    deps = await script_library_service.get_atom_dependencies(test_script.id)
    
    assert deps['count'] == 1
    assert len(deps['flows']) == 1
    
    flow_dep = deps['flows'][0]
    assert flow_dep['id'] == test_flow_with_dependency.id
    assert flow_dep['name'] == "Test Flow"
    assert 'Test Step' in flow_dep['step_names']


@pytest.mark.asyncio
async def test_delete_atom_with_dependencies_no_force(test_script, test_flow_with_dependency):
    """Test that deleting an atom with dependencies fails without force."""
    # Attempt to delete without force
    with pytest.raises(ValueError) as exc_info:
        await script_library_service.delete_script(test_script.id, force=False)
    
    assert "Cannot delete" in str(exc_info.value)
    assert "Test Flow" in str(exc_info.value)
    
    # Verify script still exists
    script = await script_library_service.get_script(test_script.id)
    assert script is not None


@pytest.mark.asyncio
async def test_delete_atom_force_with_dependencies(test_script, test_flow_with_dependency):
    """Test force deleting an atom even with dependencies."""
    # Force delete
    result = await script_library_service.delete_script(test_script.id, force=True)
    assert result is True
    
    # Verify script is deleted
    script = await script_library_service.get_script(test_script.id)
    assert script is None
    
    # Verify flow still exists (but with broken dependency)
    async with AsyncSession(client_engine) as session:
        flow = await session.get(FlowRegistry, test_flow_with_dependency.id)
        assert flow is not None
        assert flow.name == "Test Flow"


@pytest.mark.asyncio
async def test_get_dependencies_nonexistent_script():
    """Test getting dependencies for a non-existent script."""
    deps = await script_library_service.get_atom_dependencies(99999)
    assert deps['count'] == 0
    assert len(deps['flows']) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_script():
    """Test deleting a non-existent script."""
    result = await script_library_service.delete_script(99999)
    assert result is False


@pytest.mark.asyncio
async def test_dependency_check_with_config_reference(test_script):
    """Test dependency detection when script_id is in config instead of top-level."""
    async with AsyncSession(client_engine) as session:
        steps = [
            {
                "name": "Config Step",
                "type": "custom_script",
                "config": {
                    "script_id": str(test_script.id),
                    "other_param": "value"
                }
            }
        ]
        
        flow = FlowRegistry(
            name="Config Flow",
            description="Flow with config reference",
            version="1.0.0",
            status="PUBLISHED",
            trigger_type="manual",
            trigger_config="{}",
            steps=json.dumps(steps),
            is_active=True
        )
        session.add(flow)
        await session.commit()
        await session.refresh(flow)
        
        try:
            # Check dependencies
            deps = await script_library_service.get_atom_dependencies(test_script.id)
            assert deps['count'] == 1
            assert deps['flows'][0]['name'] == "Config Flow"
        finally:
            # Cleanup
            await session.delete(flow)
            await session.commit()
