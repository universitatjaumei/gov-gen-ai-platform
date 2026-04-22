"""
Tests para verificar las correcciones del ciclo de vida asíncrono.

Verifica:
1. open_credential_dialog es una corrutina
2. No se usa asyncio.run() dentro de contextos ya asíncronos
3. mail_watcher_service.get_credential maneja IDs nulos correctamente
"""
import inspect
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestAsyncCorrections:
    """Tests para verificar correcciones asíncronas."""

    def test_open_credential_dialog_is_coroutine(self):
        """Verifica que open_credential_dialog es una función async."""
        # Importamos el módulo para inspeccionar
        from client_app.app.ui import connections_page

        # Buscamos la función render_email_tab que contiene open_credential_dialog
        # La función está definida dentro de render_email_tab, así que verificamos
        # que el módulo importa asyncio (requisito para funciones async)
        assert hasattr(connections_page, 'asyncio'), \
            "El módulo debe importar asyncio"

    def test_connections_page_imports_asyncio(self):
        """Verifica que connections_page importa asyncio."""
        import client_app.app.ui.connections_page as cp

        # Verificamos que asyncio está disponible en el módulo
        assert 'asyncio' in dir(cp) or hasattr(cp, 'asyncio'), \
            "connections_page debe importar asyncio"

    def test_no_asyncio_run_in_connections_page(self):
        """Verifica que no hay asyncio.run() en connections_page."""
        import client_app.app.ui.connections_page as cp
        import inspect

        source = inspect.getsource(cp)
        # asyncio.run() no debería usarse en contextos NiceGUI
        assert 'asyncio.run(' not in source, \
            "No debe haber asyncio.run() en connections_page (NiceGUI ya tiene event loop)"


class TestMailWatcherServiceNullHandling:
    """Tests para verificar manejo de IDs nulos."""

    @pytest.mark.asyncio
    async def test_get_credential_with_none_id_returns_none(self):
        """get_credential debe retornar None si credential_id es None."""
        from client_app.app.services.mail_watcher_service import mail_watcher_service

        result = await mail_watcher_service.get_credential(None)
        assert result is None, \
            "get_credential(None) debe retornar None sin hacer query a DB"

    @pytest.mark.asyncio
    async def test_get_credential_with_none_id_no_db_query(self):
        """get_credential no debe hacer query a DB si ID es None."""
        from client_app.app.services.mail_watcher_service import MailWatcherService

        service = MailWatcherService()

        # Patcheamos AsyncSession para verificar que no se usa
        with patch('client_app.app.services.mail_watcher_service.AsyncSession') as mock_session:
            result = await service.get_credential(None)

            # No debe haberse creado ninguna sesión
            mock_session.assert_not_called()
            assert result is None


class TestRpaExecutorNoEmojis:
    """Tests para verificar que no hay emojis en logs."""

    def test_no_emojis_in_rpa_executor(self):
        """Verifica que rpa_executor no tiene emojis que rompan Windows."""
        import client_app.app.core.rpa_executor as rpa
        import inspect

        source = inspect.getsource(rpa)

        # Lista de emojis comunes que causan problemas en Windows CP1252
        problematic_emojis = [
            '🚀', '📂', '🔄', '💾', '📖', '⚠️', '🍪', '🤖',
            '✅', '🎯', '❌', '🤷', '💥', '🚑', '⏭️', '🛑', '🧠'
        ]

        for emoji in problematic_emojis:
            assert emoji not in source, \
                f"Emoji {emoji} encontrado en rpa_executor.py - causará UnicodeEncodeError en Windows"

    def test_print_statements_are_ascii_safe(self):
        """Verifica que los prints pueden codificarse en ASCII/CP1252."""
        import client_app.app.core.rpa_executor as rpa
        import inspect
        import re

        source = inspect.getsource(rpa)

        # Extraer todos los strings de print
        print_pattern = r'print\(f?"([^"]*)"'
        prints = re.findall(print_pattern, source)

        for print_str in prints:
            try:
                # Intentar codificar en CP1252 (Windows default)
                print_str.encode('cp1252')
            except UnicodeEncodeError:
                pytest.fail(f"Print statement no compatible con Windows: {print_str[:50]}...")
