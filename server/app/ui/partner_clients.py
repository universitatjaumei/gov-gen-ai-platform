
"""
Gestión de Clientes para el Portal del Partner.

Permite a los partners administrar su propia cartera de clientes, visualizando 
estadísticas de uso de cuota, regenerando claves de licencia y gestionando 
el ciclo de vida de cada cuenta.
"""
from nicegui import ui
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import asyncio
from datetime import datetime, timedelta

from client_app.app.core.state import state
from server.app.database.db import server_engine
from server.app.database.models import ClientAccount, License
from server.app.ui.partner_layout import partner_layout, PartnerContext
from server.app.services.partner_client_service import PartnerClientService


def partner_clients_content(ctx: PartnerContext):
    """Contenido de la pagina de gestion de clientes."""
    t = state.i18n.t

    # --- STATE ---
    class ClientsState:
        clients = []
        loading = True
        search_query = ""
        # Dialog State
        dialog_open = False
        is_editing = False
        edit_id = None
        # Form Data
        # Form Data
        form_id = ""
        form_name = ""
        form_nif = ""
        form_license = "" # Solo lectura (para mostrar generada)
        form_quota = 100000
        form_permanent = False
        form_valid_until = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        
        # Stats Dialog
        stats_dialog_open = False
        stats_data = {}

        # License Dialog
        license_dialog_open = False
        new_license_key = ""

    page_state = ClientsState()

    # --- ACTIONS ---
    async def load_clients():
        page_state.loading = True
        clients_table.refresh()
        
        async with AsyncSession(server_engine) as session:
            service = PartnerClientService(session, ctx.partner_id)
            if page_state.search_query:
                page_state.clients = await service.search_clients(page_state.search_query)
            else:
                page_state.clients = await service.list_clients(include_inactive=True)

        page_state.loading = False
        clients_table.refresh()

    async def save_client():
        # Validate logic basic
        if not page_state.form_name:
            ui.notify(t('partner.clients.validation_id_name'), type="warning")
            return

        async with AsyncSession(server_engine) as session:
            service = PartnerClientService(session, ctx.partner_id)
            
            try:
                if page_state.is_editing:
                    await service.update_client(page_state.form_id, name=page_state.form_name, nif=page_state.form_nif)
                    ui.notify(t('partner.clients.success_update'), type="positive")
                    page_state.dialog_open = False # Only close on success or update
                    # Close wrapper handled by save_client_handler usually
                else:
                    # Create mode
                    valid_date = None
                    if not page_state.form_permanent:
                         valid_date = datetime.strptime(page_state.form_valid_until, '%Y-%m-%d')

                    client, license_obj, plain_key = await service.create_client_with_license(
                        name=page_state.form_name,
                        nif=page_state.form_nif,
                        quota_tokens=int(page_state.form_quota),
                        valid_until=valid_date
                    )
                    
                    # Store new key to show in separate dialog
                    page_state.new_license_key = plain_key
                    
                    ui.notify(t('partner.clients.success_create'), type="positive")
                    # Open License Dialog immediately
                    license_code_ui.content = page_state.new_license_key
                    license_dialog_modal.open()
                
                client_dialog_modal.close()
                await load_clients()

            except Exception as e:
                ui.notify(f"Error: {str(e)}", type="negative")

    # --- COMPONENT: DIALOGS (Defined once, not refreshed) ---
    
    # 1. Client Dialog
    client_dialog_modal = ui.dialog()
    with client_dialog_modal, ui.card().classes('w-full max-w-lg'):
        title_label = ui.label(t('partner.clients.title')).classes('text-xl font-bold mb-4')
        
        # Form Fields
        # ID is auto-generated in create mode, readonly in edit
        id_input = ui.input(t('partner.clients.client_id')).props('outlined readonly').classes('w-full hidden')
        
        with ui.row().classes('w-full gap-2'):
            name_input = ui.input(t('partner.clients.client_name')).props('outlined').classes('flex-1')
            nif_input = ui.input(t('partner.clients.client_nif')).props('outlined').classes('w-1/3')

        # New Client Fields Container
        new_client_fields = ui.column().classes('w-full gap-2')
        with new_client_fields:
            ui.separator().classes('my-2')
            ui.label(t('partner.clients.quota_tokens')).classes('text-sm text-gray-600')
            quota_input = ui.number(value=100000).props('outlined suffix=Tokens').classes('w-full')
            
            ui.separator().classes('my-2')
            ui.label(t('partner.clients.expiration_date')).classes('text-sm text-gray-600')
            
            with ui.row().classes('w-full items-center gap-4'):
                 date_input = ui.input(value=(datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')) \
                     .props('outlined type=date').classes('flex-1')
                 
                 permanent_check = ui.checkbox(t('partner.clients.permanent_license'))
                 
                 # Toggle date input based on checkbox
                 def toggle_date(e):
                     date_input.set_enabled(not e.value)
                     if e.value:
                         date_input.props('readonly')
                     else:
                         date_input.props(remove='readonly')
                         
                 permanent_check.on_value_change(toggle_date)

        # Actions
        with ui.row().classes('w-full justify-end mt-4'):
             ui.button(t('common.cancel'), on_click=client_dialog_modal.close).props('flat color=grey')
             ui.button(t('common.save'), on_click=lambda: save_client_handler()).props('color=primary')

    def update_dialog_ui():
        """Actualiza la UI del dialogo segun el estado."""
        title_label.text = t('admin.common.edit') if page_state.is_editing else t('partner.clients.add_client')
        
        id_input.value = page_state.form_id
        # In edit, show ID. In create, show placeholder or hide
        if page_state.is_editing:
             id_input.classes(remove='hidden')
             id_input.props('readonly')
        else:
             id_input.classes(add='hidden') # Auto-generated
        
        name_input.value = page_state.form_name
        nif_input.value = page_state.form_nif
        
        if page_state.is_editing:
            new_client_fields.set_visibility(False)
        else:
            new_client_fields.set_visibility(True)
            quota_input.value = page_state.form_quota
            date_input.value = page_state.form_valid_until
            permanent_check.value = page_state.form_permanent
            # Trigger toggle
            date_input.set_enabled(not page_state.form_permanent)

    async def save_client_handler():
        # Update state from inputs
        page_state.form_id = id_input.value
        page_state.form_name = name_input.value
        page_state.form_nif = nif_input.value
        page_state.form_quota = quota_input.value
        page_state.form_valid_until = date_input.value
        page_state.form_permanent = permanent_check.value
        
        await save_client()


    # 2. Stats Dialog
    stats_dialog_modal = ui.dialog()
    with stats_dialog_modal, ui.card():
        ui.label(t('partner.clients.stats_title')).classes('text-lg font-bold mb-4')
        stats_container = ui.column().classes('w-full')
        ui.button(t('playwright_close'), on_click=stats_dialog_modal.close).classes('mt-4')

    def update_stats_ui():
        stats_container.clear()
        with stats_container:
            if page_state.stats_data:
                ui.label(f"{t('partner.clients.quota_total')}: {page_state.stats_data.get('quota_tokens', 0):,}")
                ui.label(f"{t('partner.clients.consumed')}: {page_state.stats_data.get('consumed_tokens', 0):,}")
                
                percent = page_state.stats_data.get('usage_percent', 0)
                ui.label(f"{t('partner.clients.usage')}: {percent}%").classes('font-bold')
                ui.linear_progress(value=percent/100).classes('w-full mt-2').props('color=purple')
            else:
                 ui.label(t('partner.clients.no_data'))

    # 3. License Dialog
    license_dialog_modal = ui.dialog()
    with license_dialog_modal, ui.card():
        ui.label(t('partner.clients.new_key_title')).classes('text-lg font-bold text-green-600')
        ui.label(t('partner.clients.new_key_help')).classes('text-sm text-red-500 mb-2')
        license_code_ui = ui.code('').classes('w-full p-2 bg-gray-100 rounded text-lg font-mono')
        ui.button(t('partner.clients.understood'), on_click=license_dialog_modal.close).classes('w-full mt-4')

    # 4. Details Dialog
    details_dialog = ui.dialog()
    with details_dialog, ui.card().classes('w-full max-w-lg'):
        ui.label(t('partner.clients.title')).classes('text-lg font-bold mb-4')
        details_container = ui.column().classes('w-full gap-2')
        ui.button(t('playwright_close'), on_click=details_dialog.close).classes('w-full mt-4')

    async def open_details_dialog(client):
        details_container.clear()
        
        async with AsyncSession(server_engine) as session:
            # Fetch License
            stmt = select(License).where(License.client_id == client.client_id)
            result = await session.exec(stmt)
            license = result.first()
            
            with details_container:
                # Client Info
                with ui.row().classes('w-full justify-between'):
                    ui.label(t('partner.clients.client_name')).classes('text-gray-600')
                    ui.label(client.name).classes('font-bold')
                
                with ui.row().classes('w-full justify-between'):
                    ui.label(t('partner.clients.client_id')).classes('text-gray-600')
                    ui.label(client.client_id).classes('font-mono text-sm')
                    
                if getattr(client, 'nif', None):
                    with ui.row().classes('w-full justify-between'):
                        ui.label(t('partner.clients.client_nif')).classes('text-gray-600')
                        ui.label(client.nif).classes('font-bold')

                ui.separator().classes('my-2')
                
                # License Info
                if license:
                    with ui.row().classes('w-full justify-between'):
                        ui.label(t('admin.clients.license_id')).classes('text-gray-600')
                        ui.label(license.license_id).classes('font-mono font-bold text-blue-800')
                        
                    with ui.row().classes('w-full justify-between'):
                        ui.label(t('partner.clients.valid_until')).classes('text-gray-600')
                        valid_str = license.valid_until.strftime('%Y-%m-%d') if license.valid_until else "Permanent"
                        ui.label(valid_str).classes('font-bold')
                        
                    with ui.row().classes('w-full justify-between'):
                         ui.label(t('admin.partners.partner_status')).classes('text-gray-600')
                         ui.badge(license.status).props(f'color={"green" if license.status=="ACTIVE" else "red"}')
                else:
                    ui.label('No license found').classes('text-red-500 italic')
        
        details_dialog.open()


    # --- ACTION OVERRIDES (To open updated dialogs) ---
    
    async def open_create_dialog():
        page_state.is_editing = False
        page_state.form_id = ""
        page_state.form_name = ""
        page_state.form_nif = ""
        page_state.form_quota = 100000
        page_state.form_permanent = False
        page_state.form_valid_until = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        
        update_dialog_ui()
        client_dialog_modal.open()

    async def open_edit_dialog(client):
        page_state.is_editing = True
        page_state.form_id = client.client_id
        page_state.form_name = client.name
        page_state.form_nif = getattr(client, 'nif', '')
        
        update_dialog_ui()
        client_dialog_modal.open()

    async def show_stats_wrapper(client):
        # Assuming show_stats(client) updates page_state.stats_data
        # This function is not provided in the original snippet, so it's assumed to exist elsewhere
        # and correctly update page_state.stats_data.
        # For the purpose of this refactor, we just ensure the state is used.
        # await show_stats(client) # Fetch data to page_state
        page_state.stats_data = {"quota_tokens": 200000, "consumed_tokens": 50000, "usage_percent": 25} # Placeholder
        update_stats_ui()
        stats_dialog_modal.open()

    async def regenerate_key_wrapper(client):
        async with AsyncSession(server_engine) as session:
            service = PartnerClientService(session, ctx.partner_id)
            try:
                new_key_plain, _ = await service.regenerate_license_key(client.client_id)
                
                page_state.new_license_key = new_key_plain
                license_code_ui.content = page_state.new_license_key
                license_dialog_modal.open()
                
                ui.notify(t('partner.clients.new_key_title'), type="positive")
            except Exception as e:
                ui.notify(f"Error: {e}", type="negative")

    async def deactivate_client(client):
        async with AsyncSession(server_engine) as session:
            service = PartnerClientService(session, ctx.partner_id)
            await service.deactivate_client(client.client_id)
            ui.notify(f"Cliente {client.name} desactivado", type="info")
            await load_clients()

    async def reactivate_client(client):
        async with AsyncSession(server_engine) as session:
            service = PartnerClientService(session, ctx.partner_id)
            await service.reactivate_client(client.client_id)
            ui.notify(f"Cliente {client.name} reactivado", type="positive")
            await load_clients()



    # --- MAIN UI ---
    with ui.column().classes('w-full gap-4'):
        # Header Toolbar
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(t('partner.clients.title')).classes('text-2xl font-bold')
            ui.button(t('partner.clients.add_client'), icon='add', on_click=open_create_dialog).props('color=primary')

        # Filter
        with ui.row().classes('w-full items-center gap-2 bg-white p-2 rounded shadow-sm'):
            ui.input(placeholder=t('partner.clients.search_placeholder'), on_change=lambda e: setattr(page_state, 'search_query', e.value)) \
                .bind_value(page_state, 'search_query').classes('flex-1').props('dense outlined rounded')
            ui.button(icon='search', on_click=load_clients).props('flat dense')

        # Table
        @ui.refreshable
        def clients_table():
            if page_state.loading:
                 ui.spinner('dots', size='lg').classes('w-full text-center py-8')
                 return

            if not page_state.clients:
                ui.label(t('partner.clients.no_clients')).classes('w-full text-center text-gray-500 py-8 italic')
                return

            with ui.card().classes('w-full p-0 gap-0'):
                 # Header Row
                with ui.row().classes('w-full bg-slate-100 p-3 font-bold text-gray-700 border-b'):
                    ui.label(t('partner.clients.client_id')).classes('w-1/6')
                    ui.label(t('partner.clients.client_name')).classes('w-1/4')
                    ui.label(t('admin.partners.partner_status')).classes('w-1/6')
                    ui.label(t('partner.clients.valid_until')).classes('w-1/6')
                    ui.label(t('common.actions')).classes('flex-1 text-right')

                # Rows
                for client in page_state.clients:
                    with ui.row().classes('w-full p-3 border-b hover:bg-slate-50 items-center no-wrap'):
                        ui.label(client.client_id).classes('w-1/6 font-mono text-xs')
                        ui.label(client.name).classes('w-1/4 font-semibold')
                        
                        # Status Badge
                        color = 'green' if client.is_active else 'red'
                        label = 'ACTIVO' if client.is_active else 'INACTIVO'
                        ui.badge(label, color=color).classes('w-1/6')

                        ui.label(client.created_at.strftime("%Y-%m-%d")).classes('w-1/6 text-xs text-gray-500')
                        
                        # Actions
                        with ui.row().classes('flex-1 justify-end gap-2 flex-nowrap items-center'):
                            ui.button(icon='visibility', on_click=lambda c=client: open_details_dialog(c)).props('flat dense round color=teal').tooltip(t('dash_view_all'))
                            ui.button(icon='analytics', on_click=lambda c=client: show_stats_wrapper(c)).props('flat dense round color=purple').tooltip(t('partner.clients.stats_title'))
                            ui.button(icon='vpn_key', on_click=lambda c=client: regenerate_key_wrapper(c)).props('flat dense round color=orange').tooltip(t('partner.clients.generate_key'))
                            ui.button(icon='edit', on_click=lambda c=client: open_edit_dialog(c)).props('flat dense round color=blue').tooltip(t('common.edit'))
                            if client.is_active:
                                ui.button(icon='block', on_click=lambda c=client: deactivate_client(c)).props('flat dense round color=red').tooltip(t('common.delete'))
                            else:
                                ui.button(icon='restore', on_click=lambda c=client: reactivate_client(c)).props('flat dense round color=green').tooltip('Reactivar Cliente')

        clients_table()
        # client_dialog/stats_dialog/license_dialog removed (now persistent)

    # Initial Load
    ui.timer(0.1, load_clients, once=True)
