"""
SchedulerPage - Configuración de la Acción de Programación.
Página para configurar la acción SCHEDULER que programa ejecuciones
automáticas de flujos (una vez, intervalo, o cron).
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from nicegui import ui
from sqlmodel import select

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.scheduler_service import (
    scheduler_service,
    ScheduleConfig,
    ScheduleType,
    ScheduledJob,
)
from client_app.app.database.models import FlowRegistry
from automatia_shared.enums import StepType
from client_app.app.ui.components.form_factory import AtomColorScheme
from client_app.app.ui.components.page_header import page_header


# --- STATE ---

class SchedulerPageState:
    def __init__(self):
        self.current_mode: str = 'library'  # library, design
        self.scheduled_jobs: List[ScheduledJob] = []
        self.flows: List[FlowRegistry] = []
        self.is_loading: bool = False


class DesignState:
    def __init__(self):
        self.name: str = ""
        self.flow_id: Optional[int] = None
        self.schedule_type: str = "once"  # once, interval, daily, weekly, cron
        # Para "once"
        self.run_date: str = ""
        self.run_time: str = "09:00"
        # Para "interval"
        self.interval_value: int = 1
        self.interval_unit: str = "hours"  # minutes, hours, days
        # Para "daily" / "weekly"
        self.hour: int = 9
        self.minute: int = 0
        self.days_of_week: List[str] = []  # mon, tue, wed, thu, fri, sat, sun
        # Para "cron"
        self.cron_expression: str = "0 9 * * *"
        # Estado
        self.is_saving: bool = False


# --- PAGE IMPLEMENTATION ---

async def scheduler_page(mode: str = 'library', job_id: Optional[str] = None):
    """Página principal de la acción Scheduler."""
    page_state = SchedulerPageState()
    design_state = DesignState()
    colors = AtomColorScheme.get_colors(StepType.SCHEDULER)
    t = state.i18n.t
    save_btn = None

    # --- LOGIC ---

    async def load_data():
        """Carga los datos iniciales: flujos y tareas programadas."""
        page_state.is_loading = True
        try:
            render_page.refresh()
        except:
            pass

        # Cargar flujos
        async with state.db_session() as session:
            stmt = select(FlowRegistry).where(FlowRegistry.is_active == True)
            result = await session.execute(stmt)
            page_state.flows = result.scalars().all()

        # Cargar tareas programadas
        page_state.scheduled_jobs = await scheduler_service.get_scheduled_jobs()

        page_state.is_loading = False
        try:
            render_page.refresh()
        except:
            pass

    def go_to_index():
        # Si viene desde un flujo, volver al flujo
        flow_id = None
        if state.flow_context and state.flow_context.get('mode') == 'contextual':
            flow_id = state.flow_context.get('flow_id')
        elif state.editing_flow and state.flow_id:
            flow_id = state.flow_id

        if flow_id:
            layout_manager.exit_design_mode_to_flow()
            state.clear_flow_context()
            state.clear_atom_editing_context()
            ui.navigate.to(f'/flows/{flow_id}')
            return

        ui.navigate.to('/triggers')

    async def start_new_design():
        design_state.__init__()
        # Establecer fecha por defecto a mañana
        tomorrow = datetime.now() + timedelta(days=1)
        design_state.run_date = tomorrow.strftime("%Y-%m-%d")
        layout_manager.enter_design_mode(StepType.SCHEDULER)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def handle_schedule():
        """Programa un nuevo flujo o disparador."""
        design_state.is_saving = True
        render_page.refresh()

        try:
            # Construir configuración
            config_dict = {
                "schedule_type": design_state.schedule_type,
            }

            if design_state.schedule_type == "once":
                config_dict["run_date"] = f"{design_state.run_date}T{design_state.run_time}:00"

            elif design_state.schedule_type == "interval":
                if design_state.interval_unit == "minutes":
                    config_dict["interval_minutes"] = design_state.interval_value
                elif design_state.interval_unit == "hours":
                    config_dict["interval_hours"] = design_state.interval_value
                else:  # days
                    config_dict["interval_days"] = design_state.interval_value

            elif design_state.schedule_type == "daily":
                config_dict["hour"] = design_state.hour
                config_dict["minute"] = design_state.minute

            elif design_state.schedule_type == "weekly":
                config_dict["hour"] = design_state.hour
                config_dict["minute"] = design_state.minute
                config_dict["day_of_week"] = ",".join(design_state.days_of_week)

            elif design_state.schedule_type == "cron":
                config_dict["cron_expression"] = design_state.cron_expression

            from client_app.app.database.models import TriggerConfig
            trigger = TriggerConfig(
                name=design_state.name or "Programación",
                type="schedule",
                description=get_schedule_description(design_state),
                configuration=config_dict,
                status="CONFIGURED",
                is_active=True
            )

            async with state.db_session() as session:
                session.add(trigger)
                await session.commit()
                await session.refresh(trigger)

            # Programar el job subyacente
            await scheduler_service.start_trigger(trigger)
            
            ui.notify(f"{t('scheduler.scheduled_success')} (ID: {trigger.id})", type='positive')

            go_to_index()
            await load_data()

        except Exception as e:
            ui.notify(f"Error: {e}", type='negative')
            print(f"Error saving schedule: {e}")
            import traceback
            traceback.print_exc()
        finally:
            design_state.is_saving = False
            render_page.refresh()

    async def handle_cancel_job(job_id: str):
        """Cancela una tarea programada."""
        success = await scheduler_service.cancel_schedule(job_id)
        if success:
            ui.notify(t('scheduler.cancel_success'), type='positive')
            await load_data()
        else:
            ui.notify(t('common.delete_error'), type='negative')

    async def handle_pause_job(job_id: str, is_paused: bool):
        """Pausa o reanuda una tarea."""
        if is_paused:
            success = await scheduler_service.resume_schedule(job_id)
            msg = "reanudada" if success else "Error al reanudar"
        else:
            success = await scheduler_service.pause_schedule(job_id)
            msg = "pausada" if success else "Error al pausar"

        if success:
            ui.notify(f"Tarea {msg}", type='positive')
            await load_data()
        else:
            ui.notify(msg, type='negative')

    def format_next_run(dt: Optional[datetime]) -> str:
        """Formatea la fecha de próxima ejecución."""
        if not dt:
            return t('scheduler.not_scheduled', "Sin programar")

        now = datetime.now()
        delta = dt - now

        if delta.days < 0:
            return "Pasado"
        elif delta.days == 0:
            if delta.seconds < 3600:
                minutes = delta.seconds // 60
                return f"En {minutes} min"
            else:
                hours = delta.seconds // 3600
                return f"En {hours}h"
        elif delta.days == 1:
            return f"Mañana {dt.strftime('%H:%M')}"
        elif delta.days < 7:
            return dt.strftime("%A %H:%M")
        else:
            return dt.strftime("%d/%m %H:%M")

    # --- RENDERERS ---



    @ui.refreshable
    def render_schedule_options():
        """Renderiza las opciones de tiempo específicas del tipo seleccionado."""
        st = design_state.schedule_type
        if st == 'once':
            with ui.row().classes('w-full gap-4'):
                ui.input(t('scheduler.date'), on_change=update_ui).classes('flex-grow text-sm').bind_value(design_state, 'run_date').props('type=date dense outlined')
                ui.input(t('scheduler.time'), on_change=update_ui).classes('w-32 text-sm').bind_value(design_state, 'run_time').props('type=time dense outlined')
        elif st == 'interval':
            with ui.row().classes('w-full gap-4 items-center'):
                ui.label(t('scheduler.every')).classes('text-sm font-medium')
                ui.number(value=1, min=1, max=999, on_change=update_ui).classes('w-24 text-sm').bind_value(design_state, 'interval_value').props('dense outlined')
                ui.select({'minutes': t('scheduler.minutes'), 'hours': t('scheduler.hours'), 'days': t('scheduler.days')}, on_change=update_ui).classes('w-32 text-sm').bind_value(design_state, 'interval_unit').props('dense outlined')
        elif st == 'daily':
            with ui.row().classes('w-full gap-4 items-center'):
                ui.label(t('scheduler.all_days_at')).classes('text-sm font-medium')
                ui.number(t('scheduler.time'), min=0, max=23, on_change=update_ui).classes('w-20 text-sm').bind_value(design_state, 'hour').props('dense outlined')
                ui.label(':').classes('text-lg')
                ui.number('Min', min=0, max=59, on_change=update_ui).classes('w-20 text-sm').bind_value(design_state, 'minute').props('dense outlined')
        elif st == 'weekly':
            ui.label(t('scheduler.week_days') + ':').classes('text-xs font-medium mb-1')
            with ui.row().classes('gap-1'):
                for day_code, day_name in [('mon', 'Lun'), ('tue', 'Mar'), ('wed', 'Mié'), ('thu', 'Jue'), ('fri', 'Vie'), ('sat', 'Sáb'), ('sun', 'Dom')]:
                    is_selected = day_code in design_state.days_of_week
                    def toggle_day(d=day_code):
                        if d in design_state.days_of_week: design_state.days_of_week.remove(d)
                        else: design_state.days_of_week.append(d)
                        update_ui()
                        render_schedule_options.refresh()
                    ui.button(day_name, on_click=toggle_day).props(f'{"unelevated color=indigo" if is_selected else "outline color=grey"} dense').classes('text-[10px]')
            with ui.row().classes('w-full gap-4 items-center mt-3'):
                ui.label(t('scheduler.at')).classes('text-sm font-medium')
                ui.number(t('scheduler.time'), min=0, max=23, on_change=update_ui).classes('w-20 text-sm').bind_value(design_state, 'hour').props('dense outlined')
                ui.label(':').classes('text-lg')
                ui.number('Min', min=0, max=59, on_change=update_ui).classes('w-20 text-sm').bind_value(design_state, 'minute').props('dense outlined')
        elif st == 'cron':
            ui.input(t('scheduler.cron'), placeholder='0 9 * * *', on_change=update_ui).classes('w-full font-mono text-sm').bind_value(design_state, 'cron_expression').props('dense outlined')
            ui.label(t('scheduler.cron_format')).classes('text-[10px] text-slate-500')
            ui.link(t('scheduler.cron_help'), 'https://crontab.guru/', new_tab=True).classes('text-[10px] text-indigo-600')

    def update_ui():
        """Actualiza el estado del botón de guardado."""
        if save_btn:
            is_valid = True
            if design_state.schedule_type == 'cron' and not design_state.cron_expression:
                is_valid = False
            save_btn.enable() if is_valid else save_btn.disable()

    @ui.refreshable
    def render_page():
        with ui.column().classes('w-full p-6'):
            if page_state.current_mode == 'library':
                render_library()
            elif page_state.current_mode == 'design':
                render_design()

    def render_library():
        with ui.column().classes('w-full max-w-5xl mx-auto gap-8'):
            # Header
            with ui.row().classes('w-full justify-between items-center'):
                with ui.column():
                    with ui.row().classes('items-center gap-2'):
                        ui.label(t('scheduler.title')).classes('text-3xl font-bold text-slate-800')
                    ui.label(t('scheduler.subtitle')).classes('text-slate-500')
                ui.button(t('scheduler.new'), icon='add', on_click=start_new_design).props('unelevated color=indigo-600')

            # List jobs... (existing logic simplified for clarity but keeping functionality)
            if page_state.is_loading:
                ui.spinner(size='lg').classes('mx-auto mt-8')
                return

            if not page_state.scheduled_jobs:
                with ui.card().classes('w-full p-12 text-center bg-slate-50 border-dashed border-2'):
                    ui.icon('event_busy', size='4rem').classes('text-slate-300')
                    ui.label(t('scheduler.empty')).classes('text-slate-500 mt-4')
                return

            for job in page_state.scheduled_jobs:
                with ui.card().classes('w-full p-0 overflow-hidden shadow-sm border-l-4 border-indigo-500 mb-4'):
                    with ui.row().classes('w-full items-center p-4 bg-white'):
                        ui.icon('pause_circle' if job.is_paused else 'play_circle', color='orange' if job.is_paused else 'green', size='lg')
                        with ui.column().classes('flex-grow ml-4'):
                            ui.label(job.flow_name).classes('text-lg font-bold')
                            ui.label(f'Tipo: {job.schedule_type.value}').classes('text-xs text-slate-500')
                        
                        with ui.row().classes('gap-2'):
                            ui.button(icon='play_arrow' if job.is_paused else 'pause', 
                                      on_click=lambda j=job: handle_pause_job(j.job_id, j.is_paused)).props('flat round dense')
                            ui.button(icon='delete', on_click=lambda j=job: confirm_cancel(j)).props('flat round dense color=red')

    def confirm_cancel(job: ScheduledJob):
        with ui.dialog() as d, ui.card():
            ui.label(t('scheduler.delete_confirm', name=job.flow_name)).classes('text-lg font-bold')
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button(t('common.cancel'), on_click=d.close).props('flat')
                ui.button(t('common.delete'), on_click=lambda: (d.close(), handle_cancel_job(job.job_id))).props('unelevated color=red')
        d.open()

    def render_design():
        nonlocal save_btn
        save_btn = None
        
        with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
            page_header(
                t('scheduler.create_title'),
                t('scheduler.create_subtitle')
            )

            with ui.grid(columns=2).classes('w-full gap-4'):
                # COLUMNA 1: Configuración de Tiempo
                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label(t('scheduler.config')).classes('text-base font-bold mb-2')

                        # Nombre de la programación
                        ui.input(label=t('scheduler.name'), placeholder='Ej: Informe mensual de ventas')\
                            .classes('w-full text-sm mb-3')\
                            .props('outlined dense')\
                            .bind_value(design_state, 'name')

                        ui.separator().classes('my-2')

                        schedule_options = {
                            'once': t('scheduler.once'),
                            'interval': t('scheduler.interval'),
                            'daily': t('scheduler.daily'),
                            'weekly': t('scheduler.weekly'),
                            'cron': t('scheduler.cron')
                        }
                        ui.select(schedule_options, label=t('scheduler.type'),
                                 on_change=lambda: [update_ui(), render_schedule_options.refresh()])\
                            .classes('w-full text-sm').props('dense outlined')\
                            .bind_value(design_state, 'schedule_type')

                        ui.separator().classes('my-2')
                        render_schedule_options()

                # COLUMNA 2: Automatismo y Acciones
                with ui.column().classes('gap-4'):
                    with ui.card().classes('w-full p-5 shadow-sm border border-slate-50'):
                        ui.label('Disponibilidad para flujos').classes('text-base font-bold mb-2')
                        ui.label('Este disparador estará disponible para ser seleccionado como bloque inicial en el Diseñador de Flujos. Configura la suscripción directamente en el flujo.').classes('text-sm text-slate-500')

                    # Botones de acción
                    with ui.row().classes('w-full justify-end gap-2 mt-4 items-center'):
                        ui.button(t('common.cancel'), on_click=go_to_index).props('flat color=slate text-sm')
                        save_btn = ui.button(t('scheduler.new'), icon='schedule', on_click=handle_schedule)\
                            .props('unelevated color=indigo shadow text-sm')
                        update_ui()

    def get_schedule_description(ds: DesignState) -> str:
        st = ds.schedule_type
        if st == 'once': return f"Una vez el {ds.run_date} a las {ds.run_time}"
        elif st == 'interval': return f"Cada {ds.interval_value} {ds.interval_unit}"
        elif st == 'daily': return f"Todos los días a las {ds.hour:02d}:{ds.minute:02d}"
        elif st == 'weekly': return f"Semanal ({', '.join(ds.days_of_week)}) a las {ds.hour:02d}:{ds.minute:02d}"
        elif st == 'cron': return f"Cron: {ds.cron_expression}"
        return "Sin definir"

    # --- INITIALIZATION ---
    await load_data()

    # Manejar modo inicial antes del primer renderizado
    # Verificar si viene desde un flujo (modo contextual)
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        design_state.__init__()
        tomorrow = datetime.now() + timedelta(days=1)
        design_state.run_date = tomorrow.strftime("%Y-%m-%d")
        layout_manager.enter_design_mode(StepType.SCHEDULER, from_flow=True)
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
    elif mode == 'design':
        page_state.current_mode = 'design'
        design_state.__init__()
        # Establecer fecha por defecto a mañana si es nuevo
        tomorrow = datetime.now() + timedelta(days=1)
        design_state.run_date = tomorrow.strftime("%Y-%m-%d")
        layout_manager.enter_design_mode(StepType.SCHEDULER)
    else:
        layout_manager.exit_focus_mode()

    render_page()
