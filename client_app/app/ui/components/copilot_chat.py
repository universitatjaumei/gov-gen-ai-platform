"""
Copilot Chat - Componente de Chat Contextual para el Drawer

Proporciona una interfaz de chat que usa RAG local para enviar
contexto relevante al Copiloto segun donde este el usuario.

Features:
- Area de mensajes con scroll
- Input de texto con boton enviar
- Pills de ayuda rapida contextuales
- Spinner durante carga
- Soporte para mensajes del sistema (proactivos)
"""

from nicegui import ui
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
import re
from automatia_shared.enums import StepType


# === Copiloto Activo: Mapeo de nombres de tipo a StepType ===
# Soporta tanto nombres exactos del enum como aliases comunes
STEP_TYPE_MAP = {
    # Procesadores
    'EXTRACTION': StepType.EXTRACTION,
    'PDF_EXTRACTION': StepType.EXTRACTION,  # Alias
    'ETL_TRANSFORM': StepType.ETL_TRANSFORM,
    'ETL': StepType.ETL_TRANSFORM,  # Alias
    'CUSTOM_SCRIPT': StepType.CUSTOM_SCRIPT,
    'SCRIPT': StepType.CUSTOM_SCRIPT,  # Alias
    'RPA_EXECUTE': StepType.RPA_EXECUTE,
    'RPA': StepType.RPA_EXECUTE,  # Alias
    'GRAPHICS': StepType.GRAPHICS,
    'PDF_TOOLS': StepType.PDF_TOOLS,
    'ANONYMIZATION': StepType.ANONYMIZATION,
    'MASKING': StepType.MASKING,
    'LLM_PROCESS': StepType.LLM_PROCESS,
    'LLM': StepType.LLM_PROCESS,  # Alias
    # Disparadores
    'FOLDER_WATCHER': StepType.FOLDER_WATCHER,
    'EMAIL_WATCHER': StepType.EMAIL_WATCHER,
    'WEB_WATCHER': StepType.WEB_WATCHER,
    'SCHEDULER': StepType.SCHEDULER,
    # Entradas
    'SQL_QUERY': StepType.SQL_QUERY,
    'API_FETCH': StepType.API_FETCH,
    'API_GET': StepType.API_FETCH,  # Alias
    'FOLDER_SCAN': StepType.FOLDER_SCAN,
    'EMAIL_SCAN': StepType.EMAIL_SCAN,
    # Salidas
    'SQL_INSERT': StepType.SQL_INSERT,
    'SMTP': StepType.SMTP,
    'SMTP_SEND': StepType.SMTP,  # Alias
    'EMAIL_SEND': StepType.EMAIL_SEND,
    'ARCHIVE_FILE': StepType.ARCHIVE_FILE,
    'ARCHIVE_RESULT': StepType.ARCHIVE_FILE,  # Alias
    'REPORT_GENERATE': StepType.REPORT_GENERATE,
    'REPORT': StepType.REPORT_GENERATE,  # Alias
    'REPORTS': StepType.REPORT_GENERATE,  # Alias plural
    'INFORME': StepType.REPORT_GENERATE,  # Alias español
}


def parse_prompt_proposal(response_text: str) -> Optional[str]:
    """
    Detecta y extrae propuestas de prompt del Copiloto.

    Formato esperado:
        [PROMPT_PROPOSAL]
        Tu prompt aquí...
        [/PROMPT_PROPOSAL]

    Returns:
        El contenido del prompt propuesto o None
    """
    pattern = r'\[PROMPT_PROPOSAL\](.*?)\[/PROMPT_PROPOSAL\]'
    match = re.search(pattern, response_text, re.DOTALL)

    if match:
        return match.group(1).strip()
    return None


def parse_etl_ai_prompt(response_text: str) -> Optional[str]:
    """
    Detecta y extrae propuestas de prompt para el Modo IA de ETL.

    Formato esperado:
        [ETL_AI_PROMPT]
        Instrucciones de transformación en lenguaje natural...
        [/ETL_AI_PROMPT]

    Returns:
        El contenido del prompt para ETL IA o None
    """
    pattern = r'\[ETL_AI_PROMPT\](.*?)\[/ETL_AI_PROMPT\]'
    match = re.search(pattern, response_text, re.DOTALL)

    if match:
        return match.group(1).strip()
    return None


