from typing import Optional, List, Dict, Any
from datetime import datetime
from nicegui import ui
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.core.state import state
from client_app.app.database.db import client_engine
from client_app.app.database.models import DatabaseCredentialConfig
from client_app.app.services.sql_connector_service import sql_connector_service
from client_app.app.modules.security.encryption_service import EncryptionService

class DatabaseConnectionManager:
    """
    Componente para la gestión de conexiones a bases de datos SQL (MySQL, Postgres, SQL Server, SQLite).
    Permite crear, editar, eliminar y probar conexiones.
    """
    def __init__(self):
        self.connections: List[DatabaseCredentialConfig] = []
        self.encryption = EncryptionService()
        self.t = state.i18n.t

    async def load_connections(self):
        """Carga las conexiones configuradas desde la base de datos."""
        async with AsyncSession(client_engine) as session:
            result = await session.exec(select(DatabaseCredentialConfig))
            self.connections = result.all()
        self.render_table.refresh()

    def handle_delete(self, conn_id: int):
        """Muestra diálogo de confirmación para eliminar una conexión."""
        async def confirm_delete():
            try:
                async with AsyncSession(client_engine) as session:
                    conn = await session.get(DatabaseCredentialConfig, conn_id)
                    if conn:
                        await session.delete(conn)
                        await session.commit()
                ui.notify("Conexión eliminada", type='positive')
                dialog.close()
                await self.load_connections()
            except Exception as e:
                ui.notify(f"Error al eliminar: {e}", type='negative')

        with ui.dialog() as dialog, ui.card().classes('p-6'):
            ui.label("¿Eliminar esta conexión de base de datos?").classes('text-lg font-bold mb-4')
            ui.label("Esta acción no se puede deshacer.").classes('text-slate-500 mb-4')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Eliminar', on_click=confirm_delete).props('color=negative unelevated')
        dialog.open()

    async def handle_test(self, conn_id: int):
        """Prueba una conexión existente por ID."""
        ui.notify("Probando conexión...", type='info')
        success, message = await sql_connector_service.test_connection(conn_id)
        if success:
            ui.notify(f"Conexión exitosa: {message}", type='positive')
        else:
            ui.notify(f"Error: {message}", type='negative')

    def open_connection_dialog(self, conn: Optional[DatabaseCredentialConfig] = None):
        """Abre el diálogo de edición/creación."""
        
        # Valores iniciales
        name_val = conn.name if conn else ""
        type_val = conn.db_type if conn else "mysql"
        host_val = conn.host if conn else ("localhost" if type_val != 'sqlite' else "")
        port_val = conn.port if conn else 3306
        db_val = conn.database if conn else ""
        user_val = conn.username if conn else ""
        pass_val = "" # No mostramos password
        ssl_val = conn.ssl_enabled if conn else False

        db_types = {
            'mysql': 'MySQL / MariaDB',
            'postgresql': 'PostgreSQL',
            'sqlserver': 'SQL Server',
            'sqlite': 'SQLite (Archivo Local)'
        }

        with ui.dialog() as dialog, ui.card().classes('w-[600px] p-6'):
            ui.label('Editar Conexión' if conn else 'Nueva Conexión de Base de Datos').classes('text-xl font-bold mb-4')
            
            with ui.column().classes('w-full gap-3'):
                name_input = ui.input('Nombre descriptivo', value=name_val, placeholder='Ej: ERP Producción').classes('w-full').props('outlined dense')
                
                type_select = ui.select(db_types, value=type_val, label='Tipo de Base de Datos').classes('w-full').props('outlined dense')
                
                # Campos dinámicos según tipo
                # SQLite solo necesita Database (path)
                # Otros necesitan Host, Port, User, Pass
                
                # Contenedor para campos (host/port/user/pass)
                fields_container = ui.column().classes('w-full gap-3')

                def update_fields_visibility():
                    fields_container.clear()
                    is_sqlite = type_select.value == 'sqlite'
                    
                    with fields_container:
                        if is_sqlite:
                            ui.input('Ruta del archivo (Database)', value=db_val, placeholder='/ruta/a/mi_base.db').bind_value_to(db_input).classes('w-full').props('outlined dense')
                            ui.label('Nota: Para rutas relativas, usa "./data/..."').classes('text-xs text-gray-500')
                        else:
                            with ui.row().classes('w-full gap-2'):
                                ui.input('Host / IP', value=host_val).bind_value_to(host_input).classes('flex-grow').props('outlined dense')
                                ui.number('Puerto', value=port_val).bind_value_to(port_input).classes('w-24').props('outlined dense')
                            
                            ui.input('Base de Datos', value=db_val).bind_value_to(db_input).classes('w-full').props('outlined dense')
                            
                            with ui.row().classes('w-full gap-2'):
                                ui.input('Usuario', value=user_val).bind_value_to(user_input).classes('flex-grow').props('outlined dense')
                                ui.input('Contraseña', password=True, value=pass_val).bind_value_to(pass_input).classes('flex-grow').props('outlined dense')
                            
                            ui.checkbox('Habilitar SSL', value=ssl_val).bind_value_to(ssl_check)

                # Variables para bindings (necesarios porque los inputs se recrean)
                # Usamos objetos mutables o bindings directos si es posible, pero con recreación es tricky.
                # Mejor estructura: inputs siempre existen, solo visibility cambia.
                
                # Re-approach: Create all inputs, toggle visibility.
                def update_visibility(_=None):
                    is_sqlite = type_select.value == 'sqlite'
                    host_row.visible = not is_sqlite
                    user_row.visible = not is_sqlite
                    ssl_check.visible = not is_sqlite
                    
                    if is_sqlite:
                        db_input.label = 'Ruta del archivo SQLite'
                        db_input.placeholder = 'C:/datos/base.db'
                    else:
                        db_input.label = 'Base de Datos'
                        db_input.placeholder = 'nombre_db'

                type_select.on_value_change(update_visibility)
                
                with ui.row().classes('w-full gap-2') as host_row:
                    host_input = ui.input('Host / IP', value=host_val).classes('flex-grow').props('outlined dense')
                    port_input = ui.number('Puerto', value=port_val).classes('w-24').props('outlined dense')
                
                db_input = ui.input('Base de Datos', value=db_val).classes('w-full').props('outlined dense')
                
                with ui.row().classes('w-full gap-2') as user_row:
                    user_input = ui.input('Usuario', value=user_val).classes('flex-grow').props('outlined dense')
                    pass_input = ui.input('Contraseña', password=True, value=pass_val).classes('flex-grow').props('outlined dense')
                    
                ssl_check = ui.checkbox('Habilitar SSL', value=ssl_val)
                
                # Init visibility
                update_visibility()

                # Botón de Prueba
                async def run_test():
                    # Validación básica
                    if not name_input.value:
                        ui.notify("Nombre requerido", type='warning')
                        return
                    if type_select.value != 'sqlite' and not host_input.value:
                        ui.notify("Host requerido", type='warning')
                        return

                    ui.notify("Probando credenciales...", type='info')
                    
                    # Guardar temporal
                    try:
                        temp_pass_encrypted = self.encryption.encrypt({"password": pass_input.value or ""})
                        
                        temp_conn = DatabaseCredentialConfig(
                            name=f"TEMP_TEST_{datetime.now().timestamp()}",
                            db_type=type_select.value,
                            host=host_input.value or "",
                            port=int(port_input.value or 0),
                            database=db_input.value or "",
                            username=user_input.value or "",
                            encrypted_password=temp_pass_encrypted,
                            ssl_enabled=ssl_check.value,
                            is_active=True
                        )
                        
                        async with AsyncSession(client_engine) as session:
                            session.add(temp_conn)
                            await session.commit()
                            await session.refresh(temp_conn)
                            temp_id = temp_conn.id
                        
                        # Test
                        success, msg = await sql_connector_service.test_connection(temp_id)
                        
                        # Borrar temporal
                        async with AsyncSession(client_engine) as session:
                             t_conn = await session.get(DatabaseCredentialConfig, temp_id)
                             if t_conn:
                                 await session.delete(t_conn)
                                 await session.commit()

                        if success:
                            ui.notify("Conexión Exitosa", type='positive')
                        else:
                            ui.notify(f"Fallo: {msg}", type='negative')

                    except Exception as e:
                        ui.notify(f"Error en prueba: {e}", type='negative')

                ui.button('PROBAR CONEXIÓN', icon='science', on_click=run_test).props('flat color=amber dense w-full')


            async def on_save():
                if not name_input.value:
                    ui.notify("Nombre es obligatorio", type='warning')
                    return
                if not db_input.value:
                    ui.notify("Base de datos / Ruta es obligatoria", type='warning')
                    return

                try:
                    async with AsyncSession(client_engine) as session:
                        if conn:
                            # Update
                            db_conn = await session.get(DatabaseCredentialConfig, conn.id)
                            db_conn.name = name_input.value
                            db_conn.db_type = type_select.value
                            db_conn.host = host_input.value or ""
                            db_conn.port = int(port_input.value or 0)
                            db_conn.database = db_input.value
                            db_conn.username = user_input.value or ""
                            db_conn.ssl_enabled = ssl_check.value
                            
                            # Only update password if provided
                            if pass_input.value:
                                db_conn.encrypted_password = self.encryption.encrypt({"password": pass_input.value})
                            
                            db_conn.updated_at = datetime.utcnow()
                            session.add(db_conn)
                        else:
                            # Create
                            new_conn = DatabaseCredentialConfig(
                                name=name_input.value,
                                db_type=type_select.value,
                                host=host_input.value or "",
                                port=int(port_input.value or 0),
                                database=db_input.value,
                                username=user_input.value or "",
                                encrypted_password=self.encryption.encrypt({"password": pass_input.value or ""}),
                                ssl_enabled=ssl_check.value,
                                is_active=True
                            )
                            session.add(new_conn)
                        
                        await session.commit()
                    
                    ui.notify("Conexión guardada correctamente", type='positive')
                    await self.load_connections()
                    dialog.close()

                except Exception as e:
                    ui.notify(f"Error al guardar: {e}", type='negative')

            with ui.row().classes('w-full justify-end mt-6 gap-2'):
                ui.button('CANCELAR', on_click=dialog.close).props('flat')
                ui.button('GUARDAR', on_click=on_save).props('color=primary unelevated')
        
        dialog.open()

    @ui.refreshable
    def render_table(self):
        """Renderiza la tabla de conexiones."""
        if not self.connections:
            with ui.column().classes('w-full items-center py-12 bg-slate-50 rounded-lg border border-dashed border-slate-300 h-64 justify-center'):
                ui.icon('dns', size='xl').classes('text-slate-300 mb-4')
                ui.label('No hay bases de datos configuradas').classes('text-slate-500 font-medium')
                ui.label('Añade conexiones a MySQL, PostgreSQL, SQL Server o SQLite para usarlas en tus flujos.').classes('text-sm text-slate-400 mb-4')
                ui.button('Nueva Conexión', icon='add', on_click=lambda: self.open_connection_dialog()).props('unelevated color=primary')
            return

        with ui.column().classes('w-full gap-4'):
            with ui.row().classes('w-full justify-between items-center mb-2'):
                ui.label(f'{len(self.connections)} Conexiones Disponibles').classes('text-sm font-bold text-slate-500 uppercase tracking-wider')
                ui.button('Nueva Conexión', icon='add', on_click=lambda: self.open_connection_dialog()).props('unelevated color=primary dense')

            # Cards Grid
            with ui.grid(columns=2).classes('w-full gap-4'):
                for c in self.connections:
                    with ui.card().classes('w-full p-0 border border-slate-200 shadow-sm hover:shadow-md transition-shadow'):
                        # Header Color based on Type
                        header_color = 'bg-slate-100'
                        icon = 'storage'
                        if c.db_type == 'mysql': header_color, icon = 'bg-blue-50', 'storage'
                        elif c.db_type == 'postgresql': header_color, icon = 'bg-indigo-50', 'storage'
                        elif c.db_type == 'sqlserver': header_color, icon = 'bg-red-50', 'storage'
                        elif c.db_type == 'sqlite': header_color, icon = 'bg-green-50', 'description'

                        with ui.row().classes(f'w-full p-3 {header_color} border-b border-slate-100 items-center justify-between'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon(icon).classes('text-slate-500')
                                ui.label(c.name).classes('font-bold text-slate-700')
                            
                            ui.label(c.db_type.upper()).classes('text-[10px] font-bold px-2 py-0.5 bg-white rounded border border-slate-200 text-slate-500')

                        with ui.column().classes('w-full p-4 gap-1'):
                            # Detalle
                            if c.db_type == 'sqlite':
                                ui.label(c.database).classes('text-xs font-mono text-slate-600 break-all')
                            else:
                                ui.label(f"{c.username} @ {c.host}:{c.port}").classes('text-xs font-mono text-slate-600')
                                ui.label(f"DB: {c.database}").classes('text-xs text-slate-400')

                            # Actions
                            with ui.row().classes('w-full justify-end mt-2 pt-2 border-t border-slate-50 gap-2'):
                                ui.button(icon='science', on_click=lambda x=c.id: self.handle_test(x)).props('flat round dense color=amber').tooltip('Probar Conexión')
                                ui.button(icon='edit', on_click=lambda x=c: self.open_connection_dialog(x)).props('flat round dense color=blue').tooltip('Editar')
                                ui.button(icon='delete', on_click=lambda x=c.id: self.handle_delete(x)).props('flat round dense color=red').tooltip('Eliminar')

    def render(self):
        ui.timer(0.1, self.load_connections, once=True)
        self.render_table()
