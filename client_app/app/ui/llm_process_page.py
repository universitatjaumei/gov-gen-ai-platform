"""
LLM Process Page - Página de configuración del procesador LLM.

Permite crear y configurar prompts para procesar texto con IA generativa.
Casos de uso: resumir, clasificar, traducir, analizar sentimiento.

Diseño homogeneizado siguiendo el patrón estándar de procesadores:
- Wizard de 4 fases: SOURCE, INSTRUCTION, CONFIG, TEST
- Layout de 1 columna principal + drawer lateral con stepper
- DataSourceSelector para cargar datos desde archivo, catálogo o paso previo
- Nombre provisional automático, editable al guardar
- Contrato de datos dinámico generado al sellar
"""
from nicegui import ui
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.page_header import page_header
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.ui.components.data_source_selector import (
    render_data_source_selector,
    DataSourceSelection,
    DataSourceSelectorState
)
from client_app.app.services.script_library_service import script_library_service
from client_app.app.services.naming_service import naming_service
from client_app.app.database.models import ScriptLibrary
from automatia_shared.enums import StepType


# --- PLANTILLAS PREDEFINIDAS ---
PROMPT_TEMPLATES = {
    'summarize': {
        'name': 'Resumir',
        'icon': 'summarize',
        'instruction': 'Resume el siguiente texto en máximo 3 párrafos, destacando los puntos clave.',
        'output_format': 'text'
    },
    'classify': {
        'name': 'Clasificar',
        'icon': 'label',
        'instruction': 'Clasifica el siguiente texto en una de estas categorías: {{categorias}}. Responde solo con el nombre de la categoría.',
        'output_format': 'text'
    },
    'translate': {
        'name': 'Traducir',
        'icon': 'translate',
        'instruction': 'Traduce el siguiente texto al {{idioma_destino}}.',
        'output_format': 'text'
    },
    'sentiment': {
        'name': 'Sentimiento',
        'icon': 'mood',
        'instruction': 'Analiza el sentimiento del texto. Responde con: positivo, negativo o neutro.',
        'output_format': 'text'
    },
    'extract': {
        'name': 'Extraer',
        'icon': 'find_in_page',
        'instruction': 'Extrae del texto los siguientes campos en formato JSON: {{campos}}.',
        'output_format': 'json'
    }
}

# Fases del wizard
WIZARD_PHASES = ['source', 'instruction', 'config', 'test']
PHASE_LABELS = {
    'source': 'Origen de datos',
    'instruction': 'Instrucción',
    'config': 'Configuración',
    'test': 'Validación'
}


# --- STATE CLASSES ---

@dataclass
class LLMProcessPageState:
    """Estado de la página."""
    current_mode: str = 'library'  # 'library', 'design', 'execution'
    saved_prompts: List[ScriptLibrary] = field(default_factory=list)
    search_query: str = ""
    filter_status: str = 'all'


