from nicegui import ui
from client_app.app.ui.main_layout import main_layout
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.markdown_viewer import MarkdownViewer
from client_app.app.core.state import state as app_state
from pathlib import Path

@ui.page('/docs')
async def docs_page_content():
    """Página dedicada para leer documentación a pantalla completa sin popups."""
    # Aggressive CSS to unlock ALL parent containers and allow natural document flow
    ui.add_head_html('''
    <style>
        /* Force unlock html and body */
        html, body {
            height: auto !important;
            overflow: auto !important;
        }
        /* Force unlock Quasar layout hierarchy */
        .q-layout, .q-page-container, .q-page {
            height: auto !important;
            min-height: none !important;
            overflow: visible !important;
        }
        /* Ensure the antigravity-scroll-lock class never blocks us */
        .antigravity-scroll-lock {
            overflow: auto !important;
        }
        /* Improved typography for the documentation card */
        .markdown-viewer-card .q-textarea__native {
            line-height: 1.6;
        }
    </style>
    ''')
    
    # Mini sidebar para maximizar el espacio de lectura
    main_layout(mini_sidebar=True)
    
    # Main container: Full-width responsive padding
    with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8'):
        if getattr(layout_manager, 'doc_atom_data', None) is None:
            ui.label("Documentación no disponible o sesión expirada.").classes('text-slate-500 italic mt-8')
            ui.button('Volver', icon='arrow_back', on_click=lambda: ui.navigate.back()).props('flat')
            return

        data = layout_manager.doc_atom_data
        atom_name = data.get('name', 'Documentación')
        doc_path = data.get('doc_path')
        status = str(data.get('status', '')).upper()
        
        # Robust Path Resolution
        path = None
        if doc_path:
            # 1. Base path relative to app installation
            root = Path(__file__).resolve().parent.parent.parent.parent
            possible_paths = [
                root / "data/storage/scripts/docs" / doc_path,
                root / "data/storage/scripts" / doc_path,
                Path("data/storage/scripts/docs") / doc_path,
                Path(doc_path)
            ]
            
            for p in possible_paths:
                if p.exists():
                    path = p
                    break
            
            # Fallback to default if none found
            if not path:
                path = root / "data/storage/scripts/docs" / doc_path

        # Header Section
        with ui.row().classes('w-full justify-between items-center mb-6 border-b pb-4'):
            with ui.row().classes('items-center gap-4'):
                ui.button(icon='arrow_back', on_click=lambda: ui.navigate.back()).props('flat round color=slate-700 bg-slate-100')
                with ui.column().classes('gap-0'):
                    ui.label(atom_name).classes('text-2xl font-bold text-slate-800 tracking-tight')
                    ui.label('Documentación Completa').classes('text-sm text-slate-500')
            
        # Unified Card Container for content - forcing overflow visible to avoid clipping
        with ui.column().classes('w-full bg-white border rounded-xl shadow-sm overflow-visible markdown-viewer-card'):
            if status == 'DRAFT':
                content = ""
                try:
                    if path and path.exists():
                        content = path.read_text(encoding='utf-8')
                except: pass
                
                # Editor mode: Borderless textarea inside the card
                # We add 'min-h-[60vh]' but ensure it can grow beyond that
                editor = ui.textarea(value=content).classes('w-full min-h-[60vh] font-mono text-base p-6 md:p-10').props('borderless autogrow')
                    
                def save_readme():
                    try:
                        if path:
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_text(editor.value, encoding='utf-8')
                            ui.notify(app_state.i18n.t('drawer.readme_saved', 'Documentación guardada'), type='positive')
                    except Exception as e:
                        ui.notify(f"Error al guardar README: {e}", type='negative')
                    
                with ui.row().classes('w-full justify-end p-4 border-t'):
                    ui.button(app_state.i18n.t('drawer.save_readme', 'Guardar Markdown'), icon='save', on_click=save_readme).props('color=primary')
            else:
                if doc_path:
                    # Viewer mode: MarkdownViewer inside the same card structure
                    MarkdownViewer(file_path=path, mode='full').render()
                else:
                    ui.label("Este elemento no tiene un archivo de documentación adjunto.").classes('text-slate-500 italic p-10')
