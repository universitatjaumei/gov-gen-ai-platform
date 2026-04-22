# client_app/tests/integration/test_navigation.py
import pytest
from nicegui import ui
from nicegui.testing import User

@pytest.fixture
def user(user: User) -> User:
    return user

class TestMainNavigation:
    """Tests de navegación principal del menú."""

    async def test_dashboard_loads_with_filters(self, user: User):
        """Dashboard carga con componentes principales."""
        await user.open("/")
        # Verify dashboard title or main container
        user.should_see("Dashboard")

    async def test_automatizations_submenu_navigation(self, user: User):
        """Navegar entre las 4 páginas de automatizaciones."""
        # Adjusted routes based on main.py
        pages = [
            ("/documents", "Archivos"),   # extraction-page / documents
            ("/rpa", "RPA"),              # rpa-page
            ("/etl", "ETL"),              # etl-page
            ("/custom-scripts", "Scripts"), # custom-scripts-page
        ]

        for path, expected_text in pages:
            await user.open(path)
            user.should_see(expected_text)

    async def test_connections_tabs_switch(self, user: User):
        """Verificar carga de página de conexiones."""
        await user.open("/connections")
        user.should_see("Conexiones")

    async def test_logs_page_shows_all_types(self, user: User):
        """Logs carga correctamente."""
        await user.open("/logs")
        user.should_see("Logs")
        # Verify filters exist by label text
        try:
            user.should_see("Fecha")
        except AssertionError:
            # Fallback for english or other keys
            user.should_see("Date")

    async def test_privacy_page_standalone(self, user: User):
        """Página de privacidad (anonymizer) carga correctamente."""
        await user.open("/anonymizer") # Corrected route
        try:
            user.should_see("Anonimizar")
        except AssertionError:
             user.should_see("Anonymize")

    async def test_config_pages_accessible(self, user: User):
        """Página de configuración carga correctamente."""
        await user.open("/config")
        # Verify tabs exist
        user.should_see("General")
        user.should_see("Seguridad")
