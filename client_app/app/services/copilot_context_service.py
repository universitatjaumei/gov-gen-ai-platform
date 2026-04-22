"""
Copilot Context Service - Orquestador de Contexto Dual

Detecta el modo actual del usuario (flujo, atomo, wizard, documentacion)
y recopila el contexto apropiado para enviar al Copiloto.

Features:
- Deteccion automatica de modo basada en layout_manager y app_state
- Generacion de contexto RAG segun el modo
- Pills de ayuda rapida contextuales
- Soporte para inyeccion de mensajes proactivos
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class QuickAction:
    """Accion rapida (pill) para el chat."""
    label: str
    query: str
    icon: str = "help_outline"
    action_type: str = "llm"  # 'llm' o 'deterministic'
    payload: Optional[str] = None  # Contenido a inyectar directamente si es determinista


@dataclass
class CopilotContext:
    """Contexto recopilado para el Copiloto."""
    mode: Literal['flow', 'flow_edit', 'atom', 'wizard', 'documentation', 'web_watcher', 'gallery', 'idle', 'etl', 'graphics', 'report']
    local_context: str  # Contexto RAG formateado
    flow_context: Optional[Dict[str, Any]] = None
    atom_id: Optional[str] = None
    atom_name: Optional[str] = None
    quick_actions: List[QuickAction] = field(default_factory=list)
    placeholder: str = "Escribe tu pregunta..."
    data_context: Optional[Dict[str, Any]] = None  # Contexto de datos: columnas, tipos, ejemplos


class CopilotContextService:
    """
    Orquestador de contexto para el Copiloto.

    Detecta donde esta el usuario y recopila informacion relevante
    para alimentar las consultas al Brain.
    """

    def _get_quick_actions(self, mode: str) -> List[QuickAction]:
        """Obtiene las quick actions traducidas para un modo."""
        from client_app.app.core.state import state
        t = state.i18n.t

        standard_atom_actions = [
            QuickAction("¿Cómo configuro?", "¿Cómo debo configurar esta acción?", "settings"),
            QuickAction("Ver ejemplo", "Muéstrame un ejemplo de uso de esta acción", "code"),
        ]

        actions_map = {
            'flow_edit': [
                QuickAction(t('drawer.copilot_flow_actions'), t('drawer.copilot_flow_actions_query'), "category"),
                QuickAction(t('drawer.copilot_flow_example'), t('drawer.copilot_flow_example_query'), "lightbulb"),
            ],
            'flow': [
                QuickAction("¿Son compatibles?", "¿Son compatibles los tipos de datos entre estos pasos?", "compare_arrows"),
                QuickAction("¿Falta variable?", "¿Hay alguna variable que falte definir en este flujo?", "help"),
                QuickAction("Optimizar flujo", "¿Cómo puedo optimizar este flujo?", "speed"),
            ],
            'atom': standard_atom_actions,
            'llm_process': standard_atom_actions,
            'extraction': standard_atom_actions,
            'connection': standard_atom_actions,
            'documentation': standard_atom_actions,
            'idle': [
                QuickAction("¿Qué puedo hacer?", "¿Qué tipos de automatizaciones puedo crear?", "explore"),
                QuickAction("Primeros pasos", "¿Cuáles son los primeros pasos para crear un flujo?", "flag"),
            ],
            'gallery': [
                QuickAction(t('drawer.copilot_flow_actions'), t('drawer.copilot_flow_actions_query'), "category"),
                QuickAction(t('drawer.copilot_flow_example'), t('drawer.copilot_flow_example_query'), "lightbulb"),
            ],
            'web_watcher': standard_atom_actions,
        }
        return actions_map.get(mode, [])

    def _get_placeholder(self, mode: str) -> str:
        """Obtiene el placeholder traducido para un modo."""
        from client_app.app.core.state import state
        t = state.i18n.t

        placeholders = {
            'flow_edit': t('drawer.copilot_placeholder_flow_edit'),
            'flow': t('drawer.copilot_placeholder_flow'),
            'atom': t('drawer.copilot_placeholder_atom'),
            'wizard': t('drawer.copilot_placeholder_atom'),
            'documentation': t('drawer.copilot_placeholder_atom'),
            'web_watcher': "¿En qué puedo ayudarte con el monitor web?",
            'gallery': "¿Qué tipo de acción necesitas crear?",
            'idle': t('drawer.copilot_placeholder_default'),
        }
        return placeholders.get(mode, t('drawer.copilot_placeholder_default'))

    def _enrich_deterministic_actions(self, actions: List[QuickAction], local_context: str) -> List[QuickAction]:
        """
        Interviene sobre las acciones rápidas para dotarlas de respuesta determinista
        extrayendo específicamente el contenido de las etiquetas <help_config>, <help_example>
        y <help_actions> inyectadas por los generadores de documentación automatizados o guías nativas.
        """
        if not local_context or not local_context.strip():
            return actions

        import re

        for action in actions:
            query_lower = action.query.lower()

            # Interceptar "¿Cómo configuro?"
            if "cómo configuro" in query_lower or "configurar esta" in query_lower:
                match = re.search(r'<help_config>(.*?)</help_config>', local_context, re.DOTALL | re.IGNORECASE)
                if match:
                    action.action_type = "deterministic"
                    payload = match.group(1).strip()
                    # Eliminar títulos markdown (ej: ### Cómo configurar)
                    action.payload = re.sub(r'^#+ *.*$', '', payload, flags=re.MULTILINE).strip()
                else:
                    # Fallback si no hay documentación
                    action.action_type = "deterministic"
                    action.payload = "_Aún no hay una guía de configuración rápida pre-escrita para este componente. Intenta preguntarme cualquier duda específica en el panel inferior._"

            # Interceptar "¿Qué acciones hay?" / "qué tipos de acciones"
            elif "qué acciones" in query_lower or "qué tipos de acciones" in query_lower or "acciones puedo" in query_lower:
                match = re.search(r'<help_actions>(.*?)</help_actions>', local_context, re.DOTALL | re.IGNORECASE)
                if match:
                    action.action_type = "deterministic"
                    payload = match.group(1).strip()
                    # Eliminar títulos markdown (ej: ### Acciones disponibles)
                    action.payload = re.sub(r'^#+ *.*$', '', payload, flags=re.MULTILINE).strip()
                else:
                    action.action_type = "deterministic"
                    action.payload = "_Aún no hay una lista de acciones pre-escrita para este contexto. Pregúntame directamente sobre qué necesitas automatizar._"

            # Interceptar "Ver ejemplo"
            elif "ejemplo" in query_lower:
                match = re.search(r'<help_example>(.*?)</help_example>', local_context, re.DOTALL | re.IGNORECASE)
                if match:
                    action.action_type = "deterministic"
                    payload = match.group(1).strip()
                    # Eliminar títulos markdown (ej: ### Ejemplo)
                    action.payload = re.sub(r'^#+ *.*$', '', payload, flags=re.MULTILINE).strip()
                else:
                    action.action_type = "deterministic"
                    action.payload = "_Aún no hay un ejemplo oficial pre-escrito para este componente. Pregúntame abajo mencionando tu caso de uso._"

        return actions

    # NOTA: Quick actions y placeholders ahora se obtienen de _get_quick_actions() y _get_placeholder()

    def get_context(self) -> CopilotContext:
        """
        Detecta el modo actual y recopila contexto relevante.

        Returns:
            CopilotContext con toda la informacion necesaria para el chat
        """
        from client_app.app.services.layout_manager import layout_manager
        from client_app.app.core.state import state as app_state

        # Detectar modo basado en estado actual
        mode = self._detect_mode(layout_manager, app_state)

        # Recopilar contexto segun el modo
        if mode == 'documentation':
            return self._build_documentation_context(layout_manager)
        elif mode == 'flow_edit':
            return self._build_flow_edit_context(app_state)
        elif mode == 'web_watcher':
            return self._build_web_watcher_context(layout_manager)
        elif mode == 'etl':
            return self._build_etl_design_context(app_state)
        elif mode == 'graphics':
            return self._build_graphics_design_context(app_state)
        elif mode == 'report':
            return self._build_report_design_context(app_state)
        elif mode == 'flow':
            return self._build_flow_context(app_state)
        elif mode == 'atom' or mode == 'wizard':
            return self._build_atom_context(app_state, layout_manager)
        elif mode == 'gallery':
            return self._build_gallery_context()
        else:
            return self._build_idle_context()

    def _detect_mode(self, layout_manager, app_state) -> str:
        """Detecta el modo actual del usuario."""
        from automatia_shared.enums import StepType

        # Modo documentacion (desde click en icono doc)
        if layout_manager.current_mode == 'documentation':
            return 'documentation'

        # Modo flow_edit (diseñando flujo desde el editor)
        if layout_manager.current_mode == 'flow_edit':
            return 'flow_edit'

        # Modo web_watcher (diseñando monitor web)
        if layout_manager.current_mode == 'design' and layout_manager.designing_atom_type == StepType.WEB_WATCHER:
            return 'web_watcher'
            
        # Detectar modos de diseño específicos (ETL, Gráficos, Informes)
        if layout_manager.current_mode == 'design':
            if layout_manager.designing_atom_type == StepType.ETL_TRANSFORM:
                return 'etl'
            elif layout_manager.designing_atom_type == StepType.REPORT_GENERATE:
                return 'report'
            elif layout_manager.designing_atom_type == StepType.GRAPHICS:
                return 'graphics'
        
        # Modo Report Designer (Diseñador de plantillas)
        # Aquí asumimos que si el path es /reports/designer o hay un flag en app_state
        # Por ahora lo controlaremos si está en layout_manager o a través de una heurística
        # Si no hay match explícito, fallará a 'atom' como fallback genérico.
        # Si el usuario navega a /reports/designer, el layout_manager no necesariamente tiene un designing_atom_type
        # Lo manejaremos de otra forma si es necesario.

        # PRIORIDAD: Modo diseño de átomo (incluso si viene de flujo)
        # Si layout_manager está en modo design, estamos en página de configuración de átomo
        if layout_manager.current_mode == 'design' and layout_manager.designing_atom_type:
            return 'atom'

        # Modo atomo/wizard (editando un paso dentro del editor de flujos)
        if app_state.editing_step is not None:
            return 'atom'

        # Modo flujo (editando un flujo sin paso seleccionado)
        if app_state.editing_flow is not None:
            return 'flow'

        # Modo galería (selección de tipo de acción para diseño standalone)
        if layout_manager.current_mode == 'gallery':
            return 'gallery'

        return 'idle'

    def _build_documentation_context(self, layout_manager) -> CopilotContext:
        """Construye contexto para modo documentacion."""
        from client_app.app.services.local_knowledge_service import local_knowledge_service

        doc_data = layout_manager.doc_atom_data or {}
        atom_name = doc_data.get('name', 'Átomo')
        doc_path = doc_data.get('doc_path')
        input_contract = doc_data.get('input_contract')
        output_contract = doc_data.get('output_contract')

        # Generar contexto RAG
        local_context = local_knowledge_service.get_context_for_atom(
            atom_name=atom_name,
            doc_path=doc_path,
            atom_schema=self._parse_contracts(input_contract, output_contract),
            step_type=doc_data.get('type')
        )
        
        # Fallback de contexto en caso de no tener documentacion RAG, ni codigo, ni esquema
        if not local_context or not local_context.strip():
            description = doc_data.get('description', '')
            local_context = f"--- CONTEXTO ACCIÓN: {atom_name} ---\nEl usuario está consultando la acción/átomo: '{atom_name}'. No hay esquema ni documentación extendida cargada en el RAG local.\n"
            if description:
                local_context += f"Descripción: {description}\n"
            local_context += "---"

        actions = self._get_quick_actions('documentation')
        actions = self._enrich_deterministic_actions(actions, local_context)

        return CopilotContext(
            mode='documentation',
            local_context=local_context,
            atom_name=atom_name,
            quick_actions=actions,
            placeholder=f"Pregunta sobre {atom_name}..."
        )

    def _build_web_watcher_context(self, layout_manager) -> CopilotContext:
        """Construye contexto específico para configuración de Web Watcher."""
        local_context = """
