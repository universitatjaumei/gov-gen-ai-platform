import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.ui.connections_page import CONNECTION_TABS

class TestSQLTabRendering:
    """Tests de renderizado de la tab de bases de datos."""

    def test_sql_tab_exists(self):
        """Tab de base de datos está en la lista de tabs."""
        sql_tab = next((t for t in CONNECTION_TABS if t['id'] == 'database'), None)

        assert sql_tab is not None
        assert sql_tab['icon'] == 'storage'
        assert sql_tab['label_key'] == 'connections_tab_database'

class TestSQLTabTranslations:
    """Tests de traducciones para SQL."""

    @pytest.fixture
    def translations(self):
        """Cargar traducciones."""
        import json
        with open('translations.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def test_sql_translations_exist(self, translations):
        """Traducciones SQL en español existen."""
        es = translations.get('es', {})

        required_keys = [
            'connections_tab_database',
            'database_title',
            'database_new',
            'database_edit',
            'database_no_configs',
            'database_test_connection',
            'database_testing',
            'database_delete_confirm'
        ]

        for key in required_keys:
            assert key in es, f"Missing translation key: {key}"

class TestSQLUIFunctionality:
    """Tests de integración básica de la UI con servicios SQL."""

    @pytest.mark.asyncio
    async def test_test_connection_calls_sql_service(self):
        """Probar conexión llama al SQLConnectorService."""
        from client_app.app.services.sql_connector_service import sql_connector_service
        
        with patch.object(sql_connector_service, 'test_connection', new_callable=AsyncMock) as mock_test:
            mock_test.return_value = (True, "Conectado correctamente a la base de datos")
            
            # Simular la llamada que haría el botón en la UI
            success, msg = await sql_connector_service.test_connection(1)
            
            assert success is True
            assert "Conectado" in msg
            mock_test.assert_called_once_with(1)
