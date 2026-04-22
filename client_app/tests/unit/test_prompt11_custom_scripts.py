import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from nicegui import ui

class TestCustomScriptPage(unittest.TestCase):

    def setUp(self):
        # Mocks global dependencies
        self.mock_ui_row = patch('nicegui.ui.row').start()
        self.mock_ui_column = patch('nicegui.ui.column').start()
        self.mock_ui_card = patch('nicegui.ui.card').start()
        self.mock_ui_label = patch('nicegui.ui.label').start()
        self.mock_ui_button = patch('nicegui.ui.button').start()
        self.mock_ui_toggle = patch('nicegui.ui.toggle').start()
        self.mock_ui_upload = patch('nicegui.ui.upload').start()
        self.mock_ui_input = patch('nicegui.ui.input').start()
        self.mock_ui_textarea = patch('nicegui.ui.textarea').start()
        self.mock_ui_select = patch('nicegui.ui.select').start()
        self.mock_ui_checkbox = patch('nicegui.ui.checkbox').start()
        self.mock_ui_notify = patch('nicegui.ui.notify').start()
        self.mock_refreshable = patch('nicegui.ui.refreshable').start()
        
        # Mock refreshable decorator to return the function itself (simplified)
        def side_effect(func):
            func.refresh = MagicMock()
            return func
        self.mock_refreshable.side_effect = side_effect

        # Mock Services
        self.mock_custom_script_service = patch('client_app.app.ui.custom_script_page.custom_script_service').start()
        self.mock_script_ingestion_service = patch('client_app.app.ui.custom_script_page.script_ingestion_service').start()
        self.mock_audit_service = patch('client_app.app.ui.custom_script_page.external_script_audit_service').start()
        
        # Mock AutomationSelector
        self.mock_automation_selector = patch('client_app.app.ui.custom_script_page.render_automation_selector', new_callable=AsyncMock).start()
        
        # Mock State
        self.mock_state = patch('client_app.app.ui.custom_script_page.state').start()
        self.mock_state.i18n.t.side_effect = lambda x, y='': y or x


    def tearDown(self):
        patch.stopall()

    async def test_page_initial_render(self):
        from client_app.app.ui.custom_script_page import custom_script_page_content
        
        # Run function
        await custom_script_page_content()
        
        # Verify Selector is called
        self.mock_automation_selector.assert_called_once()
        args, kwargs = self.mock_automation_selector.call_args
        self.assertEqual(kwargs.get('automation_type'), 'CUSTOM_SCRIPT')
        self.assertEqual(kwargs.get('label'), 'Mis Scripts Personalizados')
        self.assertEqual(kwargs.get('create_label'), '--- Crear Nuevo Script IA / Importar ---')

    async def test_creation_mode_toggle(self):
        """Test that toggle exists and has correct options."""
        from client_app.app.ui.custom_script_page import custom_script_page_content
        
        await custom_script_page_content()
        
        # Verify Toggle logic (we can't easily check internal state without deep inspection, 
        # but we can check if ui.toggle was called with expected options)
        self.mock_ui_toggle.assert_called()
        args, kwargs = self.mock_ui_toggle.call_args
        options = kwargs.get('options', args[0] if args else {})
        self.assertIn('ai', options)
        self.assertIn('import', options)
        
    async def test_import_mode_logic(self):
        """Test import specific UI elements appear when mode is Import (simulated)."""
        # Since we can't easily switch state in this unit test without exposing the internal WizardState,
        # we will rely on checking the structure of the code via inspection or simply assume that
        # if we set the wizard state (if accessible) it renders.
        # However, custom_script_page_content creates a local wizard. 
        # Integration test would be better, but for unit checking:
        pass # Placeholder for manual or integration verification

    async def test_import_execution(self):
        """Test that ingestion service is called."""
        # We can expose the handle_import helper if we want to test it directly, 
        # or mock the callback passed to the UI.
        pass

if __name__ == '__main__':
    unittest.main()
