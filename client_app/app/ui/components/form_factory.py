from dataclasses import dataclass, field
from typing import List, Optional, Literal, Any, Dict
from nicegui import ui
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from automatia_shared.enums import StepType
from client_app.app.services.data_flow_analyzer import data_flow_analyzer
from client_app.app.database.db import client_engine
from client_app.app.database.models import DatabaseCredentialConfig
from client_app.app.services.sql_connector_service import sql_connector_service

@dataclass
class VariableInfo:
    """Información básica de una variable disponible en el flujo."""
    name: str
    type: str
    source_step: str
    reference: str  # e.g., '{{steps.step_1.output}}'

@dataclass
class FormContext:
    """Contexto para el renderizado de formularios de diseño."""
    mode: Literal['standalone', 'flow'] = 'standalone'
    flow_id: Optional[int] = None
    step_index: Optional[int] = None
    available_variables: List[VariableInfo] = field(default_factory=list)

class AtomColorScheme:
    """Esquema de colores para tipos de átomos."""
    
    COLORS = {
        StepType.EXTRACTION: {
            'primary': 'bg-blue-500',
            'light': 'bg-blue-100',
            'border': 'border-blue-500',
            'text': 'text-blue-700',
            'icon': '📄'
        },
        StepType.ETL: {
            'primary': 'bg-green-500',
            'light': 'bg-green-100',
            'border': 'border-green-500',
            'text': 'text-green-700',
            'icon': '🔄'
        },
        StepType.RPA_EXECUTE: {
            'primary': 'bg-purple-500',
            'light': 'bg-purple-100',
            'border': 'border-purple-500',
            'text': 'text-purple-700',
            'icon': '🤖'
        },
        StepType.CUSTOM_SCRIPT: {
            'primary': 'bg-indigo-500',
            'light': 'bg-indigo-100',
            'border': 'border-indigo-500',
            'text': 'text-indigo-700',
            'icon': '💻'
        },
        StepType.REPORT_GENERATE: {
            'primary': 'bg-pink-500',
            'light': 'bg-pink-100',
            'border': 'border-pink-500',
            'text': 'text-pink-700',
            'icon': '📊'
        },
        StepType.API_FETCH: {
            'primary': 'bg-cyan-600',
            'light': 'bg-cyan-100',
            'border': 'border-cyan-600',
            'text': 'text-cyan-700',
            'icon': '🔗'
        },
        StepType.EMAIL: {
            'primary': 'bg-amber-600',
            'light': 'bg-amber-100',
            'border': 'border-amber-600',
            'text': 'text-amber-700',
            'icon': '📧'
        },
        StepType.SQL_QUERY: {
            'primary': 'bg-emerald-600',
            'light': 'bg-emerald-100',
            'border': 'border-emerald-600',
            'text': 'text-emerald-700',
            'icon': '🗄️'
        },
        StepType.WEBHOOK: {
            'primary': 'bg-violet-600',
            'light': 'bg-violet-100',
            'border': 'border-violet-600',
            'text': 'text-violet-700',
            'icon': '🌐'
        },
        StepType.CONNECTION: {
            'primary': 'bg-yellow-600',
            'light': 'bg-yellow-100',
            'border': 'border-yellow-600',
            'text': 'text-yellow-700',
            'icon': '📁'
        }
    }
    
    @classmethod
    def get_colors(cls, step_type: StepType) -> dict:
        """Obtiene el esquema de colores para un tipo de acción."""
        return cls.COLORS.get(step_type, cls.COLORS[StepType.CUSTOM_SCRIPT])

