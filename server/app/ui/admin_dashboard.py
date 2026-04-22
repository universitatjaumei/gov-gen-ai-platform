
"""
Dashboard principal del SuperAdmin.

Proporciona una visión consolidada del estado del sistema mediante KPIs 
globales que incluyen el número de partners, clientes, licencias activas 
y consumo total de tokens en el mes corriente.
"""
from nicegui import ui
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
from client_app.app.core.state import state

from server.app.database.db import server_engine
from server.app.database.models import PartnerAccount, ClientAccount, License, BillingRecord

def admin_dashboard_content():
    """
    Renderiza la interfaz del Dashboard de Administración.
    
    Ejecuta consultas asíncronas para cargar métricas y genera tarjetas de 
    navegación hacia las secciones principales del panel.
    """
    t = state.i18n.t

    class DashState:
        total_partners: int = 0
        total_clients: int = 0
        active_licenses: int = 0
        total_tokens_month: int = 0
        loading: bool = True

    dash_state = DashState()

    async def load_kpis():
        async with AsyncSession(server_engine) as session:
            # Partners
            stmt = select(func.count(PartnerAccount.partner_id))
            try:
                result = await session.exec(stmt)
                dash_state.total_partners = result.first() or 0
            except: dash_state.total_partners = 0

            # Clients
            stmt = select(func.count(ClientAccount.client_id))
            try:
                result = await session.exec(stmt)
                dash_state.total_clients = result.first() or 0
            except: dash_state.total_clients = 0

            # Active Licenses
            stmt = select(func.count(License.license_id)).where(License.status == "active")
            try:
                result = await session.exec(stmt)
                dash_state.active_licenses = result.first() or 0
            except: dash_state.active_licenses = 0
            
            # Total Tokens Month
            first_day = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
            stmt = select(func.sum(BillingRecord.tokens_used)).where(BillingRecord.timestamp >= first_day)
            try:
                result = await session.exec(stmt)
                dash_state.total_tokens_month = result.first() or 0
            except: dash_state.total_tokens_month = 0

        dash_state.loading = False
        kpi_container.refresh()


    
    # --- NAVIGATION CARDS ---
    
    ADMIN_CARDS = [
        {
            'name': t('admin.dashboard.card_partners_title'),
            'desc': t('admin.dashboard.card_partners_desc'),
            'icon': 'business',
            'color': 'indigo',
            'route': '/admin/partners'
        },
        {
            'name': t('admin.dashboard.card_clients_title'),
            'desc': t('admin.dashboard.card_clients_desc'),
            'icon': 'badge',
            'color': 'blue',
            'route': '/admin/clients'
        },
        {
            'name': t('admin.dashboard.card_licenses_title'),
            'desc': t('admin.dashboard.card_licenses_desc'),
            'icon': 'verified_user',
            'color': 'green',
            'route': '/admin/licenses'
        },
        {
            'name': t('admin.dashboard.card_ai_title'),
            'desc': t('admin.dashboard.card_ai_desc'),
            'icon': 'psychology',
            'color': 'purple',
            'route': '/admin/ai-config'
        },
        {
            'name': t('admin.dashboard.card_prompts_title'),
            'desc': t('admin.dashboard.card_prompts_desc'),
            'icon': 'edit_note',
            'color': 'pink',
            'route': '/admin/prompts'
        }
    ]

    def render_card(card_data):
        color = card_data['color']
        name = card_data['name']
        desc = card_data['desc']
        route = card_data['route']
        
        with ui.card().classes(f'w-full p-3 hover:shadow-md transition-all border-l-4 border-{color}-500 flex-row items-center gap-4 cursor-pointer shadow-sm').on('click', lambda: ui.navigate.to(route)):
            with ui.column().classes(f'p-2 bg-{color}-50 rounded-lg'):
                ui.icon(card_data['icon'], size='1.5em').classes(f'text-{color}-600')
            
            with ui.column().classes('flex-grow gap-0'):
                ui.label(name).classes('font-bold text-sm text-slate-800')
                ui.label(desc).classes('text-[10px] text-gray-400 leading-tight line-clamp-1')

            ui.button(icon='arrow_forward', on_click=lambda: ui.navigate.to(route)) \
                .props(f'flat round dense color={color}').classes('ml-auto')


    
    @ui.refreshable
    def kpi_container():
        if dash_state.loading:
            ui.spinner('dots', size='lg')
            return

        with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3'):
            # KPI 1: Partners
            with ui.card().classes('p-3 flex-row gap-3 items-center bg-white shadow-sm border border-gray-100 hover:shadow-md transition-shadow'):
                with ui.column().classes('p-2 bg-indigo-50 rounded-full'):
                    ui.icon('business', size='1.5em').classes('text-indigo-600')
                with ui.column().classes('gap-0'):
                    ui.label(str(dash_state.total_partners)).classes('text-base font-bold leading-none text-slate-700')
                    ui.label(t('admin.dashboard.kpi_partners')).classes('text-[10px] text-gray-400 uppercase font-bold tracking-wider')
            
            # KPI 2: Clientes
            with ui.card().classes('p-3 flex-row gap-3 items-center bg-white shadow-sm border border-gray-100 hover:shadow-md transition-shadow'):
                with ui.column().classes('p-2 bg-blue-50 rounded-full'):
                    ui.icon('badge', size='1.5em').classes('text-blue-600')
                with ui.column().classes('gap-0'):
                    ui.label(str(dash_state.total_clients)).classes('text-base font-bold leading-none text-slate-700')
                    ui.label(t('admin.dashboard.kpi_clients')).classes('text-[10px] text-gray-400 uppercase font-bold tracking-wider')

            # KPI 3: Licencias
            with ui.card().classes('p-3 flex-row gap-3 items-center bg-white shadow-sm border border-gray-100 hover:shadow-md transition-shadow'):
                with ui.column().classes('p-2 bg-green-50 rounded-full'):
                    ui.icon('verified_user', size='1.5em').classes('text-green-600')
                with ui.column().classes('gap-0'):
                    ui.label(str(dash_state.active_licenses)).classes('text-base font-bold leading-none text-slate-700')
                    ui.label(t('admin.dashboard.kpi_licenses')).classes('text-[10px] text-gray-400 uppercase font-bold tracking-wider')
            
            # KPI 4: Tokens Globales
            with ui.card().classes('p-3 flex-row gap-3 items-center bg-white shadow-sm border border-gray-100 hover:shadow-md transition-shadow'):
                with ui.column().classes('p-2 bg-orange-50 rounded-full'):
                    ui.icon('token', size='1.5em').classes('text-orange-600')
                with ui.column().classes('gap-0'):
                    ui.label(f"{dash_state.total_tokens_month:,}").classes('text-base font-bold leading-none text-slate-700')
                    ui.label(t('admin.dashboard.kpi_tokens')).classes('text-[10px] text-gray-400 uppercase font-bold tracking-wider')

    # --- RENDER MAIN LAYOUT ---

    ui.label(t('admin.dashboard.title')).classes('text-2xl font-bold mb-6 text-slate-800')

    kpi_container()
    
    ui.separator().classes('my-8')
    
    ui.label(t('admin.dashboard.subtitle')).classes('text-xl font-bold mb-4 text-slate-700')
    
    with ui.grid().classes('w-full gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 items-stretch'):
        for card in ADMIN_CARDS:
            render_card(card)

    ui.timer(0.1, load_kpis, once=True)

