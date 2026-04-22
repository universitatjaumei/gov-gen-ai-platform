"""
Panel de Configuración de IA para Administradores.

Permite gestionar los proveedores de LLM (Google, OpenRouter), asignar 
modelos específicos a cada rol del sistema (Extracción, Lógica, Supervisión) 
y programar tareas de mantenimiento del catálogo de modelos.
"""
from nicegui import ui
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.core.state import state
from server.app.database.db import server_engine
from server.app.database.models import AIConfig

# --- CONSTANTS ---
from server.app.services.model_fetcher import get_models_for_provider
from server.app.services.scheduler_service import scheduler_service

# --- CONSTANTS ---
PROVIDERS = ["google", "openrouter"]
DEFAULT_MODELS = {
    'extraccion_pdf': { 'google': 'gemini-2.5-flash', 'openrouter': 'openai/gpt-oss-120b' },
    'logico_navegacion': { 'google': 'gemini-3-flash-preview', 'openrouter': 'anthropic/claude-haiku-4.5' },
    'supervision': { 'google': 'gemini-3.1-pro-preview', 'openrouter': 'anthropic/claude-sonnet-4.5' }
}

def get_roles(t):
    return [
        {"key": "extraccion_pdf", "label": f"{t('admin_role_text')} (Tier 1)"},
        {"key": "logico_navegacion", "label": f"{t('admin_role_logic')} (Tier 2)"},
        {"key": "supervision", "label": f"{t('admin_role_supervision')} (Tier 3)"},
    ]

def admin_ai_content():
    t = state.i18n.t
    ui.label('Configuración IA').classes('text-2xl font-bold mb-6 text-slate-800')

    with ui.card().classes('w-full p-4 mb-6'):
        ui.label(t('admin_ai_config_section')).classes('text-lg font-bold mb-4')
        ui.label("Gestión de proveedores y modelos (Server-side)").classes('text-sm text-gray-500 mb-4')

        # Grid layout for roles
        with ui.grid(columns=3).classes('w-full gap-4'):
            for role in get_roles(t):
                with ui.card().classes('p-4 hover:shadow-md transition-shadow'):
                    ui.label(role["label"]).classes('font-bold text-slate-700 mb-2')

                    # Referencia al model_select para el handler
                    model_select_ref = {'select': None}
                    role_key = role["key"]

                    # Handler para cambio de proveedor
                    async def on_provider_change(e, r_key=role_key, m_ref=model_select_ref):
                        m_sel = m_ref['select']
                        if not m_sel:
                            return
                        provider = e.value if hasattr(e, 'value') else e
                        models = await get_models_for_provider(provider)
                        if not models:
                            default = DEFAULT_MODELS.get(r_key, {}).get(provider, '')
                            models = [default] if default else []
                        m_sel.options = models
                        # Seleccionar el modelo por defecto del proveedor
                        default_model = DEFAULT_MODELS.get(r_key, {}).get(provider, '')
                        if default_model in models:
                            m_sel.value = default_model
                        elif models:
                            m_sel.value = models[0]
                        m_sel.update()

                    # Container para selectores con espacio adecuado
                    with ui.column().classes('w-full gap-4'):
                        # Provider select PRIMERO
                        provider_select = ui.select(
                            PROVIDERS,
                            label=t('admin_provider'),
                            value='google',
                            on_change=on_provider_change
                        ).classes('w-full')

                        # Model select DESPUÉS
                        model_select = ui.select(
                            [],
                            label=t('admin_model')
                        ).classes('w-full').props('use-input')

                        # Guardar referencia
                        model_select_ref['select'] = model_select

                    # Load current config if exists
                    async def load_current(r_key=role["key"], p_sel=provider_select, m_sel=model_select):
                        async with AsyncSession(server_engine) as session:
                            conf = await session.get(AIConfig, r_key)

                            current_provider = 'google'
                            current_model = ''

                            if conf:
                                current_provider = conf.provider
                                current_model = conf.model_id
                            else:
                                current_provider = 'google'
                                current_model = DEFAULT_MODELS.get(r_key, {}).get('google', '')

                            # Cargar modelos para el proveedor
                            models = await get_models_for_provider(current_provider)
                            if not models:
                                default = DEFAULT_MODELS.get(r_key, {}).get(current_provider, '')
                                models = [default] if default else []

                            # Actualizar selectores
                            p_sel.options = PROVIDERS
                            p_sel.value = current_provider
                            m_sel.options = models
                            m_sel.value = current_model
                            p_sel.update()
                            m_sel.update()

                    ui.timer(0.1, load_current, once=True)

                    async def save_role_config(r=role, p=provider_select, m=model_select):
                        async with AsyncSession(server_engine) as session:
                            conf = await session.get(AIConfig, r["key"])
                            if not conf:
                                conf = AIConfig(role_key=r["key"], provider=p.value, model_id=m.value)
                                session.add(conf)
                                print(f"[Admin AI] CREATED new config: role={r['key']}, provider={p.value}, model={m.value}")
                            else:
                                print(f"[Admin AI] UPDATING config: role={r['key']}, OLD provider={conf.provider}, NEW provider={p.value}")
                                conf.provider = p.value
                                conf.model_id = m.value
                                session.add(conf)
                            await session.commit()

                            # Verify the save worked
                            verify = await session.get(AIConfig, r["key"])
                            print(f"[Admin AI] VERIFIED after commit: role={r['key']}, provider={verify.provider if verify else 'NOT FOUND'}")
                        ui.notify(f"Configuración de {r['label']} guardada.", type='positive')

                    async def test_api_connection(p=provider_select, m=model_select):
                        """Probar la conexión con la API del proveedor seleccionado."""
                        provider = p.value
                        model = m.value

                        if not model:
                            ui.notify("Selecciona un modelo primero", type='warning')
                            return

                        ui.notify(f"Probando conexión con {provider}...", type='info')

                        try:
                            from server.app.modules.brain.infrastructure.llm_gateway import ejecutar_tarea

                            config = {'provider': provider, 'model_id': model}
                            result = await ejecutar_tarea(
                                prompt="Responde únicamente con la palabra OK.",
                                config_rol=config,
                                script_origen="admin_ai_test"
                            )

                            if result.get("error"):
                                ui.notify(f"Error: {result['error']}", type='negative')
                            elif result.get("response"):
                                ui.notify(f"Conexión exitosa con {provider}/{model}", type='positive')
                            else:
                                ui.notify(f"Sin respuesta de {provider}/{model}", type='warning')
                        except Exception as e:
                            ui.notify(f"Error: {str(e)[:100]}", type='negative')

                    with ui.row().classes('w-full gap-2 mt-4'):
                        ui.button(icon='save', on_click=save_role_config).props('flat dense color=primary').tooltip('Guardar configuración')
                        ui.button(icon='science', on_click=test_api_connection).props('flat dense color=secondary').tooltip('Probar conexión API')

    # --- PROVIDER UPDATE SCHEDULER ---
    render_scheduler_section(t)


