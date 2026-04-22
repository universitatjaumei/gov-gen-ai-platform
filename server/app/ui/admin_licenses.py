
"""
Panel de Monitorización y Control de Licencias.

Ofrece una visión detallada del ciclo de vida de las licencias, permitiendo 
visualizar el consumo de tokens frente a las cuotas asignadas y el historial 
de operaciones de cada cliente.
"""
from nicegui import ui
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.database.models import License, ClientAccount, PartnerAccount, BillingRecord
from automatia_shared.enums import LicenseStatus
from datetime import datetime

# Helper Functions
def get_status_color(license_obj: License) -> str:
    if license_obj.status != LicenseStatus.ACTIVE.value: return "red"
    if license_obj.consumed_tokens >= license_obj.quota_tokens: return "red"
    if license_obj.valid_until:
        days_left = (license_obj.valid_until - datetime.utcnow()).days
        if days_left < 0: return "red"
        if days_left < 15: return "orange"
    return "green"

def get_status_label(license_obj: License) -> str:
    if license_obj.status != LicenseStatus.ACTIVE.value: return license_obj.status
    if license_obj.consumed_tokens >= license_obj.quota_tokens: return "QUOTA_EXCEEDED"
    if license_obj.valid_until and datetime.utcnow() > license_obj.valid_until: return "EXPIRED"
    days_left = (license_obj.valid_until - datetime.utcnow()).days
    if days_left < 15: return f"EXPIRING_SOON ({days_left}d)"
    return "ACTIVE"


