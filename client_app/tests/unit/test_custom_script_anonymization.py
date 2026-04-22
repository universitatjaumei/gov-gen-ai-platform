# client_app/tests/unit/test_custom_script_anonymization.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

class TestCustomScriptAnonymization:
    """Tests de anonimización en Custom Scripts."""

    def test_custom_script_page_shows_privacy_indicator(self):
        """La página Custom Script muestra indicador de privacidad."""
        with open('client_app/app/ui/custom_script_page.py', 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'render_privacy_indicator' in content or 'privacy_indicator' in content

    def test_logic_uses_anonymizer(self):
        """Verifica que la lógica usa el anonimizador."""
        with open('client_app/app/ui/custom_script_page.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify AnonymizationContext import
        assert 'from client_app.app.modules.privacy.anonymizer import AnonymizationContext' in content
        
        # Verify usage in generate_logic
        assert 'anonymizer = AnonymizationContext' in content
        assert 'user_prompt_anon = anonymizer.anonymize(wizard.user_prompt)' in content
        assert 'script_generator_service.generate_script(user_prompt_anon' in content

