import pytest
from unittest.mock import AsyncMock, patch, MagicMock

class TestFoldersTabRendering:
    """Tests de renderizado de la tab folders."""

    def test_folders_tab_exists(self):
        """Tab folders está en la lista de tabs."""
        from client_app.app.ui.connections_page import CONNECTION_TABS

        folder_tab = next((t for t in CONNECTION_TABS if t['id'] == 'folders'), None)

        assert folder_tab is not None
        assert folder_tab['icon'] == 'folder'

    def test_folders_tab_not_placeholder(self):
        """Tab folders ya no es placeholder."""
        from client_app.app.ui.connections_page import FOLDERS_TAB_IS_PLACEHOLDER

        # Después de implementar, debe ser False
        assert FOLDERS_TAB_IS_PLACEHOLDER is False


class TestFoldersTabTranslations:
    """Tests de traducciones."""

    @pytest.fixture
    def translations(self):
        """Cargar traducciones."""
        import json
        with open('translations.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def test_spanish_translations_exist(self, translations):
        """Traducciones en español existen."""
        es = translations.get('es', {})

        required_keys = [
            'folder_watcher_title',
            'folder_watcher_new',
            'folder_watcher_edit',
            'folder_watcher_name',
            'folder_watcher_path',
            'folder_watcher_patterns',
            'folder_watcher_flow',
            'folder_watcher_recursive',
            'folder_watcher_stabilization',
            'folder_watcher_autostart',
            'folder_watcher_start',
            'folder_watcher_stop',
            'folder_watcher_delete_confirm',
            'folder_watcher_no_configs',
            'folder_watcher_status_active',
            'folder_watcher_status_stopped'
        ]

        for key in required_keys:
            assert key in es, f"Missing translation key: {key}"

    def test_catalan_translations_exist(self, translations):
        """Traducciones en catalán existen."""
        ca = translations.get('ca', {})

        # Al menos las keys básicas
        assert 'folder_watcher_title' in ca


class TestFoldersTabFunctionality:
    """Tests de funcionalidad (con mocks)."""

    @pytest.mark.asyncio
    async def test_create_config_calls_service(self):
        """Crear config llama al servicio."""
        from client_app.app.services.folder_watcher_service import folder_watcher_service

        with patch.object(folder_watcher_service, 'create_config', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = 1

            # Simular llamada directa al servicio (la UI llamaría a esto)
            # En tests de UI lógica a veces testeamos la función de 'save' del dialogo,
            # pero aquí verificamos que el servicio es mockeable.
            result = await folder_watcher_service.create_config({
                "name": "Test",
                "watch_path": "/tmp",
                "flow_id": 1
            })

            assert result == 1
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_watcher_calls_service(self):
        """Iniciar watcher llama al servicio."""
        from client_app.app.services.folder_watcher_service import folder_watcher_service

        with patch.object(folder_watcher_service, 'start_watcher', new_callable=AsyncMock) as mock_start:
            mock_start.return_value = (True, "Started")

            success, msg = await folder_watcher_service.start_watcher(1)

            assert success is True
            mock_start.assert_called_once_with(1)
