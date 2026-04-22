
import pytest
import asyncio
import sys, os
sys.path.append(os.getcwd())

from client_app.app.services.script_library_service import script_library_service

@pytest.mark.asyncio
async def test_add_script_to_library():
    """Test adding script from different modules."""
    
    # Add ETL script
    etl_script = await script_library_service.add_script(
        source_module='etl',
        name='CSV to Excel Transformer',
        code='def transform(df): return df.rename(columns={"old": "new"})',
        description='Transforms CSV to Excel with column renaming',
        tags=['etl', 'transform'],
        user_prompt='Convert CSV to Excel and rename columns'
    )
    
    assert etl_script.id is not None
    assert etl_script.source_module == 'etl'
    assert etl_script.status == 'draft'
    assert etl_script.script_path.endswith('.py')
    
    # Verify file created
    from pathlib import Path
    script_file = Path('data/storage/scripts/src') / etl_script.script_path
    assert script_file.exists()
    
    # Cleanup
    await script_library_service.delete_script(etl_script.id)


@pytest.mark.asyncio
async def test_promote_script_with_validation():
    """Test script promotion with AST validation."""
    
    # Safe script
    safe_script = await script_library_service.add_script(
        source_module='graphics',
        name='Bar Chart Generator',
        code='import matplotlib.pyplot as plt\ndef plot(df): plt.bar(df.index, df.values)',
        description='Generates bar charts'
    )
    
    # Promote to validated
    result = await script_library_service.promote_script(safe_script.id, 'validated')
    assert result['success'] is True
    assert result['new_status'] == 'validated'
    
    # Dangerous script
    dangerous_script = await script_library_service.add_script(
        source_module='extraction',
        name='Malicious Extractor',
        code='import os\nos.system("rm -rf /")',
        description='Dangerous script'
    )
    
    # Attempt promotion - should fail
    result = await script_library_service.promote_script(dangerous_script.id, 'validated')
    assert result['success'] is False
    assert 'security validation failed' in result['message'].lower()
    assert 'violations' in result
    
    # Cleanup
    await script_library_service.delete_script(safe_script.id)
    await script_library_service.delete_script(dangerous_script.id)


@pytest.mark.asyncio
async def test_search_scripts_by_module():
    """Test searching scripts by source module."""
    
    # Add scripts from different modules
    custom = await script_library_service.add_script(
        source_module='custom',
        name='Custom Script 1',
        code='print("custom")',
        description='Custom script'
    )
    
    etl = await script_library_service.add_script(
        source_module='etl',
        name='ETL Script 1',
        code='def transform(df): return df',
        description='ETL script'
    )
    
    # Search by module
    custom_scripts = await script_library_service.search_scripts(source_module='custom')
    etl_scripts = await script_library_service.search_scripts(source_module='etl')
    
    assert any(s.id == custom.id for s in custom_scripts)
    assert any(s.id == etl.id for s in etl_scripts)
    assert not any(s.id == etl.id for s in custom_scripts)
    
    # Cleanup
    await script_library_service.delete_script(custom.id)
    await script_library_service.delete_script(etl.id)


@pytest.mark.asyncio
async def test_search_scripts_by_tags():
    """Test searching scripts by tags."""
    
    script1 = await script_library_service.add_script(
        source_module='graphics',
        name='Line Plot',
        code='def plot(): pass',
        description='Line plot',
        tags=['visualization', 'line']
    )
    
    script2 = await script_library_service.add_script(
        source_module='graphics',
        name='Bar Plot',
        code='def plot(): pass',
        description='Bar plot',
        tags=['visualization', 'bar']
    )
    
    # Search by tag
    viz_scripts = await script_library_service.search_scripts(tags=['visualization'])
    assert len(viz_scripts) >= 2
    
    line_scripts = await script_library_service.search_scripts(tags=['line'])
    assert any(s.id == script1.id for s in line_scripts)
    assert not any(s.id == script2.id for s in line_scripts)
    
    # Cleanup
    await script_library_service.delete_script(script1.id)
    await script_library_service.delete_script(script2.id)


@pytest.mark.asyncio
async def test_get_script_loads_code_from_disk():
    """Test that get_script loads code from disk."""
    
    original_code = 'def process(): return "data"'
    script = await script_library_service.add_script(
        source_module='extraction',
        name='Data Processor',
        code=original_code,
        description='Processes data'
    )
    
    # Retrieve script
    retrieved = await script_library_service.get_script(script.id)
    assert retrieved is not None
    assert hasattr(retrieved, 'code')
    assert retrieved.code == original_code
    
    # Cleanup
    await script_library_service.delete_script(script.id)
