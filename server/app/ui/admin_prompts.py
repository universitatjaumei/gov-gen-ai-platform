
"""
Editor Avanzado de System Prompts.

Permite refinar las instrucciones maestras enviadas a los modelos de IA 
en cada fase del proceso, gestionando variables dinámicas y overrides de 
potencia (Tiers) según la complejidad de la tarea.
"""
from nicegui import ui
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.core.state import state
from server.app.database.db import server_engine
from server.app.database.models import ExtractionServiceConfig


    

# --- TIER SELECTOR ---
# --- TIER SELECTOR ---
# Note: Labels are now translation keys or processed at runtime
# We keep values here but labels will be resolved dynamically
TIER_OPTIONS = [
    {"value": None, "key_label": "tier_default_label", "key_desc": "tier_default_desc", "badge": "⚪"},
    {"value": 1, "key_label": "tier_1_label", "key_desc": "tier_1_desc", "badge": "🟢"},
    {"value": 2, "key_label": "tier_2_label", "key_desc": "tier_2_desc", "badge": "🟡"},
    {"value": 3, "key_label": "tier_3_label", "key_desc": "tier_3_desc", "badge": "🔴"},
]

def admin_prompts_content():
    t = state.i18n.t

    # --- PROMPT METADATA MAPPING ---
    # --- PROMPT METADATA MAPPING ---
    PROMPT_METADATA = {
        # EXT Priority 1
        "System: Discovery (Fase 0)": { "task": "Extracción PDF", "phase": "Fase 0: Data Discovery", "icon": "search", "color": "blue", "sort_priority": 10 },
        "System: Precision Extraction (Fase 1)": { "task": "Extracción PDF", "phase": "Fase 1: Extracción de Precisión", "icon": "description", "color": "indigo", "sort_priority": 11 },
        "System: Refinement (Golden Record)": { "task": "Extracción PDF", "phase": "Fase 2: Refinamiento de Datos", "icon": "verified", "color": "green", "sort_priority": 12 },
        "System: Data Noise Filter": { "task": "Extracción PDF", "phase": "Filtrado de Ruido", "icon": "filter_alt", "color": "orange", "sort_priority": 13 },
        "System: Clarification (Extraction)": { "task": "Extracción PDF", "phase": "Clarificación", "icon": "contact_support", "color": "indigo", "sort_priority": 14 },
        
        # RPA Priority 2
        "System: RPA Analysis": { "task": "Navegación RPA", "phase": "Análisis de Tarea Web", "icon": "public", "color": "cyan", "sort_priority": 20 },
        "System: RPA Refinement": { "task": "Navegación RPA", "phase": "Refinamiento de Selector", "icon": "ads_click", "color": "teal", "sort_priority": 21 },
        "System: RPA Vision": { "task": "Navegación RPA", "phase": "Visión Computacional", "icon": "visibility", "color": "cyan", "sort_priority": 22 },
        "System: Clarification (RPA)": { "task": "Navegación RPA", "phase": "Clarificación", "icon": "contact_support", "color": "cyan", "sort_priority": 23 },
        
        # ETL Priority 3
        "System: Script Factory (Phase 1)": { "task": "Transformación ETL", "phase": "Fase 1: Generación de Código", "icon": "code", "color": "pink", "sort_priority": 30 },
        "Auto-reparación y Refinamiento (Fase 3)": { "task": "Extracción PDF", "phase": "Fase 3: Auto-reparación de Script", "icon": "loop", "color": "purple", "sort_priority": 15 },
        "System: Script Refinement Loop (Phase 3)": { "task": "Extracción PDF", "phase": "Fase 3: Auto-reparación de Script", "icon": "loop", "color": "purple", "sort_priority": 15 },
        "System: Audit Forensic (Phase 3)": { "task": "Extracción PDF", "phase": "Fase 3: Análisis de Calidad", "icon": "gavel", "color": "red", "sort_priority": 16 },
        "System: Script Factory (Phase 3)": { "task": "Extracción PDF", "phase": "Fase 3: Generación de Script", "icon": "factory", "color": "deep-purple", "sort_priority": 14 },
        "System: Clarification (ETL)": { "task": "Transformación ETL", "phase": "Clarificación", "icon": "contact_support", "color": "purple", "sort_priority": 33 },

        # Custom Scripts Priority 4
        "System: Custom Script Generator": { "task": "Personalizados", "phase": "Generación de Scripts", "icon": "auto_fix_high", "color": "pink", "sort_priority": 40 },
        "System: Clarification (Custom Script)": { "task": "Personalizados", "phase": "Clarificación", "icon": "contact_support", "color": "pink", "sort_priority": 41 },

        # Flow Orchestration Priority 5
        "System: Flow Orchestrator": { "task": "Orquestador", "phase": "Orquestación de Flujos", "icon": "hub", "color": "red", "sort_priority": 50 },
    }

    # Map Tasks to Default Tiers (Inferred)
    # Tier 1 (Flash): Extraction
    # Tier 2 (Logic): RPA, Navigation
    # Tier 3 (Supervision): ETL, Code Gen
    DEFAULT_TIER_MAPPING = {
        "Extracción PDF": 1,
        "Navegación RPA": 2,
        "Transformación ETL": 3,
        "Personalizados": 3,
        "Orquestador": 3
    }

    # Main Container (Vertical Stack) - use tight gap to avoid huge spaces
    with ui.column().classes('w-full gap-4'):
        
        # 1. HEADER & FILTERS
        with ui.card().classes('w-full p-4 border border-gray-200 shadow-sm'):
            with ui.row().classes('w-full justify-between items-center mb-2'):
                ui.label("Editor de Prompts").classes('text-2xl font-bold text-slate-800')
                ui.icon('tune', size='sm').classes('text-gray-400')
            
            with ui.row().classes('w-full gap-4 items-center'):
                search_input = ui.input(placeholder="Buscar por nombre...").props('outlined dense prepend-inner-icon="search"').classes('flex-grow')
                
                # Extract unique tasks and phases for filters
                unique_tasks = sorted(list(set(m['task'] for m in PROMPT_METADATA.values())))
                unique_phases = sorted(list(set(m['phase'] for m in PROMPT_METADATA.values())))
                
                task_filter = ui.select(options=['Todas'] + unique_tasks, value='Todas', label="Tarea / Función").props('outlined dense options-dense').classes('w-64')
                phase_filter = ui.select(options=['Todas'] + unique_phases, value='Todas', label="Fase del Proceso").props('outlined dense options-dense').classes('w-64')

        # 2. RESULTS GRID (Selection)
        # Changed to max 3 columns: lg:grid-cols-3
        results_container = ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3')
        
        # 3. EDITOR (Full Width)
        # Remove min-height fixed to avoid gap if empty, handle visibility dynamically
        editor_card = ui.card().classes('w-full p-0 border border-gray-200 shadow-md hidden').classes('remove-hidden') # logic below
        editor_content = ui.column().classes('w-full h-full p-6')

        # --- LOGIC ---
        
        current_prompts = [] 
        current_selection = {'id': None}

        async def load_prompt_editor(service_id):
            editor_content.clear()
            current_selection['id'] = service_id
            
            if not service_id:
                editor_card.set_visibility(False)
                return
            
            editor_card.set_visibility(True)

            prompt_data = None
            async with AsyncSession(server_engine) as session:
                prompt_data = await session.get(ExtractionServiceConfig, service_id)
            
            if not prompt_data: return

            meta = PROMPT_METADATA.get(prompt_data.name, {"icon": "edit", "color": "gray", "task": "Sistema", "phase": "General"})
            
            with editor_content:
                # Editor Header
                with ui.row().classes('w-full items-center mb-6 pb-4 border-b gap-4'):
                    with ui.column().classes(f'p-3 bg-{meta["color"]}-50 rounded-lg'):
                        ui.icon(meta['icon'], size='md').classes(f'text-{meta["color"]}-600')
                    with ui.column().classes('gap-1'):
                        ui.label(prompt_data.name).classes('text-2xl font-bold text-slate-800')
                        with ui.row().classes('gap-2'):
                            ui.badge(meta['task'], color=meta['color']).props('outline')
                            ui.icon('arrow_right', size='xs').classes('text-gray-300')
                            ui.label(meta['phase']).classes('text-sm text-gray-500 italic')
                
                # Metadata Row (Horizontal 3 columns)
                with ui.grid(columns=3).classes('w-full gap-4 mb-4'):
                     ui.input('ID Servicio', value=prompt_data.service_id).props('outlined dense readonly label-color="primary"').classes('w-full')
                     ui.input(t('prompt_name'), value=prompt_data.name).props('outlined dense readonly label-color="primary"').classes('w-full')
                     ui.textarea(t('description'), value=prompt_data.description).props('outlined dense readonly label-color="primary" rows=1').classes('w-full')

                # Tier Selector
                with ui.column().classes('w-full mb-4 p-3 border border-gray-200 rounded-lg bg-gray-50'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                         ui.icon('layers', size='xs').classes('text-gray-500')
                         ui.label(t('admin.prompts.tier_selector_label')).classes('font-bold text-gray-700 text-sm')
                    
                    # Generate options dict dynamically with translations
                    tier_opts = {}
                    default_tier_num = DEFAULT_TIER_MAPPING.get(meta.get("task"), 2) # Default to Tier 2 if unknown
                    
                    for opt in TIER_OPTIONS:
                        label = t("admin.prompts." + opt["key_label"])
                        if opt["value"] is None:
                             # Append default info: "Por defecto (usa rol: Tier X)"
                             default_tier_name = t(f"admin.prompts.tier_{default_tier_num}_label").split("-")[-1].strip() # e.g. "Flash"
                             label = f"{label}: Tier {default_tier_num} ({default_tier_name})"
                        
                        tier_opts[opt["value"]] = f'{opt["badge"]} {label}'

                    tier_radio = ui.radio(
                        options=tier_opts,
                        value=prompt_data.tier_override if hasattr(prompt_data, 'tier_override') else None
                    ).props('inline').classes('w-full text-sm')

                    # Tooltip dinámico
                    tier_info = ui.label("").classes('text-xs text-blue-600 italic mt-1 ml-1')

                    def update_tier_info(e):
                        selected = next((o for o in TIER_OPTIONS if o["value"] == e.value), None)
                        if selected:
                            tier_info.text = t("admin.prompts." + selected["key_desc"])
                    
                    tier_radio.on_value_change(update_tier_info)
                    update_tier_info(tier_radio)

                # Editor Area (Full Width below metadata)
                with ui.column().classes('w-full flex-grow gap-2'):
                    with ui.row().classes('w-full justify-between items-center'):
                        ui.label(t('prompt_template')).classes('font-bold text-gray-700')
                        vars_label = ui.label(t('detected_vars') + ': -').classes('text-xs bg-gray-100 px-2 py-1 rounded text-gray-600')

                    text_area = ui.textarea(
                        value=prompt_data.system_prompt_template,
                        placeholder='Instrucciones para la IA...'
                    ).classes('w-full flex-grow text-sm font-mono').props('outlined input-class="font-mono text-gray-700 leading-relaxed" rows=20 spellcheck="false"')
                    
                    def update_vars(e):
                        import re
                        vs = re.findall(r'\{([^}]+)\}', e.value or '')
                        vars_label.text = f"{t('detected_vars')}: {', '.join(sorted(set(vs)))}"
                    text_area.on('input', update_vars)
                    update_vars(text_area)

                # Actions
                ui.separator().classes('my-6')
                with ui.row().classes('w-full justify-end gap-3'):
                    async def save_prompt():
                        if not current_selection['id']: return
                        async with AsyncSession(server_engine) as session:
                            p = await session.get(ExtractionServiceConfig, current_selection['id'])
                            if p:
                                p.system_prompt_template = text_area.value
                                if hasattr(p, 'tier_override'):
                                    p.tier_override = tier_radio.value
                                session.add(p)
                                await session.commit()
                        ui.notify(t('prompt_saved'), type='positive')
                    
                    ui.button(t('save'), icon='save', on_click=save_prompt).props('color=primary unelevated size=lg')
            
            # Scroll to editor
            ui.run_javascript(f'window.scrollTo(0, document.body.scrollHeight);')


        def render_results():
            results_container.clear()
            
            # Filter Logic
            term = search_input.value.lower()
            sel_task = task_filter.value
            sel_phase = phase_filter.value
            
            filtered = []
            for p in current_prompts:
                # 1. Name Search
                if term and term not in p.name.lower(): continue
                
                # 2. Metadata Filters
                meta = PROMPT_METADATA.get(p.name, {"task": "Sistema", "phase": "General"})
                
                if sel_task != 'Todas' and meta.get('task') != sel_task: continue
                if sel_phase != 'Todas' and meta.get('phase') != sel_phase: continue
                
                filtered.append(p)

            with results_container:
                if not filtered:
                    ui.label("No se encontraron prompts.").classes('col-span-full text-center text-gray-400 italic py-4')
                
                for p in filtered:
                     meta = PROMPT_METADATA.get(p.name, {"task": "Sistema", "phase": "General", "icon": "settings", "color": "gray"})
                     # Card
                     with ui.card().classes('p-3 cursor-pointer hover:shadow-lg transition-all border-l-4').style(f'border-left-color: var(--q-{meta["color"]})').on('click', lambda _, i=p.service_id: load_prompt_editor(i)):
                        with ui.row().classes('items-start gap-3 no-wrap'):
                            ui.icon(meta['icon']).classes(f'text-{meta["color"]}-500 mt-1')
                            with ui.column().classes('gap-1 flex-1 min-w-0'): 
                                # Use text-xs for description info to fit better
                                ui.label(p.name.replace("System: ", "")).classes('font-bold text-sm text-slate-700 leading-tight truncate w-full')
                                with ui.row().classes('gap-1 items-center'):
                                     # TIER BADGE
                                     tier_val = getattr(p, 'tier_override', None)
                                     badge, badge_color = "⚪", "gray"
                                     for opt in TIER_OPTIONS:
                                         if opt["value"] == tier_val:
                                             badge = opt["badge"]
                                             # Map badge to color class basically
                                             if tier_val == 1: badge_color = "green"
                                             elif tier_val == 2: badge_color = "yellow" 
                                             elif tier_val == 3: badge_color = "red"
                                             break
                                     
                                     ui.label(badge).classes('text-xs').tooltip(t('admin.prompts.tier_badge_tooltip', tier=(tier_val if tier_val else 'Default')))
                                     ui.label(meta['task']).classes('text-[10px] font-bold text-gray-400 uppercase tracking-wider')

        async def fetch_prompts():
            async with AsyncSession(server_engine) as session:
                try:
                    result = await session.exec(select(ExtractionServiceConfig))
                    all_prompts = result.all()
                    
                    # Sort Logic: By Metadata Priority first, then by Name
                    def sort_key(p):
                        meta = PROMPT_METADATA.get(p.name, {"sort_priority": 999})
                        return (meta.get("sort_priority", 999), p.name)
                    
                    current_prompts[:] = sorted(all_prompts, key=sort_key)
                    render_results()
                except Exception as e:
                    print(f"Error fetching prompts: {e}")

        # Hook up filters
        search_input.on('input', render_results)
        task_filter.on_value_change(render_results)
        phase_filter.on_value_change(render_results)

        # Initial Load
        ui.timer(0.1, fetch_prompts, once=True)
        # Show placeholder editor initially
        ui.timer(0.2, lambda: load_prompt_editor(None), once=True)

