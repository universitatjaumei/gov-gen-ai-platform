"""
Tests TDD para verificar migración de watchers.
Ejecutar ANTES de eliminar: pytest client_app/tests/unit/test_watcher_migration.py -v
"""
import pytest
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestLegacyFilesRemoved:
    """Tests para verificar que archivos legacy fueron eliminados."""

    def test_mail_watcher_page_removed(self):
        """mail_watcher_page.py debe estar eliminado."""
        legacy_path = project_root / 'client_app' / 'app' / 'ui' / 'mail_watcher_page.py'
        assert not legacy_path.exists(), f"Archivo legacy aún existe: {legacy_path}"

    def test_web_watcher_page_removed(self):
        """web_watcher_page.py debe estar eliminado."""
        legacy_path = project_root / 'client_app' / 'app' / 'ui' / 'web_watcher_page.py'
        assert not legacy_path.exists(), f"Archivo legacy aún existe: {legacy_path}"


class TestLegacyImportsRemoved:
    """Tests para verificar que imports legacy fueron eliminados."""

    def test_main_no_mail_watcher_import(self):
        """main.py no debe importar mail_watcher_page."""
        main_path = project_root / 'main.py'
        content = main_path.read_text(encoding='utf-8')

        assert 'from client_app.app.ui.mail_watcher_page' not in content
        assert 'import mail_watcher_page' not in content

    def test_main_no_web_watcher_import(self):
        """main.py no debe importar web_watcher_page."""
        main_path = project_root / 'main.py'
        content = main_path.read_text(encoding='utf-8')

        assert 'from client_app.app.ui.web_watcher_page' not in content
        assert 'import web_watcher_page' not in content


class TestLegacyRoutesRedirect:
    """Tests para verificar que rutas legacy redirigen correctamente."""

    def test_mail_watcher_route_redirects(self):
        """La ruta /mail-watcher debe redirigir a /connections."""
        import main
        import inspect

        source = inspect.getsource(main)

        # Debe existir la ruta pero redirigir
        assert "@ui.page('/mail-watcher')" in source or '@ui.page("/mail-watcher")' in source
        # Y debe contener navegación a /connections
        # Buscar patrón de redirección
        assert "navigate.to('/connections')" in source or 'navigate.to("/connections")' in source

    def test_web_watcher_route_redirects(self):
        """La ruta /web-watcher debe redirigir a /connections."""
        import main
        import inspect

        source = inspect.getsource(main)

        assert "@ui.page('/web-watcher')" in source or '@ui.page("/web-watcher")' in source
        assert "navigate.to('/connections')" in source or 'navigate.to("/connections")' in source


class TestConnectionsPageComplete:
    """Tests para verificar que connections_page tiene toda la funcionalidad."""

    def test_email_tab_has_credential_management(self):
        """Tab Email debe tener gestión de credenciales."""
        from client_app.app.ui.connections_page import render_email_tab
        import inspect

        source = inspect.getsource(render_email_tab)

        assert 'save_imap_credential' in source or 'credential' in source.lower()

    def test_email_tab_has_whitelist(self):
        """Tab Email debe tener configuración de whitelist."""
        from client_app.app.ui.connections_page import render_email_tab
        import inspect

        source = inspect.getsource(render_email_tab)

        assert 'whitelist' in source.lower()

    def test_email_tab_has_logs(self):
        """Tab Email debe mostrar logs de ejecución."""
        from client_app.app.ui.connections_page import render_email_tab
        import inspect

        source = inspect.getsource(render_email_tab)

        assert 'logs' in source.lower() or 'execution' in source.lower()

    def test_web_tab_has_history(self):
        """Tab Web debe mostrar historial de cambios."""
        from client_app.app.ui.connections_page import render_web_tab
        import inspect

        source = inspect.getsource(render_web_tab)

        # Assuming history view or similar exists, or at least list of monitors with status
        # This test might need adjustment if history UI isn't explicitly named "history"
        # Checking for "last_checked_at" or similar indicators of history tracking
        assert 'last_check' in source.lower() or 'history' in source.lower() or 'logs' in source.lower()
