from typing import Optional, Dict, Any, Callable
from nicegui import ui
from client_app.app.core.state import state

async def show_escalation_dialog(
    asset_id: Optional[int],
    asset_type: str,
    details: Dict[str, Any],
    on_success: Optional[Callable] = None
):
    """
    Muestra un diálogo para escalar una solicitud de soporte al Partner.
    
    Args:
        asset_id: ID del activo (script, playbook, etc.) o None si es nuevo.
        asset_type: Tipo de activo ('custom_script', 'flow', etc.)
        details: Diccionario con contexto (prompt, código, errores).
        on_success: Callback opcional tras envío exitoso.
    """
    
    with ui.dialog() as dialog, ui.card().classes('w-[500px] p-6'):
        ui.label('🆘 Solicitar Ayuda al Partner').classes('text-xl font-bold mb-4')
        ui.label('Describe el problema para que el Partner pueda ayudarte a resolverlo. Enviaremos automáticamente el contexto técnico (prompt y código).').classes('text-sm text-slate-500 mb-4')
        
        comment_area = ui.textarea(
            label='Tu mensaje al Partner',
            placeholder='Ej: "La IA no consigue extraer correctamente el campo Fecha Vencimiento..."'
        ).classes('w-full mb-6').props('outlined autogrow')
        
        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            
            async def send_request():
                if not comment_area.value.strip():
                    ui.notify('Por favor, escribe un comentario descriptivo', type='warning')
                    return
                
                try:
                    # Show loading
                    ui.notify('Enviando solicitud...', icon='send', type='info')
                    
                    # Call API
                    # Note: license_key is usually in app_state or we can get it from first ServerConnection
                    # For now assume trials or a valid connection exists.
                    license_key = "DEV_LICENSE_KEY_12345" # Fallback or get from DB
                    
                    await state.brain.escalate_support_request(
                        asset_id=asset_id,
                        asset_type=asset_type,
                        details=details,
                        user_comment=comment_area.value,
                        license_key=license_key
                    )
                    
                    ui.notify('Solicitud enviada correctamente', type='positive')
                    dialog.close()
                    if on_success:
                        await on_success()
                except Exception as e:
                    ui.notify(f'Error al enviar solicitud: {e}', type='negative')
            
            ui.button('Enviar a Partner', on_click=send_request).props('color=primary')
            
        dialog.open()