def render_scheduler_section(t):
    """Render the provider update scheduler section."""
    with ui.card().classes('w-full p-4 mt-6'):
        ui.label(t('admin.scheduler.section_title')).classes('text-lg font-bold mb-4')
        ui.label(t('admin.scheduler.section_desc')).classes('text-sm text-gray-500 mb-4')

        # State holders for UI elements
        scheduler_state = {'status': None}

        async def load_scheduler_status():
            scheduler_state['status'] = await scheduler_service.get_status()
            render_scheduler_ui.refresh()

        @ui.refreshable
        def render_scheduler_ui():
            status = scheduler_state['status']
            if not status:
                ui.spinner()
                return

            with ui.row().classes('w-full gap-6 items-start'):
                # Left: Status and config
                with ui.column().classes('flex-1 gap-4'):
                    # Status row
                    with ui.row().classes('items-center gap-4'):
                        status_color = 'green' if status.get('running') else 'gray'
                        status_icon = 'check_circle' if status.get('running') else 'cancel'
                        ui.icon(status_icon).classes(f'text-{status_color}-500 text-2xl')
                        ui.label(
                            t('admin.scheduler.status_running') if status.get('running')
                            else t('admin.scheduler.status_stopped')
                        ).classes(f'text-{status_color}-600 font-medium')

                        if status.get('next_run'):
                            from datetime import datetime
                            next_run = datetime.fromisoformat(status['next_run'])
                            ui.label(f"| {t('admin.scheduler.next_run')}: {next_run.strftime('%H:%M')}").classes('text-gray-500 text-sm')

                    # Config controls
                    with ui.row().classes('items-center gap-4'):
                        enabled_switch = ui.switch(
                            t('admin.scheduler.enabled_label'),
                            value=status.get('enabled', True)
                        )

                        ui.label(t('admin.scheduler.time_label')).classes('text-sm ml-4')
                        hour_select = ui.select(
                            options=[f"{h:02d}" for h in range(24)],
                            value=f"{status.get('refresh_hour', 3):02d}"
                        ).classes('w-20').props('dense')
                        ui.label(':').classes('text-lg')
                        minute_select = ui.select(
                            options=[f"{m:02d}" for m in range(0, 60, 5)],
                            value=f"{status.get('refresh_minute', 0):02d}"
                        ).classes('w-20').props('dense')

                    # Last run info
                    if status.get('last_run'):
                        from datetime import datetime
                        last_run = datetime.fromisoformat(status['last_run'])
                        ui.label(
                            f"{t('admin.scheduler.last_run')}: {last_run.strftime('%Y-%m-%d %H:%M')}"
                        ).classes('text-xs text-gray-400')

                # Right: Action buttons
                with ui.column().classes('gap-2'):
                    async def save_scheduler_config():
                        await scheduler_service.update_schedule(
                            enabled=enabled_switch.value,
                            hour=int(hour_select.value),
                            minute=int(minute_select.value)
                        )
                        ui.notify(t('admin.scheduler.config_saved'), type='positive')
                        await load_scheduler_status()

                    async def run_manual_refresh():
                        ui.notify(t('admin.scheduler.manual_started'), type='info')
                        await scheduler_service.run_now()
                        ui.notify(t('admin.scheduler.manual_completed'), type='positive')
                        await load_scheduler_status()

                    ui.button(
                        t('common.save'),
                        icon='save',
                        on_click=save_scheduler_config
                    ).props('color=primary dense')

                    ui.button(
                        t('admin.scheduler.run_now'),
                        icon='refresh',
                        on_click=run_manual_refresh
                    ).props('color=secondary outline dense')

        render_scheduler_ui()
        ui.timer(0.1, load_scheduler_status, once=True)
