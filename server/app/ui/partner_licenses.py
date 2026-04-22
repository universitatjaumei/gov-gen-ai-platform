
"""
Panel de Administración de Licencias para Partners.

Permite gestionar las cuotas de tokens y periodos de validez de las 
licencias activas de sus clientes, proporcionando un historial detallado 
de modificaciones y auditoría.
"""
from datetime import datetime
from nicegui import ui
from sqlmodel.ext.asyncio.session import AsyncSession
import asyncio

from server.app.database.db import server_engine
from server.app.ui.partner_layout import partner_layout, PartnerContext
from server.app.services.partner_license_service import PartnerLicenseService
from automatia_shared.enums import LicenseStatus


def partner_licenses_content(ctx: PartnerContext):
    """Contenido de la pagina de licencias."""

    class LicenseState:
        licenses = []
        alerts_expiring = []
        alerts_quota = []
        loading = True

        # Dialogs
        quota_dialog_open = False
        selected_license = None # License object
        add_tokens = 50000

        validity_dialog_open = False
        add_days = 30

        audit_dialog_open = False
        audit_logs = []

        # Consumption dialog
        consumption_dialog_open = False
        consumption_data = None

    state = LicenseState()

    async def load_data():
        state.loading = True
        state.licenses = []
        state.alerts_expiring = []
        state.alerts_quota = []
        license_table.refresh()
        alerts_section.refresh()

        async with AsyncSession(server_engine) as session:
            service = PartnerLicenseService(session, ctx.partner_id)
            all_lics = await service.list_licenses()
            
            # Enrich with client name manually or via join in service (service returns License with relationships lazy loaded usually)
            # For this UI, we need client name. The list_licenses joins ClientAccount but returns License objects.
            # We rely on lazy loading or eager loading. Since we are in async session context, lazy load might fail if session closed.
            # But here we are inside the session context block.
            
            # However, for robustness, we will fetch data flat or use a joined query.
            # Service implementation uses select(License).join(...) returning License objects. 
            # We need to ensure we can access license.client.name OR update query in service.
            # Let's assume for now we might need to fetch client details separately or rely on service.
            # To be safe and fast, let's just assume we can get basic info, or we modify service to return tuples.
            # Given existing code, let's try accessing client relationship if configured in SQLModel, 
            # otherwise simplistic approach: Service ensures filtering.
            
            # WORKAROUND: For pure display speed without complex N+1, we might just list licenses.
            # But the user needs to know WHICH client.
            # I will assume SQLModel relationship is working within session.
            
            state.licenses = all_lics
            
            state.alerts_expiring = await service.get_expiring_soon(days=15)
            state.alerts_quota = await service.get_low_quota(threshold_percent=20)

        state.loading = False
        license_table.refresh()
        alerts_section.refresh()


    async def adjust_quota():
        if not state.selected_license: return
        
        async with AsyncSession(server_engine) as session:
            service = PartnerLicenseService(session, ctx.partner_id)
            await service.adjust_quota(state.selected_license.license_id, int(state.add_tokens))
            ui.notify(f"Quota aumentada en {state.add_tokens} tokens", type='positive')
        
        state.quota_dialog_open = False
        await load_data()


    async def extend_validity():
        if not state.selected_license: return

        async with AsyncSession(server_engine) as session:
            service = PartnerLicenseService(session, ctx.partner_id)
            await service.extend_validity(state.selected_license.license_id, int(state.add_days))
            ui.notify(f"Validez extendida en {state.add_days} dias", type='positive')

        state.validity_dialog_open = False
        await load_data()


    async def toggle_status(lic):
        try:
            async with AsyncSession(server_engine) as session:
                service = PartnerLicenseService(session, ctx.partner_id)
                if lic.status == LicenseStatus.ACTIVE.value:
                    await service.suspend_license(lic.license_id, reason="Manual suspension")
                    ui.notify("Licencia suspendida", type='warning')
                else:
                    await service.reactivate_license(lic.license_id)
                    ui.notify("Licencia reactivada", type='positive')
            await load_data()
        except Exception as e:
            ui.notify(str(e), type='negative')


    async def load_audit(lic):
        async with AsyncSession(server_engine) as session:
            service = PartnerLicenseService(session, ctx.partner_id)
            state.audit_logs = await service.get_license_audit(lic.license_id)
            state.audit_dialog_open = True
            audit_dialog.refresh()

    async def load_consumption(lic):
        state.selected_license = lic
        state.consumption_data = None
        state.consumption_dialog_open = True
        consumption_dialog.refresh()

        from server.app.services.consumption_query_service import ConsumptionQueryService
        async with AsyncSession(server_engine) as session:
            service = ConsumptionQueryService(session)
            state.consumption_data = await service.get_license_summary(lic.license_id)

        consumption_dialog.refresh()

    def open_quota_dialog(lic):
        state.selected_license = lic
        state.quota_dialog_open = True
        quota_dialog.refresh()

    def open_validity_dialog(lic):
        state.selected_license = lic
        state.validity_dialog_open = True
        validity_dialog.refresh()


    # --- UI COMPONENTS ---

    with ui.column().classes('w-full gap-6'):
        
        with ui.row().classes('w-full justify-between items-center'):
            ui.label("Gestion de Licencias").classes('text-2xl font-bold')
            ui.button(icon='refresh', on_click=load_data).props('flat round dense')

        # ALERTS SECTION
        @ui.refreshable
        def alerts_section():
            if not state.alerts_expiring and not state.alerts_quota:
                return

            with ui.row().classes('w-full gap-4 mb-4'):
                if state.alerts_expiring:
                    with ui.card().classes('bg-red-50 border-l-4 border-red-500 p-4 flex-1'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('warning', size='sm').classes('text-red-600')
                            ui.label("Expira Pronto").classes('font-bold text-red-800')
                        ui.label(f"{len(state.alerts_expiring)} licencias expiran en < 15 dias").classes('text-sm text-red-700')

                if state.alerts_quota:
                    with ui.card().classes('bg-orange-50 border-l-4 border-orange-500 p-4 flex-1'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('battery_alert', size='sm').classes('text-orange-600')
                            ui.label("Quota Baja").classes('font-bold text-orange-800')
                        ui.label(f"{len(state.alerts_quota)} licencias con < 20% quota").classes('text-sm text-orange-700')

        alerts_section()

        # TABLE
        @ui.refreshable
        def license_table():
            if state.loading:
                ui.spinner('dots', size='lg').classes('w-full text-center py-8')
                return

            if not state.licenses:
                ui.label("No hay licencias activas.").classes('w-full text-center italic text-gray-500')
                return

            with ui.card().classes('w-full p-0 gap-0'):
                # Header
                with ui.row().classes('w-full bg-slate-100 p-3 font-bold text-gray-700 border-b'):
                    ui.label("ID Licencia").classes('w-1/6')
                    # ui.label("Cliente").classes('w-1/5') 
                    ui.label("Quota Consumida").classes('w-1/5') # Reduced from 1/4
                    ui.label("Validez").classes('w-1/6')
                    ui.label("Estado").classes('w-1/6')
                    ui.label("Acciones").classes('flex-1 text-right min-w-[150px]') # Ensure minimum width for icons

                # Rows
                for lic in state.licenses:
                     with ui.row().classes('w-full p-3 border-b hover:bg-slate-50 items-center'):
                        ui.label(lic.license_id).classes('w-1/6 font-mono text-xs')
                        
                        # Usage Bar
                        with ui.column().classes('w-1/5 gap-1'): # Reduced from 1/4 (matches header)
                            pct = 0
                            if lic.quota_tokens > 0:
                                pct = (lic.consumed_tokens / lic.quota_tokens)
                            
                            color = 'green' if pct < 0.8 else 'orange' if pct < 0.95 else 'red'
                            ui.linear_progress(value=pct).props(f'color={color}').classes('h-2 rounded')
                            ui.label(f"{lic.consumed_tokens:,} / {lic.quota_tokens:,}").classes('text-xs text-gray-500')

                        # Validity
                        days_left = (lic.valid_until - datetime.utcnow()).days
                        valid_color = 'text-red-500 font-bold' if days_left < 15 else 'text-gray-700'
                        ui.label(f"{lic.valid_until.strftime('%Y-%m-%d')} ({days_left} dias)").classes(f'w-1/6 text-sm {valid_color}')

                        # Status
                        is_active = lic.status.upper() == 'ACTIVE'
                        status_color = 'green' if is_active else 'red'
                        ui.badge(lic.status.upper(), color=status_color).classes('w-1/6')

                        # Actions
                        with ui.row().classes('flex-1 justify-end gap-1'):
                            ui.button(icon='bar_chart', on_click=lambda l=lic: load_consumption(l)).props('flat dense round color=teal').tooltip('Ver Consumo')
                            ui.button(icon='add_circle', on_click=lambda l=lic: open_quota_dialog(l)).props('flat dense round color=blue').tooltip('Aumentar Quota')
                            ui.button(icon='event_repeat', on_click=lambda l=lic: open_validity_dialog(l)).props('flat dense round color=green').tooltip('Extender Validez')

                            pause_icon = 'play_arrow' if lic.status == 'SUSPENDED' else 'pause'
                            ui.button(icon=pause_icon, on_click=lambda l=lic: toggle_status(l)).props('flat dense round color=orange').tooltip('Suspender/Reactivar')

                            ui.button(icon='history', on_click=lambda l=lic: load_audit(l)).props('flat dense round color=grey').tooltip('Ver Auditoría')

        license_table()


        # DIALOGS
        @ui.refreshable
        def quota_dialog():
            with ui.dialog() as dialog, ui.card():
                dialog.bind_visibility_from(state, 'quota_dialog_open')
                ui.label("Aumentar Quota de Tokens").classes('text-lg font-bold mb-4')
                
                if state.selected_license:
                    ui.label(f"Licencia: {state.selected_license.license_id}").classes('text-sm text-gray-500 mb-2')
                
                ui.number("Tokens a añadir", value=50000, step=1000).bind_value(state, 'add_tokens').classes('w-full').props('outlined')
                
                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button("Cancelar", on_click=dialog.close).props('flat')
                    ui.button("Aplicar", on_click=adjust_quota).props('color=primary')

        @ui.refreshable
        def validity_dialog():
            with ui.dialog() as dialog, ui.card():
                dialog.bind_visibility_from(state, 'validity_dialog_open')
                ui.label("Extender Validez").classes('text-lg font-bold mb-4')
                
                if state.selected_license:
                    ui.label(f"Licencia: {state.selected_license.license_id}").classes('text-sm text-gray-500 mb-2')

                ui.number("Días a añadir", value=30, step=1).bind_value(state, 'add_days').classes('w-full').props('outlined')

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button("Cancelar", on_click=dialog.close).props('flat')
                    ui.button("Aplicar", on_click=extend_validity).props('color=primary')

        @ui.refreshable
        def audit_dialog():
             with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl'):
                dialog.bind_visibility_from(state, 'audit_dialog_open')
                ui.label("Historial de Cambios").classes('text-lg font-bold mb-4')

                if not state.audit_logs:
                    ui.label("No hay registros.").classes('italic text-gray-500')
                else:
                    with ui.column().classes('w-full gap-2 max-h-96 overflow-y-auto'):
                        for log in state.audit_logs:
                            with ui.row().classes('w-full p-2 border rounded items-start gap-3 bg-gray-50'):
                                ui.label(log['timestamp'][:16].replace('T', ' ')).classes('text-xs font-mono text-gray-500 w-24')
                                with ui.column().classes('flex-1 gap-0'):
                                    ui.label(log['action']).classes('font-bold text-sm')
                                    # Format details nicely
                                    import json
                                    details_str = json.dumps(log['details'], ensure_ascii=False)
                                    ui.label(details_str).classes('text-xs text-gray-600 break-all')

                ui.button("Cerrar", on_click=dialog.close).classes('mt-4 w-full')

        @ui.refreshable
        def consumption_dialog():
            with ui.dialog() as dialog, ui.card().classes('w-full max-w-3xl'):
                dialog.bind_visibility_from(state, 'consumption_dialog_open')
                ui.label("Consumo de Licencia").classes('text-lg font-bold mb-4')

                data = state.consumption_data

                if not data:
                    ui.spinner('dots', size='lg')
                    ui.label("Cargando datos de consumo...").classes('text-gray-500')
                elif data.get('error'):
                    ui.label(f"Error: {data['error']}").classes('text-red-500')
                else:
                    # Info básica
                    with ui.row().classes('w-full gap-4 mb-4'):
                        ui.label(f"Cliente: {data.get('client_name', 'N/A')}").classes('font-bold')
                        ui.label(f"Licencia: {data.get('license_id', 'N/A')}").classes('text-gray-500')

                    # KPI Cards
                    with ui.row().classes('w-full gap-4 mb-4'):
                        with ui.card().classes('flex-1 p-4 bg-blue-50'):
                            ui.label('Tokens Consumidos').classes('text-sm text-gray-600')
                            ui.label(f"{data.get('consumed_tokens', 0):,}").classes('text-2xl font-bold text-blue-800')

                        with ui.card().classes('flex-1 p-4 bg-green-50'):
                            ui.label('Coste Total USD').classes('text-sm text-gray-600')
                            ui.label(f"${data.get('total_cost_usd', 0):.4f}").classes('text-2xl font-bold text-green-800')

                        with ui.card().classes('flex-1 p-4 bg-purple-50'):
                            ui.label('Tokens Restantes').classes('text-sm text-gray-600')
                            ui.label(f"{data.get('remaining_tokens', 0):,}").classes('text-2xl font-bold text-purple-800')

                    # Barra de progreso
                    usage_pct = data.get('usage_percent', 0)
                    ui.label(f"Uso: {usage_pct:.1f}%").classes('text-sm')
                    color = 'green' if usage_pct < 70 else 'orange' if usage_pct < 90 else 'red'
                    ui.linear_progress(value=usage_pct/100).props(f'color={color}').classes('rounded mb-4')

                    # Últimas operaciones
                    ops = data.get('recent_operations', [])
                    if ops:
                        ui.label('Últimas Operaciones').classes('font-bold mb-2')
                        with ui.column().classes('w-full max-h-64 overflow-y-auto'):
                            for op in ops:
                                with ui.row().classes('w-full p-2 border-b text-sm items-center'):
                                    ui.label(op.get('timestamp', '')).classes('w-32 text-gray-500 font-mono text-xs')
                                    ui.label(op.get('model_id', 'N/A')).classes('flex-1')
                                    ui.label(f"{op.get('tokens_used', 0):,}").classes('w-24 text-right')
                                    ui.label(f"${op.get('cost_usd', 0):.6f}").classes('w-24 text-right text-green-600')
                    else:
                        ui.label('No hay operaciones registradas').classes('text-gray-500 italic')

                ui.button("Cerrar", on_click=dialog.close).classes('mt-4 w-full')

        quota_dialog()
        validity_dialog()
        audit_dialog()
        consumption_dialog()

    # Init
    ui.timer(0.1, load_data, once=True)