def parse_proposed_steps(response_text: str) -> Optional[List[Dict]]:
    """
    Detecta y parsea propuestas de pasos en la respuesta del Copiloto.

    Formatos soportados (con/sin números, negritas, viñetas):
        1. [API_FETCH] Nombre del paso - Descripción
        2. **[GRAPHICS]** Otro paso - Descripción
        - [ETL_TRANSFORM] Sin número - Descripción
        * [REPORT_GENERATE] Con viñeta - Descripción

    Returns:
        Lista de dicts [{type: StepType, name: str, description: str}] o None
    """
    # Patrón robusto que acepta:
    # - Números opcionales con . o ) : (?:\d+[\.\)]\s*)?
    # - Viñetas opcionales: (?:[-*]\s*)?
    # - Negritas opcionales alrededor del tipo: (?:\*\*)?
    # - El tipo en mayúsculas: [A-Z_]+
    # - Nombre hasta el guion o fin de línea
    # - Descripción opcional después del guion
    pattern = r'^\s*(?:(?:\d+[\.\)]|[-*])\s*)?(?:\*\*)?\[([A-Z_]+)\](?:\*\*)?\s*([^-\n]+?)(?:\s*-\s*([^\n]*))?$'

    matches = list(re.finditer(pattern, response_text, re.MULTILINE))

    if len(matches) < 2:
        return None

    steps = []
    for match in matches:
        type_str = match.group(1)
        name = match.group(2).strip() if match.group(2) else ''
        description = match.group(3).strip() if match.group(3) else ''

        step_type = STEP_TYPE_MAP.get(type_str.upper())

        if step_type:
            steps.append({
                'type': step_type,
                'name': name,
                'description': description
            })

    return steps if len(steps) >= 2 else None


def parse_domain_proposal(response_text: str, domain_tag: str) -> Optional[List[Dict]]:
    """
    Detecta y parsea propuestas genéricas para otros dominios (ETL, Graphics, Reports).
    
    Usa el mismo patrón base pero adaptado a la etiqueta específica e intenta
    extraer un JSON de configuración si existe en la descripción.
    
    Formato esperado:
        1. [ETL_OP] Nombre de operación - Descripción {"config": "json"}
        
    Args:
        response_text: Respuesta completa de la IA.
        domain_tag: Etiqueta del dominio (ej. 'ETL_OP', 'CHART_CONFIG', 'REPORT_BLOCK')
        
    Returns:
        Lista de operaciones con su configuración extraída, o None si no hay.
    """
    # Buscamos el inicio de cada operación usando un iterador
    import re
    # Patrón robusto para aceptar listas con/sin números, viñetas, negritas, etc.
    pattern = rf'^\s*(?:(?:\d+[\.\)]|[-*])\s*)?(?:\*\*)?\[({domain_tag})\](?:\*\*)?\s*([^-\n]+)(?:\s*-\s*([^\n]*))?'
    matches = list(re.finditer(pattern, response_text, re.MULTILINE))
    
    if not matches:
        return None
        
    operations = []
    for i, match in enumerate(matches):
        name = match.group(2).strip()
        desc_intro = (match.group(3) or "").strip()
            
        # Extraer todo el contenido de esta operación hasta la siguiente o fin de texto
        start_idx = match.end()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(response_text)
        
        op_content = response_text[start_idx:end_idx]
        full_description = (desc_intro + " " + op_content).strip()
        
        # Intentar extraer JSON de la descripción
        json_config = {}
        # Usamos re.DOTALL para que .* cruce líneas y buscar desde la primera llave a la última
        json_match = re.search(r'(\{.*\})', full_description, re.DOTALL)
        if json_match:
            try:
                import json
                json_str = json_match.group(1)
                json_config = json.loads(json_str)
                # Limpiamos el JSON de la descripción visual
                full_description = full_description.replace(json_str, '').strip()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("No se pudo extraer JSON de la propuesta: %s", str(e))
                pass
                
        # Combinar el payload extraído con la base de la operación para
        # que coincida con los esquemas Pydantic requeridos en la UI
        operation = {
            'type': name,
            'description': full_description
        }
        if json_config and isinstance(json_config, dict):
            operation.update(json_config)
            
        operations.append(operation)
        
    return operations if len(operations) >= 1 else None