@dataclass
class LLMDesignState:
    """Estado completo del wizard de diseño LLM."""

    # Fase actual del wizard
    phase: str = 'source'  # 'source', 'instruction', 'config', 'test'

    # FASE 1: Origen de datos
    data_source: Optional[DataSourceSelection] = None
    data_source_selector_state: Optional[DataSourceSelectorState] = None
    source_preview: Optional[str] = None
    source_columns: List[str] = field(default_factory=list)

    # FASE 2: Instrucción
    instruction: str = ""
    system_prompt: str = ""
    selected_template: Optional[str] = None

    # FASE 3: Configuración
    output_format: str = "text"  # 'text' o 'json'
    json_schema: Optional[Dict] = None
    json_schema_fields: List[Dict] = field(default_factory=list)
    temperature: float = 0.3
    max_tokens: int = 1000

    # FASE 4: Prueba
    test_input: str = ""
    test_result: Optional[str] = None
    test_error: str = ""
    is_testing: bool = False
    last_test_tokens: int = 0
    last_test_time_ms: int = 0

    # Metadatos
    provisional_name: str = ""
    description: str = ""
    editing_id: Optional[int] = None

    # Estado UI
    is_saving: bool = False

    # Contratos generados
    input_contract: List[Dict] = field(default_factory=list)
    output_contract: List[Dict] = field(default_factory=list)

    def reset(self):
        """Reinicia todo el estado."""
        self.phase = 'source'
        self.data_source = None
        self.data_source_selector_state = DataSourceSelectorState()
        self.source_preview = None
        self.source_columns = []
        self.instruction = ""
        self.system_prompt = ""
        self.selected_template = None
        self.output_format = "text"
        self.json_schema = None
        self.json_schema_fields = []
        self.temperature = 0.3
        self.max_tokens = 1000
        self.test_input = ""
        self.test_result = None
        self.test_error = ""
        self.is_testing = False
        self.last_test_tokens = 0
        self.last_test_time_ms = 0
        self.provisional_name = ""
        self.description = ""
        self.editing_id = None
        self.is_saving = False
        self.input_contract = []
        self.output_contract = []

    def get_phase_index(self) -> int:
        """Retorna el índice de la fase actual para el stepper."""
        return WIZARD_PHASES.index(self.phase) if self.phase in WIZARD_PHASES else 0

    def can_proceed_to_next(self) -> bool:
        """Valida si se puede avanzar a la siguiente fase."""
        if self.phase == 'source':
            # Puede avanzar si hay datos cargados o si es texto manual directo
            return self.data_source is not None or bool(self.source_preview)
        elif self.phase == 'instruction':
            return bool(self.instruction.strip())
        elif self.phase == 'config':
            return True  # Config siempre tiene valores por defecto
        elif self.phase == 'test':
            return True  # Puede guardar sin probar (aunque se recomienda)
        return False

    def next_phase(self) -> bool:
        """Avanza a la siguiente fase si es posible."""
        idx = self.get_phase_index()
        if idx < len(WIZARD_PHASES) - 1:
            self.phase = WIZARD_PHASES[idx + 1]
            return True
        return False

    def prev_phase(self) -> bool:
        """Retrocede a la fase anterior."""
        idx = self.get_phase_index()
        if idx > 0:
            self.phase = WIZARD_PHASES[idx - 1]
            return True
        return False


# --- PAGE CONTENT ---

