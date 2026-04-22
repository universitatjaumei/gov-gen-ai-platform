import pytest
import hashlib
from unittest.mock import MagicMock, AsyncMock, patch
from sqlmodel import select

# We will import the service after implementing it, for now we assume it exists
# or we can import the class if we implement the file skeleton first.
# To follow strict TDD Red, I should create the test first, which implies the import might fail 
# or I create the file with empty class.
# I will create the file with empty class first in the next step to avoid ImportErrors blocking the test collection.

# However, I can write the test assuming the service is available.
# But `pytest` collection will fail if module not found.
# So I will assume I'll create the file immediately after this.

# Target import:
# from client_app.app.services.custom_script_service import custom_script_service, CustomScriptService

@pytest.mark.asyncio
async def test_calculate_code_hash():
    from client_app.app.services.custom_script_service import CustomScriptService
    service = CustomScriptService()
    code = "print('hello')"
    expected_hash = hashlib.sha256(code.encode()).hexdigest()
    assert service.calculate_code_hash(code) == expected_hash

@pytest.mark.asyncio
async def test_create_script(test_client_db, tmp_path):
    """Test creating a script with valid data."""
    # We need to patch the client_engine inside the service to use our test engine
    # Patch everything that could cause side effects or hangs
    mock_scripts_dir = tmp_path / "scripts" / "src"
    mock_docs_dir = tmp_path / "scripts" / "docs"
    mock_scripts_dir.mkdir(parents=True)
    mock_docs_dir.mkdir(parents=True)

    with patch("client_app.app.services.custom_script_service.client_engine", test_client_db), \
         patch("client_app.app.services.custom_script_service.SCRIPTS_DIR", mock_scripts_dir), \
         patch("client_app.app.services.custom_script_service.DOCS_DIR", mock_docs_dir), \
         patch("client_app.app.services.script_library_service.script_library_service", AsyncMock()) as mock_lib:
        
        from client_app.app.services.custom_script_service import CustomScriptService
        from client_app.app.database.models import CustomScript
        
        service = CustomScriptService()
        # Since it's a singleton, we need to manually update its paths for the test
        service.scripts_dir = mock_scripts_dir
        service.docs_dir = mock_docs_dir
        
        script = await service.create_script(
            name="Test Script",
            user_prompt="Do something",
            code="import os",
            description="A test script",
            tags=["test"]
        )
        
        assert script.id is not None
        assert script.name == "Test Script"
        assert script.code_hash == hashlib.sha256("import os".encode()).hexdigest()
        assert script.status == "draft"

@pytest.mark.asyncio
async def test_get_script(test_client_db, tmp_path):
    """Test retrieving a script by ID."""
    mock_scripts_dir = tmp_path / "scripts" / "src"
    mock_docs_dir = tmp_path / "scripts" / "docs"
    mock_scripts_dir.mkdir(parents=True)
    mock_docs_dir.mkdir(parents=True)

    with patch("client_app.app.services.custom_script_service.client_engine", test_client_db), \
         patch("client_app.app.services.custom_script_service.SCRIPTS_DIR", mock_scripts_dir), \
         patch("client_app.app.services.custom_script_service.DOCS_DIR", mock_docs_dir), \
         patch("client_app.app.services.script_library_service.script_library_service", AsyncMock()):
        
        from client_app.app.services.custom_script_service import CustomScriptService
        service = CustomScriptService()
        service.scripts_dir = mock_scripts_dir
        service.docs_dir = mock_docs_dir
        
        # Create first
        created = await service.create_script(name="Find Me", user_prompt=".", code=".")
        
        # Get
        retrieved = await service.get_script(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Find Me"

@pytest.mark.asyncio
async def test_log_execution(test_client_db, tmp_path):
    """Test logging execution start and end."""
    mock_scripts_dir = tmp_path / "scripts" / "src"
    mock_docs_dir = tmp_path / "scripts" / "docs"
    mock_scripts_dir.mkdir(parents=True)
    mock_docs_dir.mkdir(parents=True)

    with patch("client_app.app.services.custom_script_service.client_engine", test_client_db), \
         patch("client_app.app.services.custom_script_service.SCRIPTS_DIR", mock_scripts_dir), \
         patch("client_app.app.services.custom_script_service.DOCS_DIR", mock_docs_dir), \
         patch("client_app.app.services.script_library_service.script_library_service", AsyncMock()):
        
        from client_app.app.services.custom_script_service import CustomScriptService
        service = CustomScriptService()
        service.scripts_dir = mock_scripts_dir
        service.docs_dir = mock_docs_dir
        
        script = await service.create_script(name="Exec Me", user_prompt=".", code=".")
        
        # Log Start
        exec_record = await service.log_execution_start(script.id, input_files=["in.txt"])
        assert exec_record.id is not None
        assert exec_record.status == "running"
        assert exec_record.started_at is not None
        
        # Log End
        await service.log_execution_end(
            execution_id=exec_record.id,
            status="success",
            output_files=["out.txt"],
            output_preview="Done"
        )
        
        # Verify update
        history = await service.get_execution_history(script.id)
        assert len(history) == 1
        assert history[0].status == "success"
        assert history[0].output_files == ["out.txt"]
        assert history[0].completed_at is not None
        
        # Verify Script Metrics Updated
        # (This usually happens in log_execution_end or separate generic update)
        updated_script = await service.get_script(script.id)
        assert updated_script.execution_count == 1
        assert updated_script.last_executed is not None

@pytest.mark.asyncio
async def test_toggle_favorite(test_client_db, tmp_path):
    """Test toggling favorite status."""
    mock_scripts_dir = tmp_path / "scripts" / "src"
    mock_docs_dir = tmp_path / "scripts" / "docs"
    mock_scripts_dir.mkdir(parents=True)
    mock_docs_dir.mkdir(parents=True)

    with patch("client_app.app.services.custom_script_service.client_engine", test_client_db), \
         patch("client_app.app.services.custom_script_service.SCRIPTS_DIR", mock_scripts_dir), \
         patch("client_app.app.services.custom_script_service.DOCS_DIR", mock_docs_dir), \
         patch("client_app.app.services.script_library_service.script_library_service", AsyncMock()):
        
        from client_app.app.services.custom_script_service import CustomScriptService
        service = CustomScriptService()
        service.scripts_dir = mock_scripts_dir
        service.docs_dir = mock_docs_dir
        
        script = await service.create_script(name="Fav Me", user_prompt=".", code=".")
        assert not script.is_favorite
        
        # Toggle ON
        await service.toggle_favorite(script.id)
        updated = await service.get_script(script.id)
        assert updated.is_favorite
        
        # Toggle OFF
        await service.toggle_favorite(script.id)
        updated = await service.get_script(script.id)
        assert not updated.is_favorite
