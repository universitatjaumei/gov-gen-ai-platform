"""
Tests TDD para connections_page consolidada.
Ejecutar ANTES de implementar: pytest client_app/tests/unit/test_connections_page.py -v
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestConnectionsPageStructure:
    """Tests de estructura de la página."""

    def test_connections_page_module_exists(self):
        """El módulo connections_page debe existir."""
        try:
            from client_app.app.ui import connections_page
            assert connections_page is not None
        except ImportError:
            pytest.fail("client_app.app.ui.connections_page not found")

    def test_connections_page_content_function_exists(self):
        """Debe exportar connections_page_content()."""
        try:
            from client_app.app.ui.connections_page import connections_page_content
            assert callable(connections_page_content)
        except ImportError:
             pytest.fail("connections_page_content not found")

    def test_tab_render_functions_exist(self):
        """Deben existir funciones para renderizar cada tab."""
        try:
            from client_app.app.ui.connections_page import (
                render_folders_tab,
                render_email_tab,
                render_web_tab
            )
            assert callable(render_folders_tab)
            assert callable(render_email_tab)
            assert callable(render_web_tab)
        except ImportError:
            pytest.fail("tab render functions not found")

    def test_tab_configuration_exists(self):
        """Debe existir configuración de tabs exportable."""
        try:
            from client_app.app.ui.connections_page import CONNECTION_TABS

            assert len(CONNECTION_TABS) == 3
            assert 'folders' in [t['id'] for t in CONNECTION_TABS]
            assert 'email' in [t['id'] for t in CONNECTION_TABS]
            assert 'web' in [t['id'] for t in CONNECTION_TABS]
        except ImportError:
             pytest.fail("CONNECTION_TABS not found")

    def test_tab_configuration_has_required_fields(self):
        """Cada tab debe tener id, label_key, icon."""
        try:
            from client_app.app.ui.connections_page import CONNECTION_TABS
            for tab in CONNECTION_TABS:
                assert 'id' in tab
                assert 'label_key' in tab
                assert 'icon' in tab
        except ImportError:
            pass # Already covered


class TestFoldersTab:
    """Tests para el tab de Carpetas (placeholder)."""

    def test_folders_tab_is_placeholder(self):
        """El tab de carpetas debe ser un placeholder."""
        try:
            from client_app.app.ui.connections_page import FOLDERS_TAB_IS_PLACEHOLDER
            assert FOLDERS_TAB_IS_PLACEHOLDER is True
        except ImportError:
             pytest.fail("FOLDERS_TAB_IS_PLACEHOLDER not found")

    def test_folders_placeholder_message_exists(self):
        """Debe existir mensaje de placeholder."""
        try:
            from client_app.app.ui.connections_page import FOLDERS_PLACEHOLDER_MESSAGE
            assert 'próximamente' in FOLDERS_PLACEHOLDER_MESSAGE.lower() or 'coming' in FOLDERS_PLACEHOLDER_MESSAGE.lower()
        except ImportError:
             pytest.fail("FOLDERS_PLACEHOLDER_MESSAGE not found")


class TestEmailTab:
    """Tests para el tab de Email."""

    def test_email_tab_uses_mail_watcher_service(self):
        """El tab de email debe usar mail_watcher_service."""
        try:
            from client_app.app.ui.connections_page import render_email_tab
            import inspect

            source = inspect.getsource(render_email_tab)
            assert 'mail_watcher_service' in source
        except ImportError:
             pytest.fail("render_email_tab not found")

    def test_email_tab_has_crud_operations(self):
        """El tab de email debe tener operaciones CRUD."""
        try:
            from client_app.app.ui.connections_page import (
                email_load_config,
                email_save_config,
                email_test_connection,
                email_toggle_watcher
            )
            assert callable(email_load_config)
            assert callable(email_save_config)
            assert callable(email_test_connection)
            assert callable(email_toggle_watcher)
        except ImportError:
             pytest.fail("Email CRUD functions not found")


class TestWebTab:
    """Tests para el tab de Web."""

    def test_web_tab_uses_web_watcher_service(self):
        """El tab de web debe usar web_watcher_service."""
        try:
            from client_app.app.ui.connections_page import render_web_tab
            import inspect

            source = inspect.getsource(render_web_tab)
            # Check for service usage OR helper usage
            assert 'web_watcher_service' in source or 'web_load_watchers' in source
        except ImportError:
            pytest.fail("render_web_tab not found")

    def test_web_tab_has_crud_operations(self):
        """El tab de web debe tener operaciones CRUD."""
        try:
            from client_app.app.ui.connections_page import (
                web_load_watchers,
                web_create_watcher,
                web_delete_watcher,
                web_toggle_watcher
            )
            assert callable(web_load_watchers)
            assert callable(web_create_watcher)
            assert callable(web_delete_watcher)
            assert callable(web_toggle_watcher)
        except ImportError:
             pytest.fail("Web CRUD functions not found")


class TestConnectionsPageI18n:
    """Tests de internacionalización."""

    def test_connections_i18n_keys_exist(self):
        """Las claves i18n para connections deben existir."""
        import json

        translations_path = project_root / 'translations.json'
        with open(translations_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)

        required_keys = [
            'connections_title',
            'connections_tab_folders',
            'connections_tab_email',
            'connections_tab_web',
            'connections_folders_coming_soon',
            'connections_new_email_monitor',
            'connections_new_web_monitor',
            'connections_test_connection',
            'connections_start_monitor',
            'connections_stop_monitor',
        ]

        es_keys = translations.get('es', {})
        for key in required_keys:
            assert key in es_keys, f"Falta clave i18n: {key}"