def admin_licenses_content():
    ui.label('Licencias').classes('text-2xl font-bold mb-6 text-slate-800')
    
    with ui.card().classes('w-full p-4'):
        ui.label('Monitorización de Licencias y Consumo').classes('text-lg font-bold mb-4')
        
        # Table
        columns = [
            {'name': 'client', 'label': 'Cliente', 'field': 'client', 'sortable': True, 'align': 'left'},
            {'name': 'partner', 'label': 'Partner', 'field': 'partner', 'sortable': True, 'align': 'left'},
            {'name': 'status', 'label': 'Estado', 'field': 'status', 'sortable': True, 'align': 'center'},
            {'name': 'usage', 'label': '% Uso', 'field': 'usage_pct', 'sortable': True, 'align': 'right'},
            {'name': 'tokens', 'label': 'Tokens', 'field': 'tokens_display', 'align': 'right'},
            {'name': 'validity', 'label': 'Validez', 'field': 'valid_until', 'sortable': True, 'align': 'right'},
            {'name': 'actions', 'label': 'Detalles', 'field': 'actions', 'align': 'center'},
        ]
        
        license_table = ui.table(columns=columns, rows=[], row_key='license_id').classes('w-full')
        
        # Detail Dialog
        detail_dialog = ui.dialog()
        detail_state = {'row': None, 'consumption': None}

        with detail_dialog, ui.card().classes('w-full max-w-3xl'):
            ui.label('Detalle de Licencia y Consumo').classes('text-xl font-bold mb-4')

            @ui.refreshable
            def render_detail_content():
                row = detail_state['row']
                consumption = detail_state['consumption']

                if not row:
                    ui.label('Cargando...')
                    return

                # Info básica
                with ui.grid(columns=3).classes('w-full gap-4 mb-4'):
                    with ui.column():
                        ui.label('Cliente').classes('text-sm text-gray-500')
                        ui.label(row['client']).classes('font-bold')
                    with ui.column():
                        ui.label('Partner').classes('text-sm text-gray-500')
                        ui.label(row['partner']).classes('font-bold')
                    with ui.column():
                        ui.label('Licencia ID').classes('text-sm text-gray-500')
                        ui.label(row['license_id']).classes('font-bold')

                ui.separator().classes('my-4')

                # Estado y cuota
                with ui.grid(columns=3).classes('w-full gap-4 mb-4'):
                    with ui.column():
                        ui.label('Estado').classes('text-sm text-gray-500')
                        ui.badge(row['status_label'], color=row['color_status'])
                    with ui.column():
                        ui.label('Tokens Usados').classes('text-sm text-gray-500')
                        ui.label(row['tokens_display']).classes('font-bold')
                    with ui.column():
                        ui.label('Válida hasta').classes('text-sm text-gray-500')
                        ui.label(row['valid_until']).classes('font-bold')

                # Barra de progreso
                ui.label(f"Uso de Cuota: {row['usage_pct']}").classes('text-sm mt-2')
                ui.linear_progress(
                    value=row['usage_raw'],
                    size='20px',
                    show_value=False
                ).props(f"color={row['color_status']}").classes('rounded')

                ui.separator().classes('my-4')

                # Consumo detallado
                ui.label('Consumo y Costes').classes('text-lg font-bold mb-2')

                if consumption:
                    with ui.row().classes('w-full gap-4 mb-4'):
                        with ui.card().classes('flex-1 p-4 bg-blue-50'):
                            ui.label('Tokens Consumidos').classes('text-sm text-gray-600')
                            ui.label(f"{consumption.get('consumed_tokens', 0):,}").classes('text-2xl font-bold text-blue-800')

                        with ui.card().classes('flex-1 p-4 bg-green-50'):
                            ui.label('Coste Total USD').classes('text-sm text-gray-600')
                            ui.label(f"${consumption.get('total_cost_usd', 0):.4f}").classes('text-2xl font-bold text-green-800')

                        with ui.card().classes('flex-1 p-4 bg-purple-50'):
                            ui.label('Tokens Restantes').classes('text-sm text-gray-600')
                            ui.label(f"{consumption.get('remaining_tokens', 0):,}").classes('text-2xl font-bold text-purple-800')

                    # Últimas operaciones
                    if consumption.get('recent_operations'):
                        ui.label('Últimas Operaciones').classes('font-bold mt-4 mb-2')
                        op_columns = [
                            {'name': 'timestamp', 'label': 'Fecha', 'field': 'timestamp', 'align': 'left'},
                            {'name': 'operation', 'label': 'Operación', 'field': 'operation', 'align': 'left'},
                            {'name': 'model_id', 'label': 'Modelo', 'field': 'model_id', 'align': 'left'},
                            {'name': 'tokens_used', 'label': 'Tokens', 'field': 'tokens_used', 'align': 'right'},
                            {'name': 'cost_usd', 'label': 'USD', 'field': 'cost_usd', 'align': 'right'},
                        ]
                        ui.table(
                            columns=op_columns,
                            rows=consumption['recent_operations'],
                            row_key='timestamp'
                        ).classes('w-full').props('dense flat')
                    else:
                        ui.label('No hay operaciones registradas').classes('text-gray-500')
                else:
                    ui.label('Cargando datos de consumo...').classes('text-gray-500')

            render_detail_content()

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Cerrar', on_click=detail_dialog.close).props('flat')

        async def show_details(row):
            detail_state['row'] = row
            detail_state['consumption'] = None
            render_detail_content.refresh()
            detail_dialog.open()

            # Cargar consumo
            from server.app.services.consumption_query_service import ConsumptionQueryService
            async with AsyncSession(server_engine) as session:
                service = ConsumptionQueryService(session)
                detail_state['consumption'] = await service.get_license_summary(row['license_id'])

            render_detail_content.refresh()

        license_table.add_slot('body-cell-status', r'''
            <q-td :props="props">
                <q-badge :color="props.row.color_status">
                    {{ props.row.status_label }}
                </q-badge>
            </q-td>
        ''')
        
        license_table.add_slot('body-cell-actions', r'''
            <q-td :props="props">
                <q-btn size="sm" flat icon="visibility" @click="() => $parent.$emit('details', props.row)" />
            </q-td>
        ''')
        license_table.on('details', lambda e: show_details(e.args))

        async def refresh_licenses():
            async with AsyncSession(server_engine) as session:
                statement = select(License, ClientAccount, PartnerAccount)\
                    .join(ClientAccount, License.client_id == ClientAccount.client_id)\
                    .join(PartnerAccount, ClientAccount.partner_id == PartnerAccount.partner_id)
                results = await session.exec(statement)
                data = results.all()

                rows = []
                for lic, cli, part in data:
                    usage = 0
                    if lic.quota_tokens > 0:
                        usage = lic.consumed_tokens / lic.quota_tokens
                    
                    color = get_status_color(lic)
                    status_lbl = get_status_label(lic)
                    
                    rows.append({
                        'license_id': lic.license_id,
                        'client': cli.name,
                        'partner': part.name,
                        'status': lic.status,
                        'status_label': status_lbl,
                        'color_status': color,
                        'usage_pct': f"{usage*100:.1f}%",
                        'usage_raw': usage,
                        'tokens_display': f"{lic.consumed_tokens:,} / {lic.quota_tokens:,}",
                        'valid_until': lic.valid_until.strftime("%Y-%m-%d") if lic.valid_until else "N/A",
                    })
                license_table.rows = rows
                license_table.update()

        ui.timer(0.1, refresh_licenses, once=True)
        ui.button('Actualizar Tabla', icon='refresh', on_click=refresh_licenses).props('flat dense')
