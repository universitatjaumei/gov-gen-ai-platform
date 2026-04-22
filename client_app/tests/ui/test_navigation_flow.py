
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nicegui import ui
import asyncio

# Import the component to test
from client_app.app.ui.components.wizards.script_wizard import render_script_wizard

@pytest.mark.asyncio
class TestNavigationFlowLogic:
    """Tests for smart redirection logic using mocks."""

    async def test_save_script_logic_isolated_mode(self):
        """
        Verify that in isolated mode, it navigates to the execution page.
        """
        with patch('nicegui.ui.navigate.to') as mock_navigate, \
             patch('nicegui.ui.dialog') as mock_dialog, \
             patch('nicegui.ui.notify') as mock_notify, \
             patch('nicegui.ui.run_javascript', new_callable=AsyncMock):
            
            # Setup mock dialog
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value.__enter__.return_value = mock_dialog_instance
            
            # Call the wizard renderer (isolated mode)
            # We don't actually render in a real UI, we just want to trigger the save logic
            # To do that, we need to access the inner function
            
            # Since render_script_wizard is a component function, we'll mock the UI elements it creates
            with patch('nicegui.ui.input', return_value=MagicMock(value='Test Script')), \
                 patch('nicegui.ui.textarea'), \
                 patch('nicegui.ui.codemirror'), \
                 patch('nicegui.ui.button') as mock_button:
                
                # Capture the save callback
                await render_script_wizard(on_save=MagicMock(), is_flow_context=False)
                
                # Find the 'Guardar y Vincular' button and its callback
                save_callback = None
                for call in mock_button.call_args_list:
                    if call.args and call.args[0] == 'Guardar y Vincular':
                        save_callback = call.kwargs.get('on_click')
                
                if not save_callback:
                    # Alternative search in kwargs if args[0] is not there
                    for call in mock_button.call_args_list:
                        if call.kwargs.get('text') == 'Guardar y Vincular':
                            save_callback = call.kwargs.get('on_click')
                
                assert save_callback is not None
                
                # Execute the save callback
                await save_callback()
                
                # Verify navigation was called (after the success dialog interaction)
                # In our implementation, navigation happens when user clicks "Probar Ahora" in the success dialog
                # We need to find THAT callback
                
                probar_callback = None
                for call in mock_button.call_args_list:
                    if call.args and call.args[0] == 'Probar Ahora':
                        probar_callback = call.kwargs.get('on_click')
                
                assert probar_callback is not None
                probar_callback()
                
                # Check if it tried to navigate to an execution page
                mock_navigate.assert_called()
                args, _ = mock_navigate.call_args
                assert '/execution/' in args[0]

    async def test_save_script_logic_flow_mode(self):
        """
        Verify that in flow mode, it emits an event.
        """
        # Patch ui_emit in the module where it's used
        with patch('client_app.app.ui.components.wizards.script_wizard.ui_emit') as mock_emit, \
             patch('nicegui.ui.dialog') as mock_dialog, \
             patch('nicegui.ui.button') as mock_button, \
             patch('nicegui.ui.run_javascript', new_callable=AsyncMock):
            
            # Setup mock dialog
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value.__enter__.return_value = mock_dialog_instance
            
            with patch('nicegui.ui.input', return_value=MagicMock(value='Flow Script')), \
                 patch('nicegui.ui.textarea'), \
                 patch('nicegui.ui.codemirror'):
                
                # Call wizard in flow context
                on_save_mock = MagicMock()
                await render_script_wizard(on_save=on_save_mock, is_flow_context=True)
                
                # Find and trigger save
                save_callback = None
                for call in mock_button.call_args_list:
                    if call.args and call.args[0] == 'Guardar y Vincular':
                        save_callback = call.kwargs.get('on_click')
                
                await save_callback()
                
                # Capture the 'Continuar' button callback (which calls ui_emit)
                continuar_callback = None
                for call in mock_button.call_args_list:
                    if call.args and call.args[0] == 'Continuar':
                        continuar_callback = call.kwargs.get('on_click')
                
                assert continuar_callback is not None
                continuar_callback()
                
                # In flow mode, on_save should be called
                on_save_mock.assert_called_once()
                
                # Verify event emission
                from unittest.mock import ANY
                assert mock_emit.call_count >= 2
                mock_emit.assert_any_call('atom_created', ANY)
                mock_emit.assert_any_call('refresh_flow_step', ANY)