class CopilotChat:
    """
    Componente de chat para el panel Copilot del drawer.

    Atributos:
        messages: Historial de mensajes [{role, content, timestamp}]
        is_loading: Si esta esperando respuesta del Brain
        context_service: Servicio que orquesta el contexto
        context_suggestions: Sugerencias contextuales adicionales para el modo actual
    """

    def __init__(self, context_suggestions: List[Dict] = None):
        """
        Args:
            context_suggestions: Lista de sugerencias adicionales [{'label': str, 'query': str}]
        """
        self.messages: List[Dict] = []
        self.is_loading: bool = False
        self._input_ref = None
        self._messages_container = None
        self._scroll_area = None
        self.context_suggestions = context_suggestions or []

    def render(self):
        """Renderiza el componente completo de chat."""
        from client_app.app.services.copilot_context_service import copilot_context_service
        from client_app.app.services.layout_manager import layout_manager
        from client_app.app.core.state import state

        self.t = state.i18n.t

        # Verificar si hay mensaje pendiente del layout_manager
        pending_message = layout_manager.consume_pending_message()
        if pending_message:
            # Enviar el mensaje pendiente
            ui.timer(0.1, lambda: asyncio.create_task(self._send_message(pending_message)), once=True)

        # Obtener contexto actual
        context = copilot_context_service.get_context()

        # Combinar sugerencias del contexto con las del servicio
        all_quick_actions = list(self.context_suggestions) + (context.quick_actions or [])

        # Estructura: flex column con input fijo en la parte inferior
        with ui.column().classes('w-full h-full gap-0'):
            # Area de mensajes (scroll) - ocupa el espacio disponible
            with ui.scroll_area().classes('w-full flex-1 min-h-0 px-3 py-2') as scroll:
                self._scroll_area = scroll
                self._render_messages()

            # Pills de ayuda rapida (entre mensajes e input)
            if all_quick_actions:
                with ui.row().classes('w-full px-3 py-2 gap-2 flex-wrap border-t bg-slate-50 shrink-0'):
                    for action in all_quick_actions[:4]:  # Max 4 pills
                        self._render_quick_action_pill(action)

            # Input de mensaje (fijo en la parte inferior)
            with ui.row().classes('w-full items-center gap-2 p-3 border-t bg-white shrink-0'):
                self._input_ref = ui.input(
                    placeholder=context.placeholder
                ).classes('flex-grow').props('outlined dense')

                # Manejar Enter para enviar
                self._input_ref.on('keydown.enter', self._handle_send)

                # Boton enviar
                send_btn = ui.button(
                    icon='send',
                    on_click=self._handle_send
                ).props('flat round color=primary')

    @ui.refreshable
    def _render_messages(self):
        """Renderiza el area de mensajes."""
        from client_app.app.core.state import state
        from client_app.app.services.copilot_context_service import copilot_context_service
        t = state.i18n.t

        if not self.messages:
            # Obtener el modo actual para mostrar mensaje contextualizado
            context = copilot_context_service.get_context()

            if context.mode == 'flow_edit':
                # Mensaje de bienvenida específico para el editor de flujos
                with ui.column().classes('w-full h-full items-center justify-center py-4 px-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('auto_awesome', size='sm', color='primary')
                        ui.label(t('drawer.flow_edit_welcome', 'Asistente de diseño de flujos')).classes('text-sm font-bold text-slate-700')
                    with ui.card().classes('mt-3 p-3 bg-blue-50 border border-blue-200 max-w-[95%]'):
                        ui.label(
                            t('drawer.flow_edit_hint',
                              'Describe lo que quieres automatizar en el chat y te sugeriré los pasos necesarios. '
                              'Cuando mi propuesta incluya pasos numerados con [TIPO], aparecerá un botón para añadirlos automáticamente a tu flujo.')
                        ).classes('text-xs text-blue-700')
                return
            elif context.mode == 'etl':
                with ui.column().classes('w-full h-full items-center justify-center py-4 px-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('auto_awesome', size='sm', color='teal')
                        ui.label(t('drawer.etl_edit_welcome', 'Asistente de transformaciones')).classes('text-sm font-bold text-slate-700')
                    with ui.card().classes('mt-3 p-3 bg-teal-50 border border-teal-200 max-w-[95%]'):
                        ui.label(
                            t('drawer.etl_edit_hint',
                              'Describe en lenguaje natural cómo quieres limpiar o filtrar tus datos (ej: "elimina las filas vacías y renombra la columna ID a Identificador"). '
                              'Te sugeriré las operaciones exactas listas para aplicar.')
                        ).classes('text-xs text-teal-700')
                return
            elif context.mode == 'graphics':
                with ui.column().classes('w-full h-full items-center justify-center py-4 px-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('auto_awesome', size='sm', color='indigo')
                        ui.label(t('drawer.graphics_edit_welcome', 'Asistente de visualización')).classes('text-sm font-bold text-slate-700')
                    with ui.card().classes('mt-3 p-3 bg-indigo-50 border border-indigo-200 max-w-[95%]'):
                        ui.label(
                            t('drawer.graphics_edit_hint',
                              'Describe qué quieres visualizar (ej: "muéstrame un gráfico de barras de las ventas por provincia"). '
                              'Configuraré el gráfico automáticamente listo para aplicar.')
                        ).classes('text-xs text-indigo-700')
                return
            elif context.mode == 'report':
                with ui.column().classes('w-full h-full items-center justify-center py-4 px-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('auto_awesome', size='sm', color='orange')
                        ui.label(t('drawer.report_edit_welcome', 'Asistente de informes')).classes('text-sm font-bold text-slate-700')
                    with ui.card().classes('mt-3 p-3 bg-orange-50 border border-orange-200 max-w-[95%]'):
                        ui.label(
                            t('drawer.report_edit_hint',
                              'Describe la estructura del informe que necesitas (ej: "añade un título, un texto introductorio y la tabla de resultados"). '
                              'Generaré los bloques listos para insertar en el documento.')
                        ).classes('text-xs text-orange-700')
                return

            # Estado vacio genérico
            with ui.column().classes('w-full h-full items-center justify-center py-8'):
                ui.icon('chat_bubble_outline', size='lg', color='grey-4')
                ui.label(t('drawer.copilot_empty', 'Sin mensajes recientes')).classes('text-xs text-gray-400 italic mt-2')
            return

        with ui.column().classes('w-full gap-2') as container:
            self._messages_container = container

            for msg in self.messages:
                self._render_message(msg)

            # Spinner si esta cargando
            if self.is_loading:
                with ui.row().classes('w-full justify-start'):
                    with ui.card().classes('bg-blue-50 border-l-4 border-blue-400 p-3 max-w-[85%]'):
                        with ui.row().classes('items-center gap-2'):
                            ui.spinner('dots', size='sm', color='primary')
                            ui.label('Pensando...').classes('text-sm text-blue-600 italic')

    def _render_message(self, msg: Dict):
        """Renderiza un mensaje individual."""
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        msg_type = msg.get('type')  # Para mensajes del sistema

        if role == 'user':
            # Mensaje del usuario (derecha)
            with ui.row().classes('w-full justify-end'):
                with ui.card().classes('bg-primary text-white p-2 max-w-[90%] shadow-sm'):
                    ui.label(content).classes('text-xs')

        elif role == 'assistant':
            # Mensaje del asistente (izquierda)
            with ui.row().classes('w-full justify-start'):
                with ui.card().classes('bg-slate-100 p-2 max-w-[90%] shadow-sm'):
                    # Limpiar el contenido de los tags de propuesta para el markdown
                    display_content = re.sub(
                        r'\[PROMPT_PROPOSAL\].*?\[/PROMPT_PROPOSAL\]',
                        '',
                        content,
                        flags=re.DOTALL
                    ).strip()
                    ui.markdown(display_content).classes('text-xs prose prose-xs max-w-none [&_p]:my-1 [&_ul]:my-1 [&_ol]:my-1 prose-h3:text-sm prose-h3:mt-2 prose-h3:mb-1')

                    # === Detectar propuesta de prompt LLM ===
                    prompt_proposal = parse_prompt_proposal(content)
                    if prompt_proposal:
                        self._render_prompt_proposal_card(prompt_proposal)

                    # === Copiloto Activo: Detectar propuesta de pasos ===
                    proposed_steps = parse_proposed_steps(content)
                    if proposed_steps:
                        self._render_proposal_card(proposed_steps)

                    # === Copiloto Activo Dominios Específicos ===
                    etl_ops = parse_domain_proposal(content, 'ETL_OP')
                    if etl_ops:
                        self._render_domain_proposal_card(etl_ops, 'ETL', 'app_state.on_apply_etl_proposal')

                    # === Propuesta de Modo IA para ETL ===
                    etl_ai_prompt = parse_etl_ai_prompt(content)
                    if etl_ai_prompt:
                        self._render_etl_ai_prompt_card(etl_ai_prompt)

                    graphics_ops = parse_domain_proposal(content, 'GRAPHICS_CONFIG')
                    if graphics_ops:
                        self._render_domain_proposal_card(graphics_ops, 'Gráficos', 'app_state.on_apply_graphics_proposal')

                    report_ops = parse_domain_proposal(content, 'REPORT_BLOCK')
                    if report_ops:
                        self._render_domain_proposal_card(report_ops, 'Informes', 'app_state.on_apply_report_proposal')


        elif role == 'system':
            # Mensaje del sistema (proactivo)
            color = 'orange' if msg_type == 'type_error' else 'blue'
            with ui.row().classes('w-full justify-center'):
                with ui.card().classes(f'bg-{color}-50 border border-{color}-200 p-3 max-w-[90%]'):
                    with ui.row().classes('items-start gap-2'):
                        ui.icon('info', color=f'{color}-6', size='xs')
                        with ui.column().classes('gap-1'):
                            ui.label(content).classes(f'text-xs text-{color}-700')
                            if msg.get('action_label'):
                                ui.button(
                                    msg['action_label'],
                                    on_click=lambda m=msg: self._handle_system_action(m)
                                ).props(f'flat dense size=sm color={color}')

    def _render_proposal_card(self, proposed_steps: List[Dict]):
        """Renderiza la tarjeta de propuesta de pasos detectada."""
        with ui.card().classes('w-full mt-2 p-2 bg-indigo-50 border border-indigo-200'):
            with ui.row().classes('items-center gap-1 mb-1'):
                ui.icon('auto_awesome', color='indigo', size='xs')
                ui.label(f'Propuesta: {len(proposed_steps)} pasos').classes('font-medium text-indigo-800 text-xs')

            # Preview de pasos compacto
            with ui.column().classes('gap-0.5 mb-2'):
                for i, step in enumerate(proposed_steps, 1):
                    step_type = step['type'].value if hasattr(step['type'], 'value') else str(step['type'])
                    with ui.row().classes('items-center gap-1'):
                        ui.badge(str(i), color='indigo').props('dense')
                        ui.label(f"[{step_type}]").classes('text-[10px] font-mono text-indigo-600')
                        ui.label(step['name']).classes('text-xs text-indigo-700 truncate')

            # Botón aplicar compacto
            async def apply_proposal():
                from client_app.app.core.state import state as app_state
                if app_state.on_apply_flow_proposal:
                    await app_state.on_apply_flow_proposal(proposed_steps)
                    ui.notify('Pasos añadidos al flujo', type='positive')
                else:
                    ui.notify('No hay flujo activo para añadir pasos', type='warning')

            ui.button(
                'Aplicar propuesta',
                icon='playlist_add',
                on_click=apply_proposal
            ).props('unelevated dense color=indigo size=sm').classes('w-full text-xs')

    def _render_domain_proposal_card(self, operations: List[Dict], domain_name: str, callback_path: str):
        """Renderiza una tarjeta genérica para propuestas de dominio específico (ETL, Gráficos, Informes)."""
        with ui.card().classes('w-full mt-2 p-2 bg-teal-50 border border-teal-200'):
            with ui.row().classes('items-center gap-1 mb-1'):
                ui.icon('auto_awesome', color='teal', size='xs')
                ui.label(f'Propuesta de {domain_name}: {len(operations)} paso{"s" if len(operations) > 1 else ""}').classes('font-medium text-teal-800 text-xs')

            # Preview compacto
            with ui.column().classes('gap-0.5 mb-2'):
                for i, op in enumerate(operations, 1):
                    with ui.row().classes('items-center gap-1'):
                        ui.badge(str(i), color='teal').props('dense')
                        ui.label(f"[{op['type']}]").classes('text-[10px] font-mono text-teal-600 truncate max-w-[80px]')
                        ui.label(op['description']).classes('text-xs text-teal-700 truncate flex-1')

            # Resolver callback dinámicamente: app_state.on_apply_etl_proposal
            from client_app.app.core.state import state as app_state
            callback_attr = callback_path.split('.')[-1]
            has_callback = hasattr(app_state, callback_attr) and getattr(app_state, callback_attr) is not None

            # Botón aplicar
            async def apply_proposal():
                callback = getattr(app_state, callback_attr, None)
                if callback:
                    try:
                        # Para gráficos es 1 dict, para los demás es lista
                        if domain_name == 'Gráficos':
                            # La operación ya tiene type, x_column, y_column, etc. directamente
                            # (no dentro de un campo 'config')
                            config = dict(operations[0]) if operations else {}
                            # Remover 'description' que es solo para visualización
                            config.pop('description', None)
                            await callback(config)
                        else:
                            await callback(operations)
                        ui.notify(f'Propuesta de {domain_name} aplicada', type='positive')
                    except Exception as e:
                        ui.notify(f'Error aplicando la propuesta: {str(e)}', type='negative')

            btn = ui.button(
                'Aplicar propuesta' if has_callback else 'No disponible en este contexto',
                icon='play_circle_outline' if has_callback else 'block',
                on_click=apply_proposal if has_callback else None
            ).props('unelevated dense size=sm').classes('w-full text-xs')
            
            if has_callback:
                btn.props('color=teal')
            else:
                btn.props('color=grey-4 text-color=grey-7').disable()
                with btn:
                    ui.tooltip(f'Esta propuesta de {domain_name} requiere estar en su diseñador específico.')

    def _render_prompt_proposal_card(self, prompt_text: str):
        """Renderiza la tarjeta de propuesta de prompt para LLM Processing."""
        from client_app.app.services.layout_manager import layout_manager
        from client_app.app.core.state import state

        t = state.i18n.t

        with ui.card().classes('w-full mt-2 p-2 bg-purple-50 border border-purple-200'):
            with ui.row().classes('items-center gap-1 mb-1'):
                ui.icon('psychology', color='purple', size='xs')
                ui.label(t('llm_process.draft_title', 'Borrador del Copiloto')).classes('font-medium text-purple-800 text-xs')

            # Preview del prompt (truncado)
            preview = prompt_text[:150] + '...' if len(prompt_text) > 150 else prompt_text
            with ui.card().classes('w-full bg-white p-2 mb-2 border border-purple-100'):
                ui.label(preview).classes('text-xs text-gray-700 font-mono whitespace-pre-wrap')

            # Botón aplicar
            async def apply_prompt():
                # Guardar en layout_manager para que la página lo recoja
                layout_manager.pending_prompt_draft = prompt_text
                ui.notify(t('llm_process.draft_available', 'Borrador disponible'), type='positive')

            ui.button(
                t('llm_process.draft_accepted', 'Aplicar borrador'),
                icon='edit_note',
                on_click=apply_prompt
            ).props('unelevated dense color=purple size=sm').classes('w-full text-xs')

    def _render_etl_ai_prompt_card(self, prompt_text: str):
        """Renderiza la tarjeta de propuesta de prompt para ETL Modo IA."""
        from client_app.app.core.state import state as app_state

        with ui.card().classes('w-full mt-2 p-2 bg-amber-50 border border-amber-200'):
            with ui.row().classes('items-center gap-1 mb-1'):
                ui.icon('auto_awesome', color='amber-8', size='xs')
                ui.label('Transformación con IA').classes('font-medium text-amber-800 text-xs')

            # Preview del prompt (truncado)
            preview = prompt_text[:200] + '...' if len(prompt_text) > 200 else prompt_text
            with ui.card().classes('w-full bg-white p-2 mb-2 border border-amber-100'):
                ui.label(preview).classes('text-xs text-gray-700 whitespace-pre-wrap')

            # Verificar si hay callback disponible
            has_callback = hasattr(app_state, 'on_apply_etl_ai_prompt') and app_state.on_apply_etl_ai_prompt is not None

            # Botón aplicar
            async def apply_etl_ai_prompt():
                if app_state.on_apply_etl_ai_prompt:
                    try:
                        await app_state.on_apply_etl_ai_prompt(prompt_text)
                        ui.notify('Instrucciones aplicadas al Modo IA', type='positive')
                    except Exception as e:
                        ui.notify(f'Error: {str(e)}', type='negative')
                else:
                    ui.notify('No disponible fuera del módulo ETL', type='warning')

            btn = ui.button(
                'Aplicar en Modo IA' if has_callback else 'No disponible en este contexto',
                icon='auto_awesome' if has_callback else 'block',
                on_click=apply_etl_ai_prompt if has_callback else None
            ).props('unelevated dense size=sm').classes('w-full text-xs')

            if has_callback:
                btn.props('color=amber-8')
            else:
                btn.props('color=grey-4 text-color=grey-7').disable()
                with btn:
                    ui.tooltip('Esta propuesta requiere estar en el módulo ETL.')

    def _render_quick_action_pill(self, action):
        """Renderiza una pill de accion rapida."""
        from datetime import datetime
        
        # Soportar tanto objetos con atributos como diccionarios
        label = action.get('label') if isinstance(action, dict) else getattr(action, 'label', str(action))
        query = action.get('query') if isinstance(action, dict) else getattr(action, 'query', label)
        action_type = action.get('action_type', 'llm') if isinstance(action, dict) else getattr(action, 'action_type', 'llm')
        payload = action.get('payload', None) if isinstance(action, dict) else getattr(action, 'payload', None)

        async def on_click():
            if action_type == 'deterministic' and payload:
                # 1. Inyectar simulación de pregunta del usuario
                self.messages.append({
                    'role': 'user',
                    'content': query,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 2. Inyectar respuesta del payload
                self.messages.append({
                    'role': 'assistant',
                    'content': payload,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 3. Refrescar interfaz instantáneamente
                self._render_messages.refresh()
                
                # 4. Scroll al final
                if self._scroll_area:
                    async def scroll_to_bottom():
                        import asyncio
                        await asyncio.sleep(0.1)
                        self._scroll_area.scroll_to(percent=1.0)
                    import asyncio
                    asyncio.create_task(scroll_to_bottom())
            else:
                # Flujo normal por red al LLM
                await self._send_message(query)

        with ui.button(
            label,
            on_click=on_click
        ).props('outline dense size=sm color=primary').classes('text-xs'):
            pass

    async def _handle_send(self):
        """Maneja el envio de mensaje."""
        if self._input_ref and self._input_ref.value:
            query = self._input_ref.value.strip()
            if query:
                self._input_ref.value = ''
                await self._send_message(query)

    async def _send_message(self, query: str):
        """Envia un mensaje al Copiloto."""
        from client_app.app.services.copilot_context_service import copilot_context_service
        from client_app.app.clients.brain_client import BrainAPIClient
        from client_app.app.core.state import state
        from client_app.app.database.models import ServerConnection
        from sqlmodel.ext.asyncio.session import AsyncSession
        from client_app.app.database.db import client_engine

        # Resolve base URL and license key from DB
        async with AsyncSession(client_engine) as session:
            conn = await session.get(ServerConnection, "default")
            url = conn.brain_url if (conn and conn.brain_url) else "http://localhost:8080"
            license_key = conn.license_key if (conn and conn.license_key) else "DEV_LICENSE_KEY_12345"
            
            # Handle common dev seed mismatches
            if license_key in ["demo_key_123", "dev_key"]:
                license_key = "DEV_LICENSE_KEY_12345"

        # Agregar mensaje del usuario
        self.messages.append({
            'role': 'user',
            'content': query,
            'timestamp': datetime.now().isoformat()
        })

        self.is_loading = True
        self._render_messages.refresh()

        # Llamar al Brain via API Client
        client = BrainAPIClient(base_url=url)
        
        try:
            # Obtener contexto actual
            context = copilot_context_service.get_context()

            # Preparar historial de conversacion (ultimos 10 mensajes)
            conversation_history = [
                {'role': m['role'], 'content': m['content']}
                for m in self.messages[-10:]
                if m['role'] in ('user', 'assistant')
            ]

            result = await client.ask_copilot(
                query=query,
                license_key=license_key,
                local_context=context.local_context,
                conversation_history=conversation_history[:-1],  # Excluir el mensaje actual
                atom_id=context.atom_id,
                flow_context=context.flow_context,
                mode=context.mode
            )

            # Agregar respuesta
            response_text = result.get('response', 'No se recibió respuesta.')
            self.messages.append({
                'role': 'assistant',
                'content': response_text,
                'timestamp': datetime.now().isoformat()
            })

            # Verificar si hay sugerencia de bridge
            if result.get('has_bridge_suggestion'):
                self.inject_system_message(
                    'type_error',
                    'He detectado una posible incompatibilidad de tipos. ¿Quieres que cree un Paso Puente para convertir los datos?',
                    action_label='Crear Puente',
                    action_type='create_bridge'
                )

        except Exception as e:
            # Mensaje de error
            self.messages.append({
                'role': 'assistant',
                'content': f'Error al procesar la consulta: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })

        finally:
            self.is_loading = False
            self._render_messages.refresh()

            # Scroll al final - usar método nativo de NiceGUI con delay para asegurar render
            if self._scroll_area:
                async def scroll_to_bottom():
                    await asyncio.sleep(0.1)  # Pequeño delay para que se renderice
                    self._scroll_area.scroll_to(percent=1.0)
                asyncio.create_task(scroll_to_bottom())

    def inject_system_message(
        self,
        issue_type: str,
        message: str,
        action_label: Optional[str] = None,
        action_type: Optional[str] = None
    ):
        """
        Inyecta un mensaje automatico del sistema.

        Args:
            issue_type: Tipo de problema ('type_error', 'missing_var', etc.)
            message: Texto del mensaje
            action_label: Etiqueta del boton de accion (opcional)
            action_type: Tipo de accion a ejecutar (opcional)
        """
        self.messages.append({
            'role': 'system',
            'content': message,
            'type': issue_type,
            'action_label': action_label,
            'action_type': action_type,
            'timestamp': datetime.now().isoformat()
        })
        self._render_messages.refresh()

    def _handle_system_action(self, msg: Dict):
        """Maneja acciones de mensajes del sistema."""
        action_type = msg.get('action_type')

        if action_type == 'create_bridge':
            asyncio.create_task(self._create_bridge_dialog())

    async def _create_bridge_dialog(self):
        """
        Abre un diálogo para crear un paso puente entre dos pasos del flujo.
        Analiza la compatibilidad de tipos y genera código de transformación.
        """
        from client_app.app.core.state import state as app_state

        flow = app_state.editing_flow
        if not flow or not hasattr(flow, 'steps') or len(flow.steps) < 2:
            ui.notify('Se necesitan al menos 2 pasos en el flujo para crear un puente', type='warning')
            return

        # Crear diálogo de selección de pasos
        with ui.dialog() as dialog, ui.card().classes('p-4 min-w-[400px]'):
            ui.label('Crear Paso Puente').classes('text-lg font-bold mb-2')
            ui.label('Selecciona los pasos entre los que quieres crear un puente de transformación.').classes('text-sm text-gray-600 mb-4')

            # Opciones de pasos
            step_options = {
                str(i): f"{i+1}. {getattr(s, 'name', f'Paso {i+1}')} [{getattr(s, 'type', 'unknown')}]"
                for i, s in enumerate(flow.steps)
            }

            source_select = ui.select(
                label='Paso origen (datos de salida)',
                options=step_options,
                value=str(0) if flow.steps else None
            ).classes('w-full mb-2')

            target_select = ui.select(
                label='Paso destino (datos de entrada)',
                options=step_options,
                value=str(1) if len(flow.steps) > 1 else None
            ).classes('w-full mb-4')

            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')

                async def on_create():
                    source_idx = int(source_select.value) if source_select.value else 0
                    target_idx = int(target_select.value) if target_select.value else 1

                    if source_idx >= target_idx:
                        ui.notify('El paso origen debe ser anterior al paso destino', type='warning')
                        return

                    dialog.close()
                    await self._generate_and_inject_bridge(flow, source_idx, target_idx)

                ui.button('Crear Puente', on_click=on_create, icon='add_link').props('color=primary')

        dialog.open()

    async def _generate_and_inject_bridge(self, flow, source_idx: int, target_idx: int):
        """
        Genera el código del puente y lo inyecta en el flujo.
        """
        from client_app.app.core.state import state as app_state
        from client_app.app.services.type_compatibility_service import type_compatibility_service
        from client_app.app.services.bridge_creator import BridgeService
        from client_app.app.database.models import ServerConnection
        from sqlmodel.ext.asyncio.session import AsyncSession
        from client_app.app.database.db import client_engine

        source_step = flow.steps[source_idx]
        target_step = flow.steps[target_idx]

        # Obtener esquemas de salida/entrada
        source_config = getattr(source_step, 'config', {}) or {}
        target_config = getattr(target_step, 'config', {}) or {}

        source_output = source_config.get('output_contract', {})
        target_input = target_config.get('input_contract', {})

        # Parsear JSON si es string
        if isinstance(source_output, str):
            try:
                import json
                source_output = json.loads(source_output)
            except Exception:
                source_output = {}

        if isinstance(target_input, str):
            try:
                import json
                target_input = json.loads(target_input)
            except Exception:
                target_input = {}

        # Extraer campos
        source_fields = source_output.get('properties', {})
        target_fields = target_input.get('properties', {})

        if not source_fields or not target_fields:
            ui.notify('No se pudieron obtener los esquemas de datos de los pasos seleccionados', type='warning')
            return

        # Obtener license key
        async with AsyncSession(client_engine) as session:
            conn = await session.get(ServerConnection, "default")
            license_key = conn.license_key if (conn and conn.license_key) else "DEV_LICENSE_KEY_12345"

        ui.notify('Generando puente de transformación...', type='info')

        try:
            # Identificar campos incompatibles
            bridge_code_parts = []
            inputs = []
            outputs = []

            for target_name, target_spec in target_fields.items():
                target_type = target_spec.get('type', 'string')

                # Buscar campo correspondiente en source
                matching_source = None
                for source_name, source_spec in source_fields.items():
                    # Buscar por nombre exacto o similar
                    if source_name.lower() == target_name.lower():
                        matching_source = (source_name, source_spec)
                        break

                if matching_source:
                    source_name, source_spec = matching_source
                    source_type = source_spec.get('type', 'string')

                    # Verificar compatibilidad
                    result = type_compatibility_service.validate_connection(
                        {'name': source_name, 'type': source_type},
                        {'name': target_name, 'type': target_type}
                    )

                    if not result.is_compatible and result.bridge_suggestion:
                        inputs.append(source_name)
                        outputs.append(target_name)
                        bridge_code_parts.append(
                            f"# {source_name} ({source_type}) -> {target_name} ({target_type})"
                        )

            if not inputs:
                ui.notify('Los pasos seleccionados parecen ser compatibles. No se necesita puente.', type='positive')
                return

            # Generar código del puente usando BridgeService
            bridge_service = BridgeService(flow)

            # Crear código de transformación simple
            source_step_name = getattr(source_step, 'name', f'paso_{source_idx}').lower().replace(' ', '_')
            transform_code = f'''# Puente de transformación automático
# Origen: {getattr(source_step, "name", "Paso origen")}
# Destino: {getattr(target_step, "name", "Paso destino")}

def transform(data):
    """Transforma datos del paso origen al formato esperado por el destino."""
    result = {{}}
    for key, value in data.items():
        # Conversión básica - personalizar según necesidades
        if value is not None:
            result[key] = str(value) if not isinstance(value, (int, float, bool)) else value
        else:
            result[key] = None
    return result

# Ejecutar transformación
if '{source_step_name}' in globals():
    output_data = transform(globals()['{source_step_name}'])
else:
    output_data = {{}}
'''

            # Inyectar el paso puente
            updated_flow = bridge_service.inject_bridge_task(
                at_index=target_idx,  # Insertar justo antes del paso destino
                code=transform_code,
                inputs=inputs,
                outputs=outputs
            )

            # Actualizar el flujo en el estado
            app_state.editing_flow = updated_flow

            # Notificar éxito
            ui.notify(
                f'Paso puente creado entre "{getattr(source_step, "name", "origen")}" y "{getattr(target_step, "name", "destino")}"',
                type='positive'
            )

            # Inyectar mensaje de confirmación en el chat
            self.messages.append({
                'role': 'assistant',
                'content': f'''He creado un **Paso Puente** de transformación entre los pasos seleccionados.

**Detalles:**
- Posición: Entre paso {source_idx + 1} y paso {target_idx + 1}
- Tipo: `CUSTOM_SCRIPT` (transformación)
- Campos mapeados: {", ".join(inputs)}

Puedes editar el código del puente haciendo clic en él para ajustar las conversiones según tus necesidades.''',
                'timestamp': datetime.now().isoformat()
            })
            self._render_messages.refresh()

        except Exception as e:
            import traceback
            traceback.print_exc()
            ui.notify(f'Error al crear el puente: {str(e)}', type='negative')

    def clear_history(self):
        """Limpia el historial de mensajes."""
        self.messages.clear()
        self._render_messages.refresh()


def copilot_chat() -> CopilotChat:
    """Factory function para crear y renderizar el chat."""
    chat = CopilotChat()
    chat.render()
    return chat
