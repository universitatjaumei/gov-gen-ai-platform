
import pytest
import asyncio
import sys, os
sys.path.append(os.getcwd())

from client_app.app.services.custom_script_service import custom_script_service
from client_app.app.services.script_library_service import script_library_service
from client_app.app.database.models import ScriptLibrary

@pytest.mark.asyncio
async def test_custom_script_creation_syncs_to_library():
    """Test that creating a CustomScript also creates a ScriptLibrary entry."""
    
    unique_name = f"Sync Test Script {os.urandom(4).hex()}"
    
    # 1. Create Custom Script
    script = await custom_script_service.create_script(
        name=unique_name,
        user_prompt="Print hello",
        code="print('Hello World')",
        description="Testing sync",
        tags=["sincronizacion"]
    )
    
    assert script.id is not None
    
    # 2. Check Script Library
    library_scripts = await script_library_service.search_scripts(
        source_module='custom',
        query=unique_name
    )
    
    assert len(library_scripts) > 0
    lib_script = library_scripts[0]
    
    assert lib_script.name == unique_name
    assert lib_script.source_automation_id == script.id
    assert lib_script.code_hash == script.code_hash
    
    # Cleanup
    await custom_script_service.delete_script(script.id)
    await script_library_service.delete_script(lib_script.id)


@pytest.mark.asyncio
async def test_custom_script_update_syncs_to_library():
    """Test that updating a CustomScript updates the ScriptLibrary entry."""
    
    unique_name = f"Update Test Script {os.urandom(4).hex()}"

    # 1. Create
    script = await custom_script_service.create_script(
        name=unique_name,
        user_prompt="Original",
        code="print('Original')",
        description="Original desc"
    )
    
    # 2. Update
    new_code = "print('Updated')"
    updated_script = await custom_script_service.update_script(
        script.id,
        code=new_code,
        description="Updated desc"
    )
    
    # 3. Verify Library Sync
    library_scripts = await script_library_service.search_scripts(
        source_module='custom',
        query=unique_name
    )
    assert len(library_scripts) == 1
    lib_script = library_scripts[0]
    
    loaded_lib_script = await script_library_service.get_script(lib_script.id)
    
    assert loaded_lib_script.description == "Updated desc"
    assert loaded_lib_script.code == new_code
    
    # Cleanup
    await custom_script_service.delete_script(script.id)
    await script_library_service.delete_script(lib_script.id)


@pytest.mark.asyncio
async def test_custom_script_promotion_syncs_to_library():
    """Test that promoting CustomScript updates ScriptLibrary status."""
    
    unique_name = f"Promotion Test Script {os.urandom(4).hex()}"

    # 1. Create safe script
    script = await custom_script_service.create_script(
        name=unique_name,
        user_prompt="Safe code",
        code="x = 1"
        # status arg removed
    )
    
    # 2. Promote to validated
    result = await custom_script_service.promote_script(script.id, "validated")
    assert result.success is True
    assert result.new_status == "validated"
    
    # 3. Verify Library Status
    library_scripts = await script_library_service.search_scripts(
        source_module='custom',
        query=unique_name
    )
    assert len(library_scripts) == 1
    lib_script = library_scripts[0]
    
    assert lib_script.status == "validated"
    
    # Cleanup
    await custom_script_service.delete_script(script.id)
    await script_library_service.delete_script(lib_script.id)
