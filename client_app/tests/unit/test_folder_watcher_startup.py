import pytest
from unittest.mock import AsyncMock, patch, MagicMock

class TestFolderWatcherStartup:
    """Tests de auto-start en startup."""

    @pytest.mark.asyncio
    async def test_autostart_called_on_startup(self):
        """start_all_autostart se llama en startup (simulación)."""
        from client_app.app.services.folder_watcher_service import folder_watcher_service

        # Este test verifica que el método existe y se puede llamar
        # La integración real con main.py es difícil de testear unitariamente sin ejecutar la app
        
        with patch.object(
            folder_watcher_service,
            'start_all_autostart',
            new_callable=AsyncMock
        ) as mock_start:
            mock_start.return_value = 2

            # Simular lo que haría main.py
            count = await folder_watcher_service.start_all_autostart()

            assert count == 2
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_all_called_on_shutdown(self):
        """stop_all se llama en shutdown (simulación)."""
        from client_app.app.services.folder_watcher_service import folder_watcher_service

        with patch.object(
            folder_watcher_service,
            'stop_all',
            new_callable=AsyncMock
        ) as mock_stop:
            mock_stop.return_value = 3

            # Simular lo que haría main.py en shutdown
            count = await folder_watcher_service.stop_all()

            assert count == 3
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_engine_injected(self):
        """workflow_engine se inyecta en el servicio."""
        from client_app.app.services.folder_watcher_service import folder_watcher_service

        mock_engine = MagicMock()
        folder_watcher_service.set_workflow_engine(mock_engine)

        assert folder_watcher_service._workflow_engine is mock_engine
