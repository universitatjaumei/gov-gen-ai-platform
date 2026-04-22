# client_app/tests/unit/test_privacy_indicator.py
import pytest
from unittest.mock import MagicMock, patch

class TestPrivacyIndicator:
    """Tests para el indicador de privacidad en la UI."""

    def test_privacy_badge_translation_exists(self):
        """Verificar que las traducciones del badge existen."""
        import json
        from pathlib import Path
        
        trans_path = Path("translations.json")
        if not trans_path.exists():
            pytest.skip("Translations file not found in root")
            
        with open(trans_path, encoding='utf-8') as f:
            data = json.load(f)
            
        # Verificar claves en Español
        privacy = data.get('es', {}).get('privacy', {})
        assert 'active_badge' in privacy, "Falta traducción 'active_badge'"
        assert 'sovereign_mode' in privacy, "Falta traducción 'sovereign_mode'"
        assert 'badge_tooltip' in privacy, "Falta traducción 'badge_tooltip'"

    def test_toggle_absence_in_ui(self):
        """
        Verificar (por inspección estática o lógica) que NO hay toggle de desactivación.
        Simulamos buscando en el código fuente de extraction_page.py
        """
        from pathlib import Path
        ui_file = Path("client_app/app/ui/extraction_page.py")
        if not ui_file.exists():
            return # Skip if file not found in test env
            
        content = ui_file.read_text(encoding='utf-8')
        
        # Buscar algo que parezca un switch/checkbox de privacidad con etiqueta 'Desactivar'
        # Esto es heurístico
        terms = ["Desactivar Privacidad", "Disable Privacy", "anonimization = False", "anonymize=False"]
        
        for term in terms:
            assert term not in content, f"Encontrado término sospechoso de desactivación: {term}"

    # NOTA: Testear componentes UI de NiceGUI requiere un entorno completo (Selenium/Playwright).
    # Aquí nos limitamos a verificar la configuración y lógica.

