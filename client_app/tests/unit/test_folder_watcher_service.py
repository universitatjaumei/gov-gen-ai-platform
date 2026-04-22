import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Assuming this will fail initially
from client_app.app.services.folder_watcher_service import FolderWatcherService
from client_app.app.database.models import FolderWatcherConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

@pytest.fixture
def mock_workflow_engine():
    """Mock del WorkflowEngine."""
    engine = AsyncMock()
    engine.execute_flow = AsyncMock(return_value="exec_123")
    return engine

@pytest.fixture
async def persistent_db():
    """Persistent in-memory DB for service tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        
    yield engine
    await engine.dispose()

@pytest.fixture
def service(persistent_db):
    """Fixture para crear servicio limpio con DB mockeada."""
    # Patch the engine used in the service with our persistent test engine
    # AND Patch FolderWatcher to avoid real watchdog usage
    with patch("client_app.app.services.folder_watcher_service.client_engine", persistent_db), \
         patch("client_app.app.services.folder_watcher_service.FolderWatcher") as MockWatcher:
        
        # Setup mock behavior
        mock_instance = MockWatcher.return_value
        # start_monitoring is async, so return_value must be awaitable or AsyncMock
        mock_instance.start_monitoring = AsyncMock()
        mock_instance.stop = MagicMock()
        
        svc = FolderWatcherService()
        yield svc

class TestFolderWatcherServiceCRUD:
    """Tests CRUD de configuraciones."""

    @pytest.mark.asyncio
    async def test_create_config(self, service):
        """Crear nueva configuración de watcher."""
        config_data = {
            "name": "Facturas Entrada",
            "watch_path": "/data/input",
            "file_patterns": "*.pdf,*.xml",
            "flow_id": 1,
            "recursive": False
        }

        config_id = await service.create_config(config_data)

        assert config_id is not None
        assert config_id > 0

    @pytest.mark.asyncio
    async def test_get_config(self, service):
        """Obtener configuración por ID."""
        # Crear primero
        config_data = {"name": "Test", "watch_path": "/tmp", "flow_id": 1}
        config_id = await service.create_config(config_data)

        # Obtener
        config = await service.get_config(config_id)

        assert config is not None
        assert config["name"] == "Test"
        assert config["watch_path"] == "/tmp"

    @pytest.mark.asyncio
    async def test_list_configs(self, service):
        """Listar todas las configuraciones."""
        # Crear 2 configs
        await service.create_config({"name": "A", "watch_path": "/a", "flow_id": 1})
        await service.create_config({"name": "B", "watch_path": "/b", "flow_id": 2})

        configs = await service.list_configs()

        assert len(configs) >= 2

    @pytest.mark.asyncio
    async def test_update_config(self, service):
        """Actualizar configuración existente."""
        config_id = await service.create_config({
            "name": "Original",
            "watch_path": "/original",
            "flow_id": 1
        })

        success = await service.update_config(config_id, {
            "name": "Updated",
            "file_patterns": "*.csv"
        })

        assert success is True

        config = await service.get_config(config_id)
        assert config["name"] == "Updated"
        assert config["file_patterns"] == "*.csv"

    @pytest.mark.asyncio
    async def test_delete_config(self, service):
        """Eliminar configuración."""
        config_id = await service.create_config({
            "name": "ToDelete",
            "watch_path": "/delete",
            "flow_id": 1
        })

        success = await service.delete_config(config_id)

        assert success is True

        config = await service.get_config(config_id)
        assert config is None

    @pytest.mark.asyncio
    async def test_delete_active_config_stops_watcher(self, service, mock_workflow_engine):
        """Eliminar config activa debe detener el watcher primero."""
        config_id = await service.create_config({
            "name": "Active",
            "watch_path": "/active",
            "flow_id": 1,
            "is_active": True
        })

        # Simular que está corriendo
        service._running_watchers = {config_id: MagicMock()}
        # Mock stop_watcher to avoid actual logic, we just want to verify logic flow but delete_config
        # calls stop_watcher which we want to test.
        # But here we want to ensure delete_config logic calls stop.
        # Let's rely on actual stop_watcher logic or mock it?
        # The prompt test mocked _running_watchers.
        # Let's use patch to spy on stop_watcher
        
        with patch.object(service, "stop_watcher", new_callable=AsyncMock) as mock_stop:
             success = await service.delete_config(config_id)
             mock_stop.assert_called_with(config_id)

        assert success is True


class TestFolderWatcherServiceLifecycle:
    """Tests de ciclo de vida de watchers."""

    @pytest.mark.asyncio
    async def test_start_watcher(self, service, mock_workflow_engine, tmp_path):
        """Iniciar un watcher."""
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        config_id = await service.create_config({
            "name": "Test",
            "watch_path": str(watch_dir),
            "flow_id": 1
        })
        
        service.set_workflow_engine(mock_workflow_engine)
        success, message = await service.start_watcher(config_id)

        assert success is True
        assert "started" in message.lower()

        # Limpiar
        await service.stop_watcher(config_id)

    @pytest.mark.asyncio
    async def test_start_nonexistent_config(self, service):
        """Iniciar watcher con config inexistente falla."""
        success, message = await service.start_watcher(99999)

        assert success is False
        assert "not found" in message.lower()

    @pytest.mark.asyncio
    async def test_start_already_running(self, service, mock_workflow_engine, tmp_path):
        """Iniciar watcher ya corriendo falla."""
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        config_id = await service.create_config({
            "name": "Test",
            "watch_path": str(watch_dir),
            "flow_id": 1
        })

        service.set_workflow_engine(mock_workflow_engine)
        await service.start_watcher(config_id)
        success, message = await service.start_watcher(config_id)

        assert success is False
        assert "already running" in message.lower()

        await service.stop_watcher(config_id)

    @pytest.mark.asyncio
    async def test_stop_watcher(self, service, mock_workflow_engine, tmp_path):
        """Detener un watcher."""
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        config_id = await service.create_config({
            "name": "Test",
            "watch_path": str(watch_dir),
            "flow_id": 1
        })

        service.set_workflow_engine(mock_workflow_engine)
        await service.start_watcher(config_id)
        success, message = await service.stop_watcher(config_id)

        assert success is True
        assert "stopped" in message.lower()

    @pytest.mark.asyncio
    async def test_stop_not_running(self, service):
        """Detener watcher no corriendo falla."""
        config_id = await service.create_config({
            "name": "Test",
            "watch_path": "/tmp",
            "flow_id": 1
        })

        success, message = await service.stop_watcher(config_id)

        assert success is False
        assert "not running" in message.lower()

    @pytest.mark.asyncio
    async def test_get_status(self, service, mock_workflow_engine, tmp_path):
        """Obtener estado del servicio."""
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        config_id = await service.create_config({
            "name": "Test",
            "watch_path": str(watch_dir),
            "flow_id": 1
        })

        service.set_workflow_engine(mock_workflow_engine)
        await service.start_watcher(config_id)
        status = await service.get_status()

        assert status["active_watchers"] >= 1
        assert config_id in status["running_config_ids"]

        await service.stop_watcher(config_id)


class TestFolderWatcherServiceAutoStart:
    """Tests de auto-start."""

    @pytest.mark.asyncio
    async def test_start_all_autostart(self, service, mock_workflow_engine, tmp_path):
        """Iniciar todos los watchers con auto_start=True."""
        # Crear 2 configs, 1 con auto_start
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        dir2 = tmp_path / "dir2"
        dir2.mkdir()

        id1 = await service.create_config({
            "name": "Auto",
            "watch_path": str(dir1),
            "flow_id": 1,
            "auto_start": True
        })
        print(f"Created config ID: {id1}")

        await service.create_config({
            "name": "Manual",
            "watch_path": str(dir2),
            "flow_id": 2,
            "auto_start": False
        })
        
        # Verify DB content
        conf = await service.get_config(id1)
        print(f"Config from DB: {conf}")

        service.set_workflow_engine(mock_workflow_engine)
        started_count = await service.start_all_autostart()
        print(f"Started count: {started_count}")

        assert started_count == 1

        # Limpiar
        await service.stop_all()

    @pytest.mark.asyncio
    async def test_stop_all(self, service, mock_workflow_engine, tmp_path):
        """Detener todos los watchers."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        dir2 = tmp_path / "dir2"
        dir2.mkdir()

        id1 = await service.create_config({
            "name": "One", "watch_path": str(dir1), "flow_id": 1
        })
        id2 = await service.create_config({
            "name": "Two", "watch_path": str(dir2), "flow_id": 2
        })

        service.set_workflow_engine(mock_workflow_engine)
        await service.start_watcher(id1)
        await service.start_watcher(id2)

        stopped_count = await service.stop_all()

        assert stopped_count == 2