class FormFactory:
    """Factoría de formularios para diseño de átomos."""
    
    @staticmethod
    def render_form(step: Any, context: FormContext):
        """Renderizador genérico que deriva al formulario específico.

        NOTA: TaskSpec usa 'type', no 'step_type'. Soportamos ambos para compatibilidad.
        """
        # Compatibilidad: TaskSpec usa 'type', otros modelos pueden usar 'step_type'
        step_type = getattr(step, 'type', None) or getattr(step, 'step_type', None)

        if step_type == StepType.EXTRACTION:
            FormFactory.render_extraction_form(step, context)
        elif step_type == StepType.ETL:
            FormFactory.render_etl_form(step, context)
        elif step_type == StepType.RPA_EXECUTE:
            FormFactory.render_rpa_form(step, context)
        elif step_type == StepType.CUSTOM_SCRIPT:
            FormFactory.render_script_form(step, context)
        elif step_type == StepType.API_FETCH:
            FormFactory.render_api_form(step, context)
        elif step_type == StepType.EMAIL:
            FormFactory.render_email_form(step, context)
        elif step_type == StepType.SQL_QUERY:
            FormFactory.render_sql_form(step, context)
        # ... otros tipos se implementarán en Prompts futuros
        else:
            FormFactory.render_generic_form(step, step_type, context)

    @staticmethod
    def render_generic_form(step: Any, step_type: StepType, context: FormContext):
        """Formulario genérico para tipos no implementados específicamente."""
        t = state.i18n.t
        colors = AtomColorScheme.get_colors(step_type) if step_type else AtomColorScheme.get_colors(StepType.CUSTOM_SCRIPT)
        label_suffix = step_type.value if hasattr(step_type, 'value') else str(step_type) if step_type else t('atoms.title_singular')
        with ui.card().classes(f'{colors["light"]} {colors["border"]} border-l-4 w-full p-4 mb-4 shadow-sm'):
            ui.label(f"{colors['icon']} Configuración de {label_suffix}").classes(f'{colors["text"]} font-bold mb-4')

            with ui.column().classes('w-full gap-4'):
                # Nombre del paso
                ui.input(t('atoms.field_name')).classes('w-full').bind_value(step, 'name').props('outlined dense')
                ui.separator()
                ui.label('Configuración específica pendiente de implementación.').classes('text-xs italic')

                # Variable de salida
                FormFactory._render_output_var_field(step, colors)

    @staticmethod
    def render_script_form(step: Any, context: FormContext):
        """Formulario para Custom Script."""
        t = state.i18n.t
        colors = AtomColorScheme.get_colors(StepType.CUSTOM_SCRIPT)
        with ui.card().classes(f'{colors["light"]} {colors["border"]} border-l-4 w-full p-4 mb-4 shadow-sm'):
            ui.label(f"{colors['icon']} Script Personalizado").classes(f'{colors["text"]} font-bold mb-4')
            with ui.column().classes('w-full gap-4'):
                ui.input(t('atoms.field_name')).classes('w-full').bind_value(step, 'name').props('outlined dense')
                ui.separator()
                ui.label('Selecciona un script existente o crea uno nuevo.').classes('text-xs italic')
                FormFactory._render_output_var_field(step, colors)

    @staticmethod
    def render_api_form(step: Any, context: FormContext):
        """Formulario para API Fetch."""
        t = state.i18n.t
        colors = AtomColorScheme.get_colors(StepType.API_FETCH)
        with ui.card().classes(f'{colors["light"]} {colors["border"]} border-l-4 w-full p-4 mb-4 shadow-sm'):
            ui.label(f"{colors['icon']} Llamada a API").classes(f'{colors["text"]} font-bold mb-4')
            with ui.column().classes('w-full gap-4'):
                ui.input(t('atoms.field_name')).classes('w-full').bind_value(step, 'name').props('outlined dense')
                ui.separator()
                ui.input('URL de la API').classes('w-full').props('outlined dense').on_value_change(lambda e: step.config.update({'url': e.value}))
                FormFactory._render_output_var_field(step, colors)

    @staticmethod
    def render_email_form(step: Any, context: FormContext):
        """Formulario para Email."""
        t = state.i18n.t
        colors = AtomColorScheme.get_colors(StepType.EMAIL)
        with ui.card().classes(f'{colors["light"]} {colors["border"]} border-l-4 w-full p-4 mb-4 shadow-sm'):
            ui.label(f"{colors['icon']} Envío de Email").classes(f'{colors["text"]} font-bold mb-4')
            with ui.column().classes('w-full gap-4'):
                ui.input(t('atoms.field_name')).classes('w-full').bind_value(step, 'name').props('outlined dense')
                ui.separator()
                ui.label('Configuración de email pendiente.').classes('text-xs italic')
                FormFactory._render_output_var_field(step, colors)

    @staticmethod
    def render_sql_form(step: Any, context: FormContext):
        """Formulario para SQL Query con selector de conexión y test de consulta."""
        colors = AtomColorScheme.get_colors(StepType.SQL_QUERY)
        
        async def load_connections():
            async with AsyncSession(client_engine) as session:
                result = await session.exec(select(DatabaseCredentialConfig))
                conns = result.all()
                if not conns:
                    warning_container.set_visibility(True)
                    form_container.set_visibility(False)
                else:
                    options = {c.id: f"{c.name} ({c.db_type.upper()})" for c in conns}
                    conn_select.options = options
                    warning_container.set_visibility(False)
                    form_container.set_visibility(True)

        async def run_sql_test():
            if not conn_select.value:
                ui.notify("Selecciona una conexión", type='warning')
                return
            if not query_input.value:
                ui.notify("Escribe una consulta", type='warning')
                return
            
            test_btn.props('loading')
            try:
                # Ejecutar query
                df = await sql_connector_service.execute_query(
                    credential_id=conn_select.value,
                    query=query_input.value,
                    limit=5 # Solo preview
                )
                
                if df.empty:
                    ui.notify("Consulta exitosa pero no devolvió resultados", type='info')
                    result_preview.content = "*Sin resultados*"
                else:
                    ui.notify("Consulta exitosa", type='positive')
                    # Guardar esquema para el SchemaMapper
                    step.config['last_test_output'] = df.head(10).to_dict(orient='records')
                    
                    # Mostrar preview simple
                    result_preview.content = f"**Columnas detectadas:** {', '.join(df.columns)}\n\n"
                    result_preview.content += df.head(5).to_markdown()

            except Exception as e:
                ui.notify(f"Error: {e}", type='negative')
                result_preview.content = f"**Error:** {e}"
            finally:
                test_btn.props(remove='loading')

        with ui.card().classes(f'{colors["light"]} {colors["border"]} border-l-4 w-full p-4 mb-4 shadow-sm'):
            ui.label(f"{colors['icon']} Configuración SQL").classes(f'{colors["text"]} font-bold mb-4 text-lg')
            
            # Warning if no connections
            with ui.column().classes('w-full items-center p-6 bg-amber-50 rounded border border-amber-200 hidden') as warning_container:
                ui.icon('warning', color='amber', size='lg')
                ui.label('No hay bases de datos configuradas').classes('font-bold text-amber-900')
                ui.label('Debes configurar al menos una conexión en la sección de Configuración para usar esta acción.').classes('text-sm text-center text-amber-700 mb-4')
                ui.button('CONFIGURAR BASES DE DATOS', icon='settings', on_click=lambda: ui.navigate.to('/config?tab=Bases%20de%20Datos')).props('unelevated color=amber')

            with ui.column().classes('w-full gap-4') as form_container:
                ui.input(state.i18n.t('atoms.field_name')).classes('w-full').bind_value(step, 'name').props('outlined dense')
                ui.separator()
                
                conn_select = ui.select({}, label='Conexión a Base de Datos').classes('w-full').props('outlined dense')
                conn_select.bind_value(step.config, 'credential_id')
                
                query_input = ui.textarea('Consulta SQL', placeholder='SELECT * FROM tabla WHERE ...').classes('w-full font-mono').props('outlined autogrow')
                query_input.bind_value(step.config, 'query')
                
                with ui.row().classes('w-full justify-between items-center'):
                    test_btn = ui.button('PROBAR CONSULTA', icon='science', on_click=run_sql_test).props('unelevated color=primary dense')
                    ui.label('Solo SELECT soportado en diseño').classes('text-[10px] text-gray-400 italic')

                ui.separator()
                ui.label('Vista Previa de Resultados').classes('text-xs font-bold text-gray-500 uppercase')
                result_preview = ui.markdown(step.config.get('last_test_output', {}).get('sample', 'Sin datos de prueba')).classes('text-xs bg-white p-2 border rounded overflow-auto max-h-40 w-full')

                FormFactory._render_output_var_field(step, colors)

            ui.timer(0.1, load_connections, once=True)

    @staticmethod
    def render_extraction_form(step: Any, context: FormContext):
        """Formulario de extracción con identidad visual y bindings."""
        t = state.i18n.t
        colors = AtomColorScheme.get_colors(StepType.EXTRACTION)
        
        with ui.card().classes(f'{colors["light"]} {colors["border"]} border-l-4 w-full p-4 mb-4 shadow-sm'):
            # Header de la Acción
            with ui.row().classes('items-center mb-4'):
                ui.label(colors['icon']).classes('text-2xl')
                ui.label('Diseño de Extracción').classes(f'{colors["text"]} font-bold text-lg')
            
            # Configuración Básica
            with ui.column().classes('w-full gap-4'):
                # Nombre del paso (Binding)
                ui.input(t('atoms.field_name')).classes('w-full').bind_value(step, 'name').props('outlined dense')
                
                ui.separator()
                
                # Campos específicos (Mock para prototipo Prompt 2)
                ui.select(
                    label='Tipo de Documento',
                    options=['Factura', 'DNI', 'Contrato', 'Nómina'],
                    value=step.config.get('doc_type', 'Factura')
                ).classes('w-full').props('outlined dense').on_value_change(lambda e: step.config.update({'doc_type': e.value}))
                
                ui.switch('Usar OCR avanzado', value=step.config.get('ocr_enabled', True)).bind_value(step.config, 'ocr_enabled')
                
                ui.separator()
                
                # Nombre de Variable de Salida (IA Suggested)
                FormFactory._render_output_var_field(step, colors)

    @staticmethod
    def _render_output_var_field(step: Any, colors: dict):
        """Renderiza el campo de variable de salida con botón de IA."""
        
        # Asegurar que outputs tenga al menos un elemento
        if not step.outputs:
            step.outputs = [""]
            
        def update_output(val):
            step.outputs[0] = val

        async def get_suggestion():
            btn.set_visibility(False)
            spinner.set_visibility(True)
            try:
                # El DataFlowAnalyzer ahora usa el cerebro
                suggested = await data_flow_analyzer.suggest_semantic_name(step.type, step.config)
                input_field.set_value(suggested)
                step.outputs[0] = suggested
            finally:
                btn.set_visibility(True)
                spinner.set_visibility(False)

        with ui.column().classes('w-full gap-1'):
            ui.label('Variable de Salida').classes('text-xs font-medium text-gray-500')
            with ui.row().classes('w-full items-center no-wrap'):
                input_field = ui.input(
                    placeholder='ej: factura_extraida',
                    value=step.outputs[0],
                    on_change=lambda e: update_output(e.value)
                ).classes('flex-grow').props('outlined dense')
                
                with ui.element('div').classes('ml-2'):
                    btn = ui.button(icon='auto_awesome', on_click=get_suggestion) \
                        .props('flat round dense color=primary')
                    btn.tooltip('Sugerir nombre semÃ¡ntico con IA')
                    
                    spinner = ui.spinner(size='sm').classes('hidden')

    @staticmethod
    def render_etl_form(step: Any, context: FormContext):
        """Formulario de ETL (Esqueleto para Prompt 4)."""
        colors = AtomColorScheme.get_colors(StepType.ETL)
        with ui.card().classes(f'{colors["light"]} {colors["border"]} border-l-4 w-full p-4 mb-4 shadow-sm'):
            ui.label(f"{colors['icon']} Transformación ETL").classes(f'{colors["text"]} font-bold mb-4')
            ui.label('Módulo de transformación pendiente de implementación.').classes('text-xs italic mb-4')
            
            # Nombre de Variable de Salida (IA Suggested)
            FormFactory._render_output_var_field(step, colors)

    @staticmethod
    def render_rpa_form(step: Any, context: FormContext):
        """Formulario de RPA (Esqueleto para Prompt 4)."""
        colors = AtomColorScheme.get_colors(StepType.RPA_EXECUTE)
        with ui.card().classes(f'{colors["light"]} {colors["border"]} border-l-4 w-full p-4 mb-4 shadow-sm'):
            ui.label(f"{colors['icon']} Ejecución RPA").classes(f'{colors["text"]} font-bold mb-4')
            ui.label('Módulo de navegación pendiente de implementación.').classes('text-xs italic mb-4')
            
            # Nombre de Variable de Salida (IA Suggested)
            FormFactory._render_output_var_field(step, colors)
