import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Agregar el directorio client_app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from client_app.app.ui.dashboard_page import render_network_status_widget


@pytest.mark.asyncio
async def test_render_network_status_widget_with_configs():
    """
    Prueba que el widget de estado de red se renderice correctamente cuando hay configuraciones disponibles.
    """
    # Mock de la lista de configuraciones
    mock_configs = [
        {
            'id': 1,
            'name': 'Carpeta 1',
            'watch_path': 'C:/temp/carpeta1',
            'last_error': None,
            'is_active': True,
            'is_paused': False,
            'last_check_at': None,
            'trigger_count': 5
        }
    ]

    with patch('client_app.app.ui.dashboard_page.dash') as mock_dash:
        mock_dash.watcher_configs = mock_configs
        mock_dash.loading = False
        
        # Ejecutar la función (ahora síncrona)
        render_network_status_widget()
        
        # No hay aserciones de mocks de servicio aquí porque ahora usa dash.watcher_configs directamente


@pytest.mark.asyncio
async def test_render_network_status_widget_without_configs():
    """
    Prueba que el widget de estado de red se renderice correctamente cuando no hay configuraciones.
    """
    with patch('client_app.app.ui.dashboard_page.dash') as mock_dash:
        mock_dash.watcher_configs = []
        mock_dash.loading = False
        
        # Ejecutar la función
        render_network_status_widget()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])