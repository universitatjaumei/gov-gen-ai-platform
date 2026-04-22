"""
Formulario de configuración para paso REPORT_GENERATE.
"""
from nicegui import ui
from typing import Dict, Any, Optional, List
from client_app.app.core.state import state
from client_app.app.database.db import get_session
from client_app.app.database.models import ReportTemplate, FlowStep
from client_app.app.services.report_mapping_validator import validate_mapping, MappingValidationResult
from client_app.app.ui.components.variable_selector import VariableSelector
from sqlmodel import select


class ReportGenerateForm:
    """
    Formulario para configurar un paso de generación de informe.
    Permite seleccionar plantilla y mapear variables del flujo.
    """

    def __init__(
        self,
        step: FlowStep,
        available_variables: Dict[str, Any],
        on_config_change: Optional[callable] = None
    ):
        self.step = step
        self.available_variables = available_variables
        self.on_config_change = on_config_change

        # Extraer configuración actual
        self.config = step.custom_config or {}
        self.template_id = self.config.get("template_id")
        self.output_mode = self.config.get("output_mode", "html_interactive")
        self.variable_mapping = self.config.get("variable_mapping", {})

        # Estado
        self.current_template: Optional[ReportTemplate] = None
        self.mapping_container = None
        self.validation_result: Optional[MappingValidationResult] = None
        self.validation_container = None

    async def render(self):
        """Renderizar el formulario."""
        with ui.column().classes('w-full gap-4'):
            # Sección: Selección de plantilla
            ui.label('Plantilla de Informe').classes('font-bold text-lg')

            templates = await self._load_templates()
            template_options = {str(t.id): t.name for t in templates}

            template_select = ui.select(
                options=template_options,
                value=self.template_id,
                label='Seleccionar Plantilla',
                on_change=lambda e: self._on_template_change(e.value)
            ).classes('w-full')

            # Link al diseñador
            ui.button(
                'Crear Nueva Plantilla',
                icon='add',
                on_click=lambda: ui.navigate.to('/reports/designer')
            ).props('flat dense')

            ui.separator()

            # Sección: Modo de salida
            ui.label('Modo de Salida').classes('font-bold text-lg')

            ui.toggle(
                options={
                    'html_interactive': 'Interactivo (HTML)',
                    'pdf_static': 'Estático (PDF)'
                },
                value=self.output_mode,
                on_change=lambda e: self._on_output_mode_change(e.value)
            ).classes('w-full')

            with ui.expansion('Opciones de exportación', icon='settings').classes('w-full'):
                with ui.column().classes('w-full gap-3 p-2'):
                    # Tamaño de página
                    page_size = self.config.get('page_size', 'A4')
                    ui.select(
                        label='Tamaño de página',
                        options=['A4', 'Letter', 'A3'],
                        value=page_size,
                        on_change=lambda e: self._update_config('page_size', e.value)
                    ).classes('w-full')

                    # Orientación
                    orientation = self.config.get('orientation', 'portrait')
                    ui.select(
                        label='Orientación',
                        options={
                            'portrait': 'Vertical (Portrait)',
                            'landscape': 'Horizontal (Landscape)'
                        },
                        value=orientation,
                        on_change=lambda e: self._update_config('orientation', e.value)
                    ).classes('w-full')

                    # DPI (solo informativo, Playwright usa resolución del viewport)
                    ui.label('La resolución se ajusta automáticamente según el tamaño de página.').classes('text-xs text-gray-500')

            ui.separator()

            # Sección: Opciones Avanzadas
            with ui.expansion('Opciones avanzadas', icon='tune').classes('w-full'):
                with ui.column().classes('w-full gap-3 p-2'):
                    # Nombre del archivo de salida
                    ui.label('Nombre del archivo de salida').classes('font-bold text-sm')
                    output_filename = self.config.get('output_filename', 'informe_{{date}}.pdf')
                    ui.input(
                        value=output_filename,
                        placeholder='informe_{{date}}.pdf',
                        on_change=lambda e: self._update_config('output_filename', e.value)
                    ).classes('w-full').props('outlined dense')
                    ui.label('Usa {{date}} para fecha, {{execution_id}} para ID de ejecucion').classes('text-xs text-gray-500')

                    ui.separator().classes('my-2')

                    # Analisis con IA
                    run_analysis = self.config.get('run_analysis', False)
                    analysis_chk = ui.checkbox(
                        'Incluir analisis con IA',
                        value=run_analysis,
                        on_change=lambda e: self._update_config('run_analysis', e.value)
                    )

                    with ui.column().classes('w-full pl-6').bind_visibility_from(analysis_chk, 'value'):
                        ui.label('Instrucciones para el análisis').classes('text-sm')
                        ui.textarea(
                            value=self.config.get('analysis_instructions', ''),
                            placeholder='Describe qué aspectos debe analizar la IA...',
                            on_change=lambda e: self._update_config('analysis_instructions', e.value)
                        ).classes('w-full').props('outlined dense')

            ui.separator()

            # Sección: Mapeo de variables
            ui.label('Mapeo de Variables').classes('font-bold text-lg')
            ui.label('Conecta los datos del flujo con los campos del informe').classes('text-sm text-gray-500')

            self.mapping_container = ui.column().classes('w-full gap-2')

            if self.template_id:
                await self._render_mapping_fields()
            else:
                with self.mapping_container:
                    ui.label('Selecciona una plantilla primero').classes('text-gray-400 italic')

            # Validación
            ui.separator()
            self.validation_container = ui.column().classes('w-full')
            await self._render_validation()

    async def _load_templates(self) -> List[ReportTemplate]:
        """Cargar plantillas disponibles."""
        async with get_session() as session:
            result = session.exec(
                select(ReportTemplate).where(ReportTemplate.is_active == True)
            )
            return result.all()

    async def _on_template_change(self, template_id: str):
        """Manejar cambio de plantilla."""
        self.template_id = template_id
        self.config["template_id"] = template_id

        # Cargar plantilla
        async with get_session() as session:
             # Use await if session.exec uses async engine, otherwise sync
             # The provided code implies async session context manager but sync exec?
             # Standard sqlmodel with async engine requires await session.exec(...)
             # However in previous code snippets I used result = session.exec(...) inside async with.
             # If `get_session` returns AsyncSession, then `exec` is awaitable usually or returns result directly depending on library version.
             # I'll stick to `request.app.state.engine` usage or assuming synchronous style if the context manager handles it?
             # Actually `get_session` is `contextlib.asynccontextmanager`.
             result = await session.exec(
                select(ReportTemplate).where(ReportTemplate.id == template_id)
            )
             self.current_template = result.first()

        # Resetear mapeo
        self.variable_mapping = {}
        self.config["variable_mapping"] = self.variable_mapping

        # Re-renderizar campos de mapeo
        await self._render_mapping_fields()
        await self._render_validation()

        self._notify_change()

    def _on_output_mode_change(self, mode: str):
        """Manejar cambio de modo de salida."""
        self.output_mode = mode
        self.config["output_mode"] = mode
        self._notify_change()

    def _update_config(self, key: str, value: Any):
        """Actualizar configuración genérica."""
        self.config[key] = value
        self._notify_change()

    async def _render_mapping_fields(self):
        """Renderizar campos de mapeo de variables."""
        if not self.mapping_container:
            return

        self.mapping_container.clear()

        if not self.current_template or not self.current_template.input_schema:
            with self.mapping_container:
                ui.label('La plantilla no tiene esquema de datos definido').classes('text-amber-600')
            return

        schema = self.current_template.input_schema
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        with self.mapping_container:
            for field_name, field_spec in properties.items():
                is_required = field_name in required_fields
                field_type = field_spec.get("type", "string")

                with ui.row().classes('w-full items-center gap-2'):
                    # Indicador de requerido
                    if is_required:
                        ui.icon('star', size='xs').classes('text-red-500')
                    else:
                        ui.icon('star_border', size='xs').classes('text-gray-300')

                    # Nombre del campo
                    ui.label(field_name).classes('font-medium w-32')

                    # Tipo esperado
                    ui.chip(field_type, icon=self._get_type_icon(field_type)).props('dense')

                    # Selector de variable
                    current_value = self.variable_mapping.get(field_name, "")

                    var_selector = VariableSelector(
                        available_variables=self.available_variables,
                        current_value=current_value,
                        on_select=lambda v, fn=field_name: self._on_mapping_change(fn, v)
                    )
                    var_selector.render()

    def _get_type_icon(self, type_name: str) -> str:
        """Obtener icono para tipo de dato."""
        icons = {
            "string": "text_fields",
            "number": "pin",
            "integer": "123",
            "boolean": "toggle_on",
            "array": "list",
            "object": "data_object"
        }
        return icons.get(type_name, "help")

    def _on_mapping_change(self, field_name: str, variable_expr: str):
        """Manejar cambio en mapeo de variable."""
        self.variable_mapping[field_name] = variable_expr
        self.config["variable_mapping"] = self.variable_mapping
        self._notify_change()

        # Re-validar
        import asyncio
        # We can't await easily here if called from sync callback, so create task or run sync if possible
        # Since _render_validation is async, we create task
        # But check if running loop exists
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._render_validation())
        except RuntimeError:
            pass

    async def _render_validation(self):
        """Renderizar estado de validación."""
        if not self.validation_container:
            return

        self.validation_container.clear()

        if not self.current_template or not self.current_template.input_schema:
            return

        # Validar mapeo
        self.validation_result = validate_mapping(
            self.variable_mapping,
            self.current_template.input_schema,
            self.available_variables
        )

        with self.validation_container:
            if self.validation_result.is_valid:
                with ui.row().classes('items-center gap-2 text-green-600'):
                    ui.icon('check_circle')
                    ui.label('Configuración válida')
            else:
                with ui.column().classes('gap-1'):
                    if self.validation_result.missing_fields:
                        with ui.row().classes('items-center gap-2 text-red-600'):
                            ui.icon('error')
                            ui.label(f"Campos requeridos sin mapear: {', '.join(self.validation_result.missing_fields)}")

                    for mismatch in self.validation_result.type_mismatches:
                        with ui.row().classes('items-center gap-2 text-amber-600'):
                            ui.icon('warning')
                            ui.label(f"Campo '{mismatch['field']}': esperado {mismatch['expected']}, recibido {mismatch['actual']}")

            # Advertencias
            for warning in self.validation_result.warnings:
                with ui.row().classes('items-center gap-2 text-gray-500'):
                    ui.icon('info', size='xs')
                    ui.label(warning).classes('text-sm')

    def _notify_change(self):
        """Notificar cambio de configuración."""
        self.step.custom_config = self.config
        if self.on_config_change:
            self.on_config_change(self.config)

    def is_valid(self) -> bool:
        """Verificar si la configuración es válida."""
        return (
            self.validation_result is not None and
            self.validation_result.is_valid and
            self.template_id is not None
        )


async def render_report_generate_form(step: FlowStep, available_variables: Dict[str, Any], on_config_change: Optional[callable] = None):
    """
    Wrapper function to render the form from StepConfigurator.
    """
    form = ReportGenerateForm(step, available_variables, on_config_change)
    await form.render()
