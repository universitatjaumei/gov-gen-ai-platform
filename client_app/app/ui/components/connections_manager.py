from nicegui import ui
from typing import Optional, List, Dict, Any
from datetime import datetime
from client_app.app.core.state import state
from client_app.app.services.mail_watcher_service import mail_watcher_service
from client_app.app.database.models import LocalCredentials
from sqlmodel import select

class ConnectionsManager:
    """
    Componente reutilizable para la gestión de conexiones de correo (IMAP/SMTP).
    Proporciona tablas de gestión, diálogos de creación/edición y pruebas de conexión.
    """
    def __init__(self, service_type: str = "IMAP"):
        self.service_type = service_type # "IMAP" or "SMTP"
        self.credentials: List[Dict[str, Any]] = []
        self.is_loading = False
        self.t = state.i18n.t

    async def load_credentials(self):
        """Carga las credenciales del tipo especificado."""
        self.is_loading = True
        self.credentials = await mail_watcher_service.list_credentials(service_type=self.service_type)
        self.is_loading = False
        self.render_table.refresh()

    def handle_delete(self, cred_id: int):
        """Muestra diálogo de confirmación para eliminar una credencial."""
        async def confirm_delete():
            await mail_watcher_service.delete_credential(cred_id)
            ui.notify("Conexión eliminada", type='positive')
            dialog.close()
            await self.load_credentials()

        with ui.dialog() as dialog, ui.card().classes('p-6'):
            ui.label(f"¿Eliminar esta conexión {self.service_type}?").classes('text-lg font-bold mb-4')
            ui.label("Esta acción no se puede deshacer.").classes('text-slate-500 mb-4')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Eliminar', on_click=confirm_delete).props('color=negative unelevated')
        dialog.open()

    async def handle_test(self, cred_id: int):
        """Prueba una conexión existente."""
        ui.notify(f"Probando conexión {self.service_type}...", type='info')
        success, message = await mail_watcher_service.test_connection(cred_id)
        if success:
            ui.notify(f"Conexión exitosa: {message}", type='positive')
        else:
            ui.notify(f"Error de conexión: {message}", type='negative')

    async def handle_edit(self, cred: Dict):
        """Carga los datos completos de la credencial y abre el diálogo de edición."""
        try:
            full_data = await mail_watcher_service.get_credential(cred['id'])
            if full_data:
                self.open_credential_dialog(cred=cred, full_cred_data=full_data)
            else:
                # No se pudieron descifrar los datos, abrir diálogo vacío para re-configurar
                ui.notify("Los datos guardados no se pudieron descifrar. Deberás re-introducir la configuración.", type='warning')
                self.open_credential_dialog(cred=cred, full_cred_data=None)
        except Exception as e:
            # Error de descifrado (clave cambió), permitir edición con campos vacíos
            ui.notify("Error al descifrar credenciales. Re-introduce los datos.", type='warning')
            self.open_credential_dialog(cred=cred, full_cred_data=None)

    def open_credential_dialog(self, cred: Optional[Dict] = None, full_cred_data: Optional[Dict] = None):
        """
        Abre el diálogo para crear o editar una credencial.
        Utiliza el servicio de mail_watcher para persistir los datos.

        Args:
            cred: Datos básicos de la credencial (de list_credentials)
            full_cred_data: Datos completos descifrados (de get_credential) - solo para edición
        """
        # Valores iniciales - usar full_cred_data si está disponible
        name_val = cred.get('name', '') if cred else ""
        host_val = full_cred_data.get('server', '') if full_cred_data else ""
        port_val = full_cred_data.get('port', 993 if self.service_type == "IMAP" else 587) if full_cred_data else (993 if self.service_type == "IMAP" else 587)
        user_val = full_cred_data.get('user', '') if full_cred_data else ""
        pass_val = "" # Nunca mostramos el password
        ssl_val = full_cred_data.get('use_ssl', True) if full_cred_data else True

        with ui.dialog() as dialog, ui.card().classes('w-[500px] p-6'):
            ui.label(f"{'Editar' if cred else 'Nueva'} Conexión {self.service_type}").classes('text-xl font-bold mb-4')
            
            with ui.column().classes('w-full gap-3'):
                name_input = ui.input('Nombre descriptivo', value=name_val, placeholder='Ej: Gmail Empresa').classes('w-full').props('outlined dense')
                
                with ui.row().classes('w-full gap-2'):
                    host_input = ui.input('Servidor / Host', value=host_val, placeholder='imap.gmail.com').classes('flex-grow').props('outlined dense')
                    port_input = ui.number('Puerto', value=port_val).classes('w-24').props('outlined dense')
                
                user_input = ui.input('Usuario / Email', value=user_val).classes('w-full').props('outlined dense')
                pass_input = ui.input('Contraseña / App Token', password=True, value=pass_val).classes('w-full').props('outlined dense')
                
                with ui.row().classes('w-full items-center justify-between'):
                    ssl_label = 'Usar SSL/TLS' if self.service_type == "IMAP" else 'Usar STARTTLS/SSL'
                    ssl_check = ui.checkbox(ssl_label, value=ssl_val)
                    
                    async def run_test():
                        if not all([host_input.value, user_input.value, pass_input.value]):
                            ui.notify("Completa los datos para probar la conexión", type='warning')
                            return
                        
                        ui.notify("Probando parámetros...", type='info')
                        # Guardamos temporalmente para probar (MailWatcherService.test_connection requiere ID)
                        # Alternativamente, mail_watcher_service podría tener un método que acepte params planos
                        # Pero por ahora usamos el patrón de SMTPPage: guardar temporal -> test -> borrar
                        temp_id = await mail_watcher_service.save_credential(
                            name=f"TEMP_TEST_{datetime.now().timestamp()}",
                            server=host_input.value,
                            port=int(port_input.value),
                            username=user_input.value,
                            password=pass_input.value,
                            use_ssl=ssl_check.value,
                            service_type=self.service_type
                        )
                        success, message = await mail_watcher_service.test_connection(temp_id)
                        await mail_watcher_service.delete_credential(temp_id)
                        
                        if success:
                            ui.notify("Conexión exitosa", type='positive')
                        else:
                            ui.notify(f"Fallo: {message}", type='negative')

                    ui.button('PROBAR', icon='science', on_click=run_test).props('flat color=amber dense')

            async def on_save():
                if not all([name_input.value, host_input.value, user_input.value]):
                    ui.notify("Nombre, servidor y usuario son obligatorios", type='warning')
                    return
                
                if not cred and not pass_input.value:
                    ui.notify("La contraseña es obligatoria para nuevas conexiones", type='warning')
                    return

                try:
                    if cred:
                        # Update
                        await mail_watcher_service.update_credential(
                            credential_id=cred['id'],
                            name=name_input.value,
                            server=host_input.value,
                            port=int(port_input.value),
                            username=user_input.value,
                            password=pass_input.value if pass_input.value else None,
                            use_ssl=ssl_check.value,
                            service_type=self.service_type
                        )
                    else:
                        # Save New
                        await mail_watcher_service.save_credential(
                            name=name_input.value,
                            server=host_input.value,
                            port=int(port_input.value),
                            username=user_input.value,
                            password=pass_input.value,
                            use_ssl=ssl_check.value,
                            service_type=self.service_type
                        )
                    
                    ui.notify("Conexión guardada", type='positive')
                    await self.load_credentials()
                    dialog.close()
                except Exception as e:
                    ui.notify(f"Error al guardar: {e}", type='negative')

            with ui.row().classes('w-full justify-end mt-6 gap-2'):
                ui.button('CANCELAR', on_click=dialog.close).props('flat')
                ui.button('GUARDAR', on_click=on_save).props('color=primary unelevated')
        
        dialog.open()

    @ui.refreshable
    def render_table(self):
        """Renderiza la tabla de credenciales."""
        if not self.credentials:
            with ui.column().classes('w-full items-center py-12 bg-slate-50 rounded-lg border border-dashed border-slate-300 mb-6'):
                ui.icon('mail_lock', size='lg').classes('text-slate-300')
                ui.label(f'No hay conexiones {self.service_type} configuradas').classes('text-slate-400 mt-2')
                ui.button(f'Añadir {self.service_type}', icon='add', on_click=lambda: self.open_credential_dialog()).props('outline color=primary mt-4')
            return

        with ui.column().classes('w-full gap-2 mb-6'):
            with ui.row().classes('w-full justify-between items-center px-2 mb-1'):
                ui.label(f'Conexiones {self.service_type} registradas').classes('font-bold text-slate-700')
                ui.button(icon='add', on_click=lambda: self.open_credential_dialog()).props('flat round color=primary').tooltip(f'Nueva {self.service_type}')

            for c in self.credentials:
                with ui.card().classes('w-full p-0 shadow-none border border-slate-200 hover:border-blue-300 transition-colors overflow-hidden'):
                    with ui.row().classes('w-full items-center p-3 gap-4'):
                        ui.icon('settings_input_composite' if self.service_type == "IMAP" else 'send', size='sm').classes('text-slate-400 ml-2')

                        with ui.column().classes('flex-grow'):
                            ui.label(c['name']).classes('font-bold text-sm')
                            ui.label(f"{self.service_type} • ID: {c['id']}").classes('text-xs text-slate-400')

                        with ui.row().classes('gap-1 pr-2'):
                            ui.button(icon='science', on_click=lambda c_id=c['id']: self.handle_test(c_id)).props('flat round dense color=amber').tooltip('Probar')
                            ui.button(icon='edit', on_click=lambda curr_c=c: self.handle_edit(curr_c)).props('flat round dense color=blue').tooltip('Editar')
                            ui.button(icon='delete', on_click=lambda c_id=c['id']: self.handle_delete(c_id)).props('flat round dense color=red').tooltip('Eliminar')

    def render(self):
        """Renderizado principal del componente."""
        ui.timer(0.1, self.load_credentials, once=True)
        self.render_table()