--- CONTEXTO: MONITOR WEB ---
El usuario está configurando un monitor web. Tu rol es ayudarle como un "Ingeniero de DOM".

MODOS DE VIGILANCIA:
1. Página Completa: Ideal para webs que cambian poco (avisos legales, blogs, portales oficiales).
   - El sistema usa "Smart Digest" que elimina automáticamente: scripts, menús, footers, banners de cookies y anuncios.
   - Genera un hash del contenido principal para detectar cambios reales.
   - Ventaja: No requiere conocimientos técnicos.
   - Desventaja: Puede detectar cambios menores no deseados si el sitio es muy dinámico.

2. Selector Específico: Ideal para datos exactos (precios, stock, disponibilidad).
   - Requiere selector CSS (#id, .clase, tag) o XPath (//div[@class="precio"]).
   - Ventaja: Precisión quirúrgica, ignora todo el contenido irrelevante.
   - Desventaja: Requiere obtener el selector del elemento.

AYUDA PARA OBTENER SELECTORES:
Si el usuario no sabe obtener el selector, guíale paso a paso:
1. Abre la página web en el navegador
2. Pulsa F12 para abrir las DevTools (Herramientas de desarrollo)
3. Haz clic en el icono de selector (flecha) o pulsa Ctrl+Shift+C
4. Haz clic en el elemento que quieres vigilar
5. En el panel, clic derecho sobre el elemento resaltado
6. Selecciona "Copy" → "Copy selector" (para CSS) o "Copy XPath"

SELECTORES COMUNES PARA SITIOS CONOCIDOS:
- Amazon precio: #priceblock_ourprice, .a-price-whole, span[data-a-color="price"]
- eBay precio: .x-price-primary span
- Mercado Libre precio: .andes-money-amount__fraction
- AliExpress precio: .product-price-value

TONO: Apoyo técnico accesible. El usuario no es técnico, evita jerga innecesaria.
---
"""
        from client_app.app.services.local_knowledge_service import local_knowledge_service
        native_doc = local_knowledge_service.get_native_documentation('web_watcher', subfolder="actions")
        if native_doc:
            local_context = f"{local_context}\n\n--- DOCUMENTACIÓN NATIVA ---\n{native_doc}"

        actions = self._get_quick_actions('web_watcher')
        actions = self._enrich_deterministic_actions(actions, local_context)

        return CopilotContext(
            mode='web_watcher',
            local_context=local_context,
            quick_actions=actions,
            placeholder=self._get_placeholder('web_watcher')
        )

    def _build_flow_context(self, app_state) -> CopilotContext:
        """Construye contexto para modo flujo."""
        flow = app_state.editing_flow
        step = app_state.editing_step

        flow_context = None
        local_context = ""

        if flow:
            # Construir resumen del flujo para el contexto
            flow_summary = {
                'name': getattr(flow, 'name', 'Flujo sin nombre'),
                'steps_count': len(flow.steps) if hasattr(flow, 'steps') else 0,
                'steps': []
            }

            if hasattr(flow, 'steps'):
                for i, s in enumerate(flow.steps[:10]):  # Limitar a 10 pasos
                    step_info = {
                        'index': i,
                        'name': getattr(s, 'name', f'Paso {i+1}'),
                        'type': str(getattr(s, 'type', 'unknown'))
                    }
                    flow_summary['steps'].append(step_info)

            flow_context = flow_summary
            local_context = f"--- CONTEXTO FLUJO ---\n{json.dumps(flow_summary, indent=2, ensure_ascii=False)}\n---"

        # Si hay paso seleccionado, agregar info del paso
        atom_name = None
        if step:
            atom_name = getattr(step, 'name', None)
            step_type = str(getattr(step, 'type', 'unknown'))
            local_context += f"\n\nPaso seleccionado: {atom_name or step_type}"

        return CopilotContext(
            mode='flow',
            local_context=local_context,
            flow_context=flow_context,
            atom_name=atom_name,
            quick_actions=self._get_quick_actions('flow'),
            placeholder=self._get_placeholder('flow')
        )

    def _build_atom_context(self, app_state, layout_manager) -> CopilotContext:
        """Construye contexto para modo atomo/wizard."""
        from client_app.app.services.local_knowledge_service import local_knowledge_service
        from automatia_shared.enums import StepType

        step = app_state.editing_step
        atom_type = layout_manager.designing_atom_type

        atom_name = None
        atom_id = None
        local_context = ""
        quick_actions_key = 'atom'

        # Determinar el tipo de átomo activo
        active_type = atom_type or (getattr(step, 'type', None) if step else None)

        if step:
            atom_name = getattr(step, 'name', None)
            atom_id = str(getattr(step, 'id', '')) if hasattr(step, 'id') else None
            step_type = getattr(step, 'type', None)

            # Determinar tipo de pills segun el tipo de paso
            if step_type:
                type_str = str(step_type).lower()
                if 'extraction' in type_str:
                    quick_actions_key = 'extraction'
                elif 'connection' in type_str:
                    quick_actions_key = 'connection'
                elif 'llm_process' in type_str:
                    quick_actions_key = 'llm_process'

            # Intentar obtener contexto del atomo
            config = getattr(step, 'config', {}) or {}
            local_context = local_knowledge_service.get_context_for_atom(
                atom_id=int(atom_id) if atom_id and atom_id.isdigit() else None,
                atom_name=atom_name,
                atom_schema=config,
                step_type=active_type
            )

        elif atom_type:
            # En modo wizard sin paso aun
            atom_name = str(atom_type)
            type_str = atom_name.lower()
            if 'extraction' in type_str:
                quick_actions_key = 'extraction'
            elif 'connection' in type_str:
                quick_actions_key = 'connection'
            elif 'llm_process' in type_str:
                quick_actions_key = 'llm_process'
                
            local_context = local_knowledge_service.get_context_for_atom(
                atom_name=atom_name,
                step_type=active_type
            )

        # Agregar capacidades de UI al contexto para que la IA sepa qué pestañas están visibles
        from client_app.app.config.capability_map import get_atom_capability
        cap = get_atom_capability(active_type)
        if cap:
            local_context += f"\n\n--- UI CAPABILITIES ---\n"
            local_context += f"Has Stepper (Ajustes): {cap.has_stepper}\n"
            local_context += f"Has Variables: {cap.has_variables}\n"
            if not cap.has_stepper:
                local_context += "NOTE: The 'Ajustes' (settings) tab is HIDDEN for this atom type. Explain things via chat.\n"
            if not cap.has_variables:
                local_context += "NOTE: The 'Variables' tab is HIDDEN for this atom type. This atom doesn't expose output variables.\n"

            # Añadir ayuda contextual del átomo si existe
            if cap.contextual_help:
                local_context += "\n--- AYUDA CONTEXTUAL DE ESTA ACCIÓN ---\n"
                for help_item in cap.contextual_help:
                    local_context += f"- {help_item.get('title', '')}: {help_item.get('message', '')}\n"
            local_context += "---"

        # Inyectar variables del flujo contextual si estamos diseñando dentro de un flujo
        local_context += self._get_flow_context_snippet(app_state)

        actions = self._get_quick_actions(quick_actions_key)
        actions = self._enrich_deterministic_actions(actions, local_context)

        return CopilotContext(
            mode='atom',
            local_context=local_context,
            atom_id=atom_id,
            atom_name=atom_name,
            quick_actions=actions,
            placeholder=self._get_placeholder('atom')
        )

    def _build_flow_edit_context(self, app_state) -> CopilotContext:
        """
        Construye contexto específico para diseño de flujos.

        Este contexto le indica claramente a la IA que el usuario está
        en el editor de flujos diseñando su automatización.
        """
        flow = app_state.editing_flow

        # Construir información del flujo actual
        flow_name = getattr(flow, 'name', 'Nuevo Flujo') if flow else 'Nuevo Flujo'
        steps_info = []
        steps_count = 0

        if flow and hasattr(flow, 'steps') and flow.steps:
            steps_count = len(flow.steps)
            for i, s in enumerate(flow.steps[:10]):
                step_type = str(getattr(s, 'type', 'unknown'))
                step_name = getattr(s, 'name', f'Paso {i+1}')
                steps_info.append(f"  {i+1}. [{step_type}] {step_name}")

        steps_list = "\n".join(steps_info) if steps_info else "  (ningún paso añadido todavía)"

        # Contexto claro y directo para la IA
        local_context = f"""--- CONTEXTO: EDITOR DE FLUJOS ---
UBICACIÓN: El usuario está en el EDITOR DE FLUJOS, diseñando una automatización.
NO preguntes dónde está ni qué está haciendo. Ya lo sabes.

FLUJO ACTUAL:
- Nombre: {flow_name}
- Pasos definidos: {steps_count}
{steps_list}

TU ROL:
Eres un arquitecto de automatizaciones. Tu trabajo es:
1. Escuchar lo que el usuario quiere automatizar
2. Sugerir los PASOS (acciones) necesarios en orden
3. Explicar qué hace cada paso y por qué es necesario

PASOS DISPONIBLES EN LA PLATAFORMA:
- TRIGGERS (Disparadores): SCHEDULER (programado), FOLDER_WATCHER (monitor carpeta), EMAIL_WATCHER (monitor email), WEB_WATCHER (monitor web)
- INPUTS (Entradas): API_FETCH (petición API), SQL_QUERY (consulta SQL), FOLDER_SCAN (escaneo carpeta), EMAIL_SCAN (escaneo email)
- PROCESSORS (Procesadores): ETL_TRANSFORM (transformación datos), EXTRACTION (extracción PDF), CUSTOM_SCRIPT (script Python), RPA_EXECUTE (automatización web), GRAPHICS (visualizaciones), PDF_TOOLS (unir/dividir PDFs)
- OUTPUTS (Salidas): SMTP (envío email), SQL_INSERT (insertar en BD), ARCHIVE_FILE (archivar archivos), EMAIL_SEND (envío email avanzado)

FORMATO DE RESPUESTA PARA PROPUESTAS:
Cuando sugieras pasos para un flujo, usa EXACTAMENTE este formato:
1. [TIPO_PASO] Nombre descriptivo - Breve explicación
2. [TIPO_PASO] Otro paso - Breve explicación
...

Donde TIPO_PASO debe ser uno de: API_FETCH, SQL_QUERY, SQL_INSERT, SMTP, EMAIL_SEND, FOLDER_SCAN, EMAIL_SCAN, ETL_TRANSFORM, EXTRACTION, GRAPHICS, CUSTOM_SCRIPT, RPA_EXECUTE, ARCHIVE_FILE, SCHEDULER, FOLDER_WATCHER, EMAIL_WATCHER, WEB_WATCHER, PDF_TOOLS

EJEMPLO DE RESPUESTA CORRECTA:
"Para automatizar la descarga de datos y envío por email, te sugiero:
1. [API_FETCH] Conexión API - Descarga los datos del endpoint configurado
2. [ETL_TRANSFORM] Transformación - Procesa y filtra los datos
3. [SMTP] Envío email - Envía el resultado al destinatario"

IMPORTANTE:
- El usuario puede añadir pasos usando el botón "AÑADIR PASO" en el editor
- Los datos fluyen de un paso al siguiente usando variables como {{paso_anterior.campo}}
- Sé directo y conciso. No hagas preguntas innecesarias.
---"""
        from client_app.app.services.local_knowledge_service import local_knowledge_service
        native_doc = local_knowledge_service.get_native_documentation('flow_designer', subfolder="core")
        if native_doc:
            local_context = f"--- CONTEXTO: EDITOR DE FLUJOS ---\n{native_doc}\n{local_context}"

        # Enriquecer quick actions con respuestas deterministas de la documentación
        actions = self._get_quick_actions('flow_edit')
        actions = self._enrich_deterministic_actions(actions, local_context)

        return CopilotContext(
            mode='flow_edit',
            local_context=local_context,
            flow_context={'name': flow_name, 'steps_count': steps_count},
            quick_actions=actions,
            placeholder=self._get_placeholder('flow_edit')
        )

    def _build_etl_design_context(self, app_state) -> CopilotContext:
        """Construye contexto para el diseño de ETL."""
        local_context = f"""--- CONTEXTO: DISEÑADOR ETL ---
UBICACIÓN: El usuario está configurando una transformación de datos (ETL).

TU ROL:
Ayudar al usuario a definir operaciones de transformación de datos paso a paso.
IMPORTANTE: Usa las columnas REALES del usuario que aparecen en "DATOS DISPONIBLES".

FORMATO DE PROPUESTA:
Cuando sugieras operaciones ETL, debes usar el siguiente formato estricto:
1. [ETL_OP] Tipo de operación - Descripción breve de la operación y {{"parámetros JSON válidos"}}

OPERACIONES DISPONIBLES (ETL_OP):
- drop_columns: {{"columns": ["NombreColumnaReal1", "NombreColumnaReal2"]}}
- rename_columns: {{"mapping": {{"NombreColumnaActual": "NuevoNombre"}}}}
- filter_rows: {{"column": "NombreColumnaReal", "operator": "==", "value": "xyz"}} (operadores: ==, !=, >, <, >=, <=, contains, not_contains)
- replace_values: {{"column": "NombreColumnaReal", "replacements": {{"valorViejo": "valorNuevo"}}}}
- fill_nulls: {{"columns": ["NombreColumnaReal"], "value": "0"}}
- remove_duplicates: {{"subset": ["NombreColumnaReal"], "keep": "first"}}
- merge_columns: {{"source_columns": ["Columna1", "Columna2"], "separator": "-", "target_column": "NuevaColumna", "drop_source": true}}
- reorder_columns: {{"columns": ["Columna3", "Columna1", "Columna2"]}}

EJEMPLO DE RESPUESTA (usa columnas reales del usuario):
"Aquí tienes algunas operaciones para aplicar:
1. [ETL_OP] drop_columns - Elimina columnas innecesarias {{"columns": ["ColumnaNoDeseada"]}}
2. [ETL_OP] rename_columns - Renombrar para claridad {{"mapping": {{"NombreActual": "NombreMejor"}}}}"

IMPORTANTE - LIMITACIONES DEL MODO ASISTIDO:
- Las operaciones listadas arriba son para el MODO ASISTIDO (transformaciones predefinidas).
- El modo asistido NO soporta: agregaciones (GROUP BY, SUM, AVG), joins, pivots, cálculos complejos, o columnas calculadas.

MODO IA - PARA TRANSFORMACIONES AVANZADAS:
- Si el usuario pide algo que NO está en la lista de operaciones del modo asistido (como agrupar, sumar, promediar, pivotar, crear columnas calculadas, etc.), DEBES sugerir usar el Modo IA.
- Para sugerir una transformación con Modo IA, usa el formato [ETL_AI_PROMPT]:

[ETL_AI_PROMPT]
Descripción completa de la transformación en lenguaje natural.
Incluye todas las operaciones necesarias: eliminar columnas, agrupar, calcular, etc.
[/ETL_AI_PROMPT]

EJEMPLO - Si el usuario pide "quiero quedarme solo con las columnas Categoria y Ventas, y agrupar por Categoria sumando las Ventas":

"Esta transformación requiere agrupación, que no está disponible en el modo asistido. Te propongo usar el Modo IA con estas instrucciones:

[ETL_AI_PROMPT]
1. Conservar únicamente las columnas 'Categoria' y 'Ventas' (eliminar el resto)
2. Agrupar los datos por la columna 'Categoria'
3. Sumar los valores de 'Ventas' para cada grupo
4. El resultado debe tener dos columnas: 'Categoria' y 'Ventas_Total'
[/ETL_AI_PROMPT]"

REGLAS:
- Si TODO lo que pide el usuario se puede hacer con [ETL_OP], usa [ETL_OP].
- Si ALGO de lo que pide requiere IA (agrupaciones, cálculos, etc.), usa [ETL_AI_PROMPT] e incluye TODAS las operaciones juntas (incluso las simples como eliminar columnas).
- NUNCA inventes operaciones [ETL_OP] que no existen.
- NUNCA mezcles [ETL_OP] y [ETL_AI_PROMPT] en la misma respuesta. Elige uno.
---"""
        from client_app.app.services.local_knowledge_service import local_knowledge_service
        native_doc = local_knowledge_service.get_native_documentation('etl_transform', subfolder="actions")
        if native_doc:
            local_context = f"--- CONTEXTO NATIVO: ETL ---\n{native_doc}\n\n{local_context}"

        # Añadir contexto de datos (columnas reales del usuario)
        local_context += self._get_data_context_snippet(app_state)
        local_context += self._get_flow_context_snippet(app_state)

        return CopilotContext(
            mode='etl',
            local_context=local_context,
            quick_actions=self._get_quick_actions('atom'),
            placeholder=self._get_placeholder('atom'),
            data_context=self._get_data_context_dict(app_state)
        )

    def _build_graphics_design_context(self, app_state) -> CopilotContext:
        """Construye contexto para configurar visualizaciones."""
        local_context = f"""--- CONTEXTO: DISEÑADOR DE GRÁFICOS ---
UBICACIÓN: El usuario está configurando un gráfico y visualización de datos.

TU ROL:
Sugerir el tipo de gráfico correcto y sus parámetros básicos basados en la petición del usuario.
IMPORTANTE: Usa las columnas REALES del usuario que aparecen en "DATOS DISPONIBLES".

FORMATO DE PROPUESTA:
Cuando sugieras gráficos, DEBES usar el siguiente formato estricto:
1. [GRAPHICS_CONFIG] Tipo de gráfico - Descripción e intenciones con el {{"json de config"}}

TIPOS DE GRÁFICOS DISPONIBLES (GRAPHICS_CONFIG):
- bar, barh, bar_grouped, bar_stacked
- line, line_multi
- scatter, bubble
- pie, donut
- histogram, boxplot, violin
- heatmap

EJEMPLO DE CONFIGURACIÓN JSON:
{{"x_column": "NombreColumnaReal", "y_column": "OtraColumnaReal", "color_column": "ColumnaCategoria", "title": "Título descriptivo", "palette": "viridis", "style": "whitegrid"}}

EJEMPLO DE RESPUESTA:
"Para visualizar tus datos, un gráfico de barras apiladas es buena opción:
1. [GRAPHICS_CONFIG] bar_stacked - Barras apiladas {{"x_column": "ColumnaX", "y_column": "ColumnaY", "color_column": "ColumnaColor"}}"

IMPORTANTE - LIMITACIONES:
- Este módulo solo genera los tipos de gráficos listados arriba.
- Si el usuario pide un tipo de gráfico que no está disponible, infórmale y sugiere la alternativa más cercana.
- NUNCA inventes tipos de gráficos que no existen en la lista.
---"""
        from client_app.app.services.local_knowledge_service import local_knowledge_service
        native_doc = local_knowledge_service.get_native_documentation('report_generate', subfolder="actions")
        if native_doc:
            local_context = f"--- CONTEXTO NATIVO: GRÁFICOS ---\n{native_doc}\n\n{local_context}"

        # Añadir contexto de datos (columnas reales del usuario)
        local_context += self._get_data_context_snippet(app_state)
        local_context += self._get_flow_context_snippet(app_state)

        return CopilotContext(
            mode='graphics',
            local_context=local_context,
            quick_actions=self._get_quick_actions('atom'),
            placeholder=self._get_placeholder('atom'),
            data_context=self._get_data_context_dict(app_state)
        )

    def _build_report_design_context(self, app_state) -> CopilotContext:
        """Construye contexto para el diseñador de informes PDF/HTML."""
        local_context = f"""--- CONTEXTO: DISEÑADOR DE INFORMES ---
UBICACIÓN: El usuario está armando la estructura de un informe (informe PDF o HTML).

TU ROL:
Sugerir bloques para poblar el informe (texto, gráfico, tabla).
IMPORTANTE: Usa las columnas REALES del usuario que aparecen en "DATOS DISPONIBLES".

FORMATO DE PROPUESTA:
DEBES usar este formato:
1. [REPORT_BLOCK] Tipo de bloque - Descripción con {{"json config"}}

BLOQUES (REPORT_BLOCK):
- text: {{"content": "# Título principal\\nAquí va el texto y {{{{variable}}}}"}}
- chart: {{"chart_type": "bar", "title": "Título", "x_field": "NombreColumnaReal", "y_field": "OtraColumnaReal", "data_field": "datos"}}
- table: {{"data_field": "datos", "columns": [{{"field": "NombreColumnaReal", "header": "Encabezado"}}]}}

EJEMPLO DE RESPUESTA (usa columnas reales del usuario):
"Podemos estructurar tu informe de la siguiente forma:
1. [REPORT_BLOCK] text - Cabecera del informe {{"content": "# Reporte\\nResumen de datos."}}
2. [REPORT_BLOCK] chart - Gráfico principal {{"chart_type": "bar", "title": "Métricas", "x_field": "ColumnaX", "y_field": "ColumnaY"}}"

IMPORTANTE - LIMITACIONES:
- Este módulo solo soporta los tipos de bloque listados arriba (text, chart, table).
- Si el usuario pide funcionalidad que no está disponible (ej: cálculos, agregaciones, lógica condicional), infórmale claramente.
- NUNCA inventes bloques o funcionalidades que no existen.
---"""
        # Añadir contexto de datos (columnas reales del usuario)
        local_context += self._get_data_context_snippet(app_state)
        local_context += self._get_flow_context_snippet(app_state)

        return CopilotContext(
            mode='report',
            local_context=local_context,
            quick_actions=self._get_quick_actions('atom'),
            placeholder=self._get_placeholder('atom'),
            data_context=self._get_data_context_dict(app_state)
        )

    def _build_idle_context(self) -> CopilotContext:
        """Construye contexto para modo idle (sin contexto activo)."""
        return CopilotContext(
            mode='idle',
            local_context="",
            quick_actions=self._get_quick_actions('idle'),
            placeholder=self._get_placeholder('idle')
        )

    def _build_gallery_context(self) -> CopilotContext:
        """
        Construye contexto para la galería de átomos (selección de tipo de acción).

        En este modo, el usuario está explorando qué tipo de acción standalone puede crear.
        Cargamos la documentación del flow_designer que contiene la lista de acciones
        disponibles para que las ayudas rápidas sean deterministas.
        """
        from client_app.app.services.local_knowledge_service import local_knowledge_service

        # Cargar documentación del flow_designer que tiene las etiquetas <help_actions> y <help_example>
        native_doc = local_knowledge_service.get_native_documentation('flow_designer', subfolder="core")

        local_context = """--- CONTEXTO: GALERÍA DE ÁTOMOS ---
UBICACIÓN: El usuario está en la Galería de Átomos, explorando qué tipo de acción crear.

TU ROL:
Ayudar al usuario a entender qué tipos de automatizaciones puede crear y guiarle
en la selección del tipo de acción más apropiado para su caso de uso.

TIPOS DE ACCIONES DISPONIBLES:
Cada "átomo" es una acción independiente que puede ejecutarse de forma standalone
o incorporarse a un flujo mayor.
---"""

        if native_doc:
            local_context = f"{local_context}\n\n--- DOCUMENTACIÓN NATIVA ---\n{native_doc}"

        # Enriquecer quick actions con respuestas deterministas
        actions = self._get_quick_actions('gallery')
        actions = self._enrich_deterministic_actions(actions, local_context)

        return CopilotContext(
            mode='gallery',
            local_context=local_context,
            quick_actions=actions,
            placeholder=self._get_placeholder('gallery')
        )

    def _parse_contracts(
        self,
        input_contract: Optional[str],
        output_contract: Optional[str]
    ) -> Optional[Dict]:
        """Parsea contratos JSON a dict para usar como schema."""
        result = {}

        if input_contract:
            try:
                if isinstance(input_contract, str):
                    result['input'] = json.loads(input_contract)
                else:
                    result['input'] = input_contract
            except json.JSONDecodeError:
                pass

        if output_contract:
            try:
                if isinstance(output_contract, str):
                    result['output'] = json.loads(output_contract)
                else:
                    result['output'] = output_contract
            except json.JSONDecodeError:
                pass

        return result if result else None

    def _get_flow_context_snippet(self, app_state) -> str:
        """Helper para obtener las variables y el contexto del flujo al editar una accion de flujo."""
        flow = app_state.editing_flow
        step = app_state.editing_step
        
        if not flow or not getattr(flow, 'steps', None):
            return ""

        snippet = "\n\n--- CONTEXTO DE VARIABLES DEL FLUJO (INYECCIÓN DE DATOS PREVIOS) ---\n"
        snippet += "Estás diseñando esta acción dentro de un flujo orquestador. Tienes a tu disposición las siguientes VARIABLES generadas por los pasos anteriores de este flujo, que DEBES sugerir al usuario usar, mediante el formato Jinja {{nombre_paso.variable}}:\n"
        
        current_step_id = getattr(step, 'id', None)
        has_previous = False
        
        for i, s in enumerate(flow.steps):
            if current_step_id and getattr(s, 'id', None) == current_step_id:
                break # Solo procesar los anteriores
            
            s_type = str(getattr(s, 'type', 'unknown'))
            s_name = getattr(s, 'name', f'Paso_{i+1}')
            
            # Limpiar nombre del paso para variables
            clean_name = s_name.lower().replace(' ', '_')
            clean_name = ''.join(e for e in clean_name if e.isalnum() or e == '_')
            
            snippet += f"\n- Paso {i+1}: [{s_type}] '{s_name}' (Prefijo para variables: {clean_name})\n"
            
            config = getattr(s, 'config', {}) or {}
            out_schema = config.get('output_contract', {})
            
            if isinstance(out_schema, str):
                try: 
                    import json
                    out_schema = json.loads(out_schema)
                except Exception: 
                    out_schema = {}
                    
            if out_schema and isinstance(out_schema, dict):
                # Extraer informacion de variables del JSON Schema si existe
                props = out_schema.get('properties', {})
                if props:
                    for var_name, var_info in props.items():
                        desc = var_info.get('description', '')
                        var_type = var_info.get('type', 'desconocido')
                        snippet += f"  > {{{{{clean_name}.{var_name}}}}} : {var_type} - {desc}\n"
                        has_previous = True
            else:
                snippet += f"  (Sin variables estructuradas declaradas)\n"
                 
        snippet += "---\n"

        return snippet if has_previous else ""

    def _get_data_context_snippet(self, app_state) -> str:
        """
        Helper para obtener el contexto de datos actual (columnas, tipos, ejemplos).
        Las páginas de diseño (ETL, Graphics, Reports) deben poblar
        app_state.current_data_context cuando cargan datos.
        """
        data_ctx = getattr(app_state, 'current_data_context', None)
        if not data_ctx:
            return ""

        columns = data_ctx.get('columns', [])
        if not columns:
            return ""

        snippet = "\n\n--- DATOS DISPONIBLES ---\n"
        snippet += "El usuario ha cargado datos con las siguientes columnas. USA ESTOS NOMBRES EXACTOS en tus sugerencias:\n\n"

        dtypes = data_ctx.get('dtypes', {})
        sample_values = data_ctx.get('sample_values', {})
        row_count = data_ctx.get('row_count', 0)

        snippet += f"Total de filas: {row_count}\n"
        snippet += f"Columnas ({len(columns)}):\n"

        for col in columns:
            dtype = dtypes.get(col, 'desconocido')
            # Simplificar tipo para el LLM
            if 'int' in str(dtype).lower():
                dtype_simple = 'numérico (entero)'
            elif 'float' in str(dtype).lower():
                dtype_simple = 'numérico (decimal)'
            elif 'datetime' in str(dtype).lower() or 'date' in str(dtype).lower():
                dtype_simple = 'fecha'
            elif 'bool' in str(dtype).lower():
                dtype_simple = 'booleano'
            else:
                dtype_simple = 'texto'

            sample = sample_values.get(col, [])
            sample_str = ""
            if sample:
                # Mostrar hasta 3 valores de ejemplo
                sample_preview = [str(v)[:30] for v in sample[:3]]
                sample_str = f" → Ejemplos: {', '.join(sample_preview)}"

            snippet += f"  • {col} ({dtype_simple}){sample_str}\n"

        snippet += "\nIMPORTANTE: Usa los nombres de columna EXACTAMENTE como aparecen arriba.\n"
        snippet += "---\n"

        return snippet

    def _get_data_context_dict(self, app_state) -> Optional[Dict[str, Any]]:
        """Obtiene el contexto de datos como dict para incluir en CopilotContext."""
        return getattr(app_state, 'current_data_context', None)


# Singleton instance
copilot_context_service = CopilotContextService()