async def llm_process_page_content(prompt_id: Optional[int] = None, initial_mode: Optional[str] = None):
    """Contenido principal de la página LLM Process."""
    page_state = LLMProcessPageState()
    design_state = LLMDesignState()
    design_state.data_source_selector_state = DataSourceSelectorState()
    t = state.i18n.t

    # --- HELPERS ---

    async def load_saved_prompts(refresh: bool = True):
        """Carga los prompts guardados."""
        query = page_state.search_query if page_state.search_query else None
        results = await script_library_service.search_scripts(query=query, source_module='llm_process')
        if page_state.filter_status != 'all':
            results = [s for s in results if s.status == page_state.filter_status]
        page_state.saved_prompts = results
        if refresh:
            render_page.refresh()

    def go_to_library():
        """Vuelve a la biblioteca."""
        if state.flow_context and state.flow_context.get('mode') == 'contextual':
            flow_id = state.flow_context.get('flow_id')
            if flow_id:
                layout_manager.exit_design_mode_to_flow()
                state.clear_flow_context()
                state.clear_atom_editing_context()
                ui.navigate.to(f'/flows/{flow_id}')
                return

        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()
        render_page.refresh()

    def start_new_design(refresh: bool = True):
        """Inicia el diseño de un nuevo prompt."""
        page_state.current_mode = 'design'
        design_state.reset()
        # Generar nombre provisional
        design_state.provisional_name = naming_service.generate_provisional_name(
            StepType.LLM_PROCESS,
            config=None,
            index=len(page_state.saved_prompts) + 1
        )
        layout_manager.enter_design_mode(StepType.LLM_PROCESS)
        layout_manager.update_step_index(0)
        if refresh:
            render_page.refresh()

    async def edit_prompt(prompt: ScriptLibrary, refresh: bool = True):
        """Edita un prompt existente."""
        page_state.current_mode = 'design'
        design_state.reset()
        design_state.editing_id = prompt.id
        design_state.provisional_name = prompt.name
        design_state.description = prompt.description or ""
        design_state.instruction = prompt.user_prompt or ""

        # Cargar configuración desde config_json
        if prompt.config_json:
            config = prompt.config_json
            design_state.system_prompt = config.get('system_prompt', '')
            design_state.output_format = config.get('output_format', 'text')
            design_state.temperature = config.get('temperature', 0.3)
            design_state.max_tokens = config.get('max_tokens', 1000)
            design_state.json_schema = config.get('json_schema')

            # Cargar datos de fuente si existen
            data_source_config = config.get('data_source', {})
            if data_source_config:
                design_state.data_source = DataSourceSelection(
                    source_type=data_source_config.get('type', 'manual'),
                    atom_id=data_source_config.get('atom_id'),
                    atom_name=data_source_config.get('atom_name'),
                    step_index=data_source_config.get('step_index'),
                    step_name=data_source_config.get('step_name'),
                )

        # Ir a la fase de instrucción si ya hay datos
        design_state.phase = 'instruction' if design_state.instruction else 'source'
        layout_manager.enter_design_mode(StepType.LLM_PROCESS, atom_id=prompt.id)
        layout_manager.update_step_index(design_state.get_phase_index())
        if refresh:
            render_page.refresh()

    async def delete_prompt(prompt: ScriptLibrary):
        """Elimina un prompt."""
        try:
            await script_library_service.delete_script(prompt.id, force=True)
            ui.notify(t('llm_process.deleted', 'Prompt eliminado'), type='positive')
            await load_saved_prompts()
        except Exception as e:
            ui.notify(str(e), type='negative')

    def apply_template(template_key: str):
        """Aplica una plantilla predefinida."""
        template = PROMPT_TEMPLATES.get(template_key)
        if template:
            design_state.instruction = template['instruction']
            design_state.output_format = template['output_format']
            design_state.selected_template = template_key
            # Actualizar nombre provisional basado en template
            design_state.provisional_name = f"LLM: {template['name']}"
            render_page.refresh()
            ui.notify(t('llm_process.template_applied', 'Plantilla aplicada'), type='info')

    def update_stepper():
        """Actualiza el stepper en el drawer."""
        layout_manager.update_step_index(design_state.get_phase_index())

    def handle_source_selected(selection: DataSourceSelection):
        """Maneja la selección de fuente de datos."""
        design_state.data_source = selection

        # Extraer preview si hay contenido de archivo
        if selection.source_type == 'manual' and selection.file_content:
            try:
                # Preview de texto (primeros 500 caracteres)
                content = selection.file_content
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
                design_state.source_preview = content[:500]
                design_state.test_input = content[:1000]  # Usar como input de prueba
            except Exception:
                design_state.source_preview = "[Contenido binario - no se puede previsualizar]"

        render_page.refresh()

    def go_to_next_phase():
        """Avanza a la siguiente fase."""
        if not design_state.can_proceed_to_next():
            if design_state.phase == 'source':
                ui.notify(t('llm_process.select_source', 'Selecciona una fuente de datos'), type='warning')
            elif design_state.phase == 'instruction':
                ui.notify(t('llm_process.no_instruction', 'Escribe una instrucción'), type='warning')
            return

        if design_state.next_phase():
            # Actualizar nombre provisional basado en instrucción
            if design_state.phase == 'config' and design_state.instruction:
                preview = design_state.instruction[:35].strip()
                design_state.provisional_name = f"LLM: {preview}..."

            update_stepper()
            render_page.refresh()

    def go_to_prev_phase():
        """Retrocede a la fase anterior."""
        if design_state.prev_phase():
            update_stepper()
            render_page.refresh()

    # --- RENDERERS ---

    @ui.refreshable
    async def render_page():
        """Renderiza la página según el modo actual."""
        with ui.column().classes('w-full h-full p-6'):
            if page_state.current_mode == 'library':
                await render_library()
            elif page_state.current_mode == 'design':
                await render_design()

    async def toggle_favorite(resource):
        """Toggle favorito para un prompt LLM."""
        prompt_id = resource.get('id')
        if prompt_id:
            await script_library_service.toggle_favorite(prompt_id)
            await load_saved_prompts()

    async def render_library():
        """Renderiza la biblioteca de prompts."""
        if not page_state.saved_prompts:
            page_state.saved_prompts = await script_library_service.search_scripts(
                query=None, source_module='llm_process'
            )

        resources = []
        for p in page_state.saved_prompts:
            resources.append({
                'id': p.id,
                'name': p.name,
                'description': p.description or t('llm_process.no_description', 'Sin descripción'),
                'status': p.status or 'draft',
                'source_module': 'llm_process',
                'doc_path': p.doc_path,
                'is_favorite': p.is_favorite,
                'created_at': p.created_at,
                '_original': p
            })

        layout = StandardPageLayout(
            title=t('llm_process.title', 'Procesamiento LLM'),
            source_module='llm_process',
            resources=resources,
            on_create=start_new_design,
            on_edit=lambda r: edit_prompt(r['_original']),
            on_delete=lambda r: delete_prompt(r['_original']),
            on_execute=None,
            on_favorite_toggle=toggle_favorite,
            input_contract=['input_data', 'variables'],
            output_contract=['llm_output', 'tokens_used', 'execution_time_ms', 'pii_entities_masked']
        )
        layout.render()

    async def render_design():
        """Renderiza el wizard de diseño."""
        # Header con navegación
        with ui.row().classes('w-full items-center gap-4 mb-4'):
            ui.button(icon='arrow_back', on_click=go_to_library).props('flat round')
            page_header(
                title=t('llm_process.title', 'Procesamiento LLM'),
                subtitle=t('llm_process.subtitle', 'Configura cómo procesar texto con IA'),
                classes='gap-0 mb-0'
            )

        # Contenedor principal del wizard (1 columna)
        with ui.column().classes('w-full max-w-4xl mx-auto gap-6'):

            # Contenido de la fase actual
            with ui.card().classes('w-full p-6 border border-slate-200 shadow-sm'):
                if design_state.phase == 'source':
                    await render_phase_source()
                elif design_state.phase == 'instruction':
                    await render_phase_instruction()
                elif design_state.phase == 'config':
                    await render_phase_config()
                elif design_state.phase == 'test':
                    await render_phase_test()

            # Botones de navegación
            with ui.row().classes('w-full justify-between mt-4'):
                # Botón Atrás
                if design_state.get_phase_index() > 0:
                    ui.button(
                        t('common.back', 'Atrás'),
                        icon='arrow_back',
                        on_click=go_to_prev_phase
                    ).props('flat')
                else:
                    ui.space()

                # Botón Siguiente o Guardar
                if design_state.phase == 'test':
                    ui.button(
                        t('llm_process.save_and_seal', 'Guardar y Sellar'),
                        icon='check_circle',
                        on_click=show_save_dialog
                    ).props('unelevated color=primary')
                else:
                    ui.button(
                        t('common.next', 'Siguiente'),
                        icon='arrow_forward',
                        on_click=go_to_next_phase
                    ).props('unelevated color=primary')

    async def render_phase_source():
        """Fase 1: Selección de origen de datos."""

        # DataSourceSelector
        render_data_source_selector(
            consumer_type=StepType.LLM_PROCESS,
            on_source_selected=handle_source_selected,
            flow_context=state.flow_context,
            selector_state_override=design_state.data_source_selector_state
        )

        # Opción de texto manual directo
        ui.separator().classes('my-4')
        with ui.expansion(
            t('llm_process.manual_text', 'O escribe texto directamente'),
            icon='edit_note'
        ).classes('w-full'):
            ui.textarea(
                label=t('llm_process.manual_text_input', 'Texto a procesar'),
                placeholder=t('llm_process.manual_text_placeholder',
                    'Pega o escribe aquí el texto que quieres procesar con el LLM...')
            ).classes('w-full').props('outlined rows=5').bind_value(design_state, 'source_preview')

        # Preview de datos cargados
        if design_state.source_preview:
            with ui.card().classes('w-full p-3 bg-green-50 border border-green-200 mt-4'):
                with ui.row().classes('items-center gap-2 mb-2'):
                    ui.icon('check_circle', color='green')
                    ui.label(t('llm_process.data_loaded', 'Datos cargados')).classes('font-bold text-green-800')

                ui.label(design_state.source_preview[:300] + ('...' if len(design_state.source_preview) > 300 else '')).classes(
                    'text-sm text-slate-700 whitespace-pre-wrap'
                )

    async def render_phase_instruction():
        """Fase 2: Configuración del prompt."""
        ui.label(t('llm_process.instruction_title', 'Instrucción')).classes('text-xl font-bold mb-2')
        ui.label(t('llm_process.instruction_subtitle',
            'Define qué quieres que el LLM haga con los datos'
        )).classes('text-sm text-slate-500 mb-4')

        # Plantillas rápidas
        with ui.row().classes('w-full items-center gap-2 mb-4 flex-wrap'):
            ui.label(t('llm_process.templates', 'Plantillas:')).classes('text-sm text-slate-600')
            for key, template in PROMPT_TEMPLATES.items():
                is_selected = design_state.selected_template == key
                ui.button(
                    template['name'],
                    icon=template['icon'],
                    on_click=lambda k=key: apply_template(k)
                ).props(f'{"unelevated color=primary" if is_selected else "flat"} dense size=sm')

        # Indicador de borrador del copiloto
        if layout_manager.pending_prompt_draft:
            with ui.card().classes('w-full p-3 bg-purple-50 border border-purple-200 mb-4'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('auto_awesome', color='purple')
                    ui.label(t('llm_process.draft_available', 'Borrador del Copiloto disponible')).classes(
                        'font-bold text-purple-800'
                    )
                    ui.button(
                        t('common.apply', 'Aplicar'),
                        on_click=apply_copilot_draft
                    ).props('flat dense color=purple')

        # Textarea principal
        ui.textarea(
            label=t('llm_process.main_instruction', 'Instrucción principal'),
            placeholder=t('llm_process.instruction_placeholder',
                'Describe qué debe hacer el LLM con los datos. Ej: "Resume el contenido en 3 puntos clave"')
        ).classes('w-full').props('outlined rows=6').bind_value(design_state, 'instruction')

        # Ayuda de variables
        with ui.row().classes('w-full items-center gap-2 mt-2'):
            ui.icon('info', color='grey', size='xs')
            ui.label(t('llm_process.variables_help',
                'Usa {{variable}} para insertar datos del flujo'
            )).classes('text-xs text-slate-400')

        # Contexto del sistema (colapsable)
        ui.separator().classes('my-4')
        with ui.expansion(
            t('llm_process.system_prompt', 'Contexto del sistema (opcional)'),
            icon='settings'
        ).classes('w-full'):
            ui.textarea(
                placeholder=t('llm_process.system_prompt_placeholder',
                    'Instrucciones adicionales para el comportamiento del LLM. Ej: "Eres un asistente experto en análisis legal"')
            ).classes('w-full').props('outlined rows=3').bind_value(design_state, 'system_prompt')

    def apply_copilot_draft():
        """Aplica el borrador propuesto por el copiloto."""
        if layout_manager.pending_prompt_draft:
            design_state.instruction = layout_manager.pending_prompt_draft
            layout_manager.pending_prompt_draft = None
            render_page.refresh()
            ui.notify(t('llm_process.draft_accepted', 'Borrador aplicado'), type='positive')

    async def render_phase_config():
        """Fase 3: Ajustes avanzados."""
        ui.label(t('llm_process.config_title', 'Configuración')).classes('text-xl font-bold mb-2')
        ui.label(t('llm_process.config_subtitle',
            'Ajusta los parámetros del modelo de IA'
        )).classes('text-sm text-slate-500 mb-4')

        # Formato de salida
        with ui.row().classes('w-full items-center gap-4 mb-4'):
            ui.label(t('llm_process.output_format', 'Formato de salida:')).classes('text-sm font-medium')
            ui.toggle(
                {'text': 'Texto', 'json': 'JSON'},
                value=design_state.output_format
            ).props('dense').bind_value(design_state, 'output_format')

        # Schema JSON si aplica
        if design_state.output_format == 'json':
            with ui.card().classes('w-full p-4 bg-slate-50 border border-slate-200 mb-4'):
                ui.label(t('llm_process.json_schema', 'Campos esperados en JSON')).classes('text-sm font-bold mb-2')
                ui.textarea(
                    placeholder='{"campo1": "descripción", "campo2": "descripción"}',
                ).classes('w-full').props('outlined rows=3').bind_value(
                    design_state, 'json_schema',
                    forward=lambda x: str(x) if x else '',
                    backward=lambda x: eval(x) if x and x.strip() else None
                )

        ui.separator().classes('my-4')

        # Parámetros del modelo
        with ui.column().classes('w-full gap-4'):
            # Temperature
            with ui.row().classes('w-full items-center gap-4'):
                with ui.column().classes('w-32'):
                    ui.label(t('llm_process.temperature', 'Creatividad')).classes('text-sm font-medium')
                    ui.label(t('llm_process.temperature_hint', 'Menor = más preciso')).classes('text-xs text-slate-400')
                ui.slider(min=0, max=1, step=0.1).props('dense label-always').classes('flex-1').bind_value(
                    design_state, 'temperature'
                )
                ui.label().bind_text_from(design_state, 'temperature', backward=lambda x: f'{x:.1f}').classes('w-10 text-right')

            # Max tokens
            with ui.row().classes('w-full items-center gap-4'):
                with ui.column().classes('w-32'):
                    ui.label(t('llm_process.max_tokens', 'Max tokens')).classes('text-sm font-medium')
                    ui.label(t('llm_process.max_tokens_hint', 'Longitud máxima')).classes('text-xs text-slate-400')
                ui.slider(min=100, max=10000, step=100).props('dense label-always').classes('flex-1').bind_value(
                    design_state, 'max_tokens'
                )
                ui.label().bind_text_from(design_state, 'max_tokens', backward=lambda x: str(int(x))).classes('w-16 text-right')

    async def render_phase_test():
        """Fase 4: Validación y prueba."""
        ui.label(t('llm_process.test_title', 'Validación')).classes('text-xl font-bold mb-2')
        ui.label(t('llm_process.test_subtitle',
            'Prueba tu configuración antes de guardar'
        )).classes('text-sm text-slate-500 mb-4')

        # Input de prueba
        with ui.row().classes('w-full items-end gap-4'):
            with ui.column().classes('flex-1'):
                ui.textarea(
                    label=t('llm_process.test_input', 'Texto de prueba'),
                    placeholder=t('llm_process.test_input_placeholder',
                        'Pega aquí texto de ejemplo para probar la instrucción...')
                ).classes('w-full').props('outlined rows=4').bind_value(design_state, 'test_input')

            ui.button(
                t('common.test', 'Probar'),
                icon='science',
                on_click=handle_test
            ).props('unelevated color=green').bind_enabled_from(
                design_state, 'is_testing', backward=lambda x: not x
            )

        # Spinner de carga
        if design_state.is_testing:
            with ui.card().classes('w-full p-4 bg-blue-50 border border-blue-200 mt-4'):
                with ui.row().classes('items-center gap-3'):
                    ui.spinner('dots', size='md', color='primary')
                    ui.label(t('llm_process.testing', 'Procesando con LLM...')).classes('text-blue-800')

        # Resultado
        if design_state.test_result and not design_state.is_testing:
            with ui.card().classes('w-full p-4 bg-green-50 border border-green-200 mt-4'):
                with ui.row().classes('items-center gap-2 mb-2'):
                    ui.icon('check_circle', color='green')
                    ui.label(t('llm_process.result', 'Resultado')).classes('font-bold text-green-800')

                    if design_state.last_test_tokens > 0:
                        ui.chip(f'{design_state.last_test_tokens} tokens', icon='token').props('dense size=sm outline')
                    if design_state.last_test_time_ms > 0:
                        ui.chip(f'{design_state.last_test_time_ms}ms', icon='timer').props('dense size=sm outline')

                ui.label(design_state.test_result).classes('text-sm whitespace-pre-wrap')

        # Error
        if design_state.test_error and not design_state.is_testing:
            with ui.card().classes('w-full p-4 bg-red-50 border border-red-200 mt-4'):
                with ui.row().classes('items-center gap-2 mb-2'):
                    ui.icon('error', color='red')
                    ui.label(t('llm_process.error', 'Error')).classes('font-bold text-red-800')

                ui.label(design_state.test_error).classes('text-sm text-red-600')

        # Resumen de configuración
        ui.separator().classes('my-4')
        with ui.expansion(t('llm_process.config_summary', 'Resumen de configuración'), icon='summarize').classes('w-full'):
            with ui.column().classes('gap-2'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('source', color='grey', size='xs')
                    source_label = 'Manual' if not design_state.data_source else (
                        design_state.data_source.atom_name or
                        design_state.data_source.step_name or
                        design_state.data_source.file_name or 'Manual'
                    )
                    ui.label(f"Fuente: {source_label}").classes('text-sm')

                with ui.row().classes('items-center gap-2'):
                    ui.icon('edit_note', color='grey', size='xs')
                    ui.label(f"Instrucción: {design_state.instruction[:50]}...").classes('text-sm')

                with ui.row().classes('items-center gap-2'):
                    ui.icon('tune', color='grey', size='xs')
                    ui.label(f"Formato: {design_state.output_format} | Temp: {design_state.temperature} | Max: {design_state.max_tokens}").classes('text-sm')

    # --- HANDLERS ---

    async def handle_test():
        """Ejecuta una prueba del prompt."""
        if not design_state.instruction:
            ui.notify(t('llm_process.no_instruction', 'Escribe una instrucción'), type='warning')
            return

        if not design_state.test_input:
            ui.notify(t('llm_process.no_test_input', 'Proporciona texto de prueba'), type='warning')
            return

        design_state.is_testing = True
        design_state.test_result = None
        design_state.test_error = ""
        render_page.refresh()

        try:
            from client_app.app.modules.privacy.anonymizer import AnonymizationContext
            from client_app.app.clients.brain_client import BrainAPIClient
            import time

            start_time = time.time()

            # Anonimizar el texto de entrada
            anonymizer = AnonymizationContext(locale="es_ES")
            anonymized_input = anonymizer.anonymize(design_state.test_input)
            anonymized_instruction = anonymizer.anonymize(design_state.instruction)

            # Construir prompt
            full_prompt = f"{anonymized_instruction}\n\n---\n\n{anonymized_input}"

            # Llamar al LLM
            brain = BrainAPIClient()
            response = await brain.call_llm(
                prompt=full_prompt,
                system_prompt=design_state.system_prompt,
                temperature=design_state.temperature,
                max_tokens=int(design_state.max_tokens)
            )

            elapsed_ms = int((time.time() - start_time) * 1000)
            design_state.last_test_time_ms = elapsed_ms

            # Rehidratar la respuesta
            if response.get('success'):
                result = response.get('content', '')
                result = anonymizer.deanonymize(result)
                design_state.test_result = result
                design_state.last_test_tokens = response.get('tokens_used', 0)

                pii_count = len(anonymizer._entity_map) if hasattr(anonymizer, '_entity_map') else 0
                if pii_count > 0:
                    ui.notify(
                        t('llm_process.pii_masked', count=pii_count, default=f'{pii_count} datos personales protegidos'),
                        type='info'
                    )
            else:
                design_state.test_error = response.get('error', 'Error desconocido')

        except Exception as e:
            design_state.test_error = str(e)

        finally:
            design_state.is_testing = False
            render_page.refresh()

    def show_save_dialog():
        """Muestra el diálogo de guardado."""
        with ui.dialog() as dialog, ui.card().classes('p-6 w-96'):
            ui.label(t('llm_process.save_title', 'Guardar Procesamiento LLM')).classes('text-xl font-bold mb-4')

            # Campo de nombre editable
            name_input = ui.input(
                label=t('llm_process.name', 'Nombre'),
                value=design_state.provisional_name
            ).classes('w-full mb-3').props('outlined')

            # Campo de descripción
            desc_input = ui.textarea(
                label=t('llm_process.description', 'Descripción (opcional)'),
                value=design_state.description
            ).classes('w-full mb-4').props('outlined rows=2')

            # Contrato de salida preview
            with ui.expansion(t('llm_process.output_contract', 'Contrato de salida'), icon='output').classes('w-full mb-4'):
                output_fields = generate_output_contract()
                for field in output_fields:
                    with ui.row().classes('items-center gap-2'):
                        ui.chip(field['name'], icon='data_object').props('dense size=sm outline')
                        ui.label(f": {field['type']}").classes('text-xs text-slate-500')

            # Botones
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button(t('common.cancel', 'Cancelar'), on_click=dialog.close).props('flat')
                ui.button(
                    t('llm_process.save_and_seal', 'Guardar y Sellar'),
                    icon='check_circle',
                    on_click=lambda: handle_save(name_input.value, desc_input.value, dialog)
                ).props('unelevated color=primary')

        dialog.open()

    def generate_output_contract() -> List[Dict]:
        """Genera el contrato de salida basado en la configuración."""
        contract = [
            {'name': 'llm_output', 'type': 'string' if design_state.output_format == 'text' else 'object'},
            {'name': 'tokens_used', 'type': 'integer'},
            {'name': 'execution_time_ms', 'type': 'integer'},
            {'name': 'pii_entities_masked', 'type': 'integer'},
        ]

        if design_state.output_format == 'json' and design_state.json_schema:
            contract[0]['schema'] = design_state.json_schema
            contract.append({'name': 'schema_validation_passed', 'type': 'boolean'})

        return contract

    def generate_input_contract() -> List[Dict]:
        """Genera el contrato de entrada basado en la fuente."""
        contract = [
            {'name': 'input_data', 'type': 'string', 'description': 'Datos o texto de entrada'},
        ]

        if design_state.data_source:
            if design_state.data_source.source_type == 'catalog':
                contract.append({
                    'name': 'source_atom_id',
                    'type': 'integer',
                    'value': design_state.data_source.atom_id
                })
            elif design_state.data_source.source_type == 'flow_step':
                contract.append({
                    'name': 'source_step_index',
                    'type': 'integer',
                    'value': design_state.data_source.step_index
                })

        return contract

    async def handle_save(name: str, description: str, dialog):
        """Guarda el prompt."""
        if not design_state.instruction:
            ui.notify(t('llm_process.no_instruction', 'Escribe una instrucción'), type='warning')
            return

        dialog.close()
        design_state.is_saving = True

        try:
            # Generar contratos
            input_contract = generate_input_contract()
            output_contract = generate_output_contract()

            # Preparar configuración
            config = {
                # Instrucciones
                'instruction': design_state.instruction,
                'system_prompt': design_state.system_prompt,

                # Configuración del modelo
                'output_format': design_state.output_format,
                'temperature': design_state.temperature,
                'max_tokens': int(design_state.max_tokens),
                'json_schema': design_state.json_schema,

                # Origen de datos
                'data_source': {
                    'type': design_state.data_source.source_type if design_state.data_source else 'manual',
                    'atom_id': design_state.data_source.atom_id if design_state.data_source else None,
                    'atom_name': design_state.data_source.atom_name if design_state.data_source else None,
                    'step_index': design_state.data_source.step_index if design_state.data_source else None,
                    'step_name': design_state.data_source.step_name if design_state.data_source else None,
                } if design_state.data_source else None,

                # Contratos de datos
                'input_contract': input_contract,
                'output_contract': output_contract,

                # Metadatos de última prueba
                'last_test': {
                    'input_preview': design_state.test_input[:200] if design_state.test_input else None,
                    'output_preview': design_state.test_result[:200] if design_state.test_result else None,
                    'tokens_used': design_state.last_test_tokens,
                    'timestamp': datetime.utcnow().isoformat()
                } if design_state.test_result else None
            }

            if design_state.editing_id:
                # Actualizar existente
                await script_library_service.update_script(
                    script_id=design_state.editing_id,
                    name=name,
                    description=description,
                    user_prompt=design_state.instruction,
                    config_json=config
                )
            else:
                # Crear nuevo
                await script_library_service.add_script(
                    name=name,
                    description=description,
                    user_prompt=design_state.instruction,
                    code="",  # LLM no genera código Python
                    source_module='llm_process',
                    config_json=config
                )

            # Actualizar paso del flujo si estamos en contexto
            if state.flow_context and state.flow_context.get('mode') == 'contextual':
                step = state.flow_context.get('step')
                if step:
                    step.config['instruction'] = design_state.instruction
                    step.config['system_prompt'] = design_state.system_prompt
                    step.config['output_format'] = design_state.output_format
                    step.config['temperature'] = design_state.temperature
                    step.config['max_tokens'] = design_state.max_tokens
                    if hasattr(state, 'on_step_change'):
                        state.on_step_change()

            ui.notify(t('llm_process.saved', 'Procesamiento LLM guardado'), type='positive')
            go_to_library()
            await load_saved_prompts()

        except Exception as e:
            ui.notify(f"Error: {e}", type='negative')

        finally:
            design_state.is_saving = False

    # --- INICIALIZACIÓN ---

    # Verificar contexto
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        design_state.reset()
        design_state.provisional_name = naming_service.generate_provisional_name(StepType.LLM_PROCESS)
        layout_manager.enter_design_mode(StepType.LLM_PROCESS, from_flow=True)

        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
            # Cargar instrucción si existe en el paso
            if step.config.get('instruction'):
                design_state.instruction = step.config.get('instruction', '')
                design_state.system_prompt = step.config.get('system_prompt', '')
                design_state.output_format = step.config.get('output_format', 'text')
                design_state.temperature = step.config.get('temperature', 0.3)
                design_state.max_tokens = step.config.get('max_tokens', 1000)
                design_state.phase = 'instruction'

    elif prompt_id:
        prompt = await script_library_service.get_script(int(prompt_id))
        if prompt:
            await edit_prompt(prompt, refresh=False)
    elif initial_mode == 'design':
        start_new_design(refresh=False)
    else:
        layout_manager.exit_focus_mode()

    # Timer para detectar borradores del copiloto
    def check_pending_draft():
        if layout_manager.pending_prompt_draft and page_state.current_mode == 'design':
            render_page.refresh()

    ui.timer(1.0, check_pending_draft)

    await load_saved_prompts(refresh=False)

    # Si hay config_id del flujo, cargar el prompt
    if flow_config_id:
        prompt = await script_library_service.get_script(int(flow_config_id))
        if prompt:
            await edit_prompt(prompt, refresh=False)

    await render_page()
