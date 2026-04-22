from typing import List, Callable, Optional, Dict, Any
from nicegui import ui
from automatia_shared.contracts.ui_contract import OutputField, InputType

class FileTypeSelector:
    """
    Component to select file extensions for File Inputs (Folder Scan, Email Scan).
    Defines the 'files[]' output variable with filter logic.

    Can work with:
    - A step object (for flow editor context)
    - A direct config dict (for standalone page context)
    """
    COMMON_EXTENSIONS = {
        'category_docs': ['pdf', 'docx', 'txt', 'rtf'],
        'category_data': ['csv', 'xlsx', 'json', 'parquet', 'xml'],
        'category_images': ['jpg', 'png', 'jpeg', 'tiff'],
        'category_archives': ['zip', 'rar', '7z']
    }

    def __init__(self, step=None, config: Optional[Dict[str, Any]] = None, on_change: Optional[Callable] = None):
        """
        Args:
            step: Step object from flow editor (has .config attribute)
            config: Direct config dict for standalone pages
            on_change: Callback when extensions change
        """
        from client_app.app.core.state import state
        self.t = state.i18n.t
        self.step = step
        self._direct_config = config
        self.on_change = on_change
        self.selected_extensions: List[str] = self._load_extensions()

    @property
    def config(self) -> Dict[str, Any]:
        """Returns the config dict, whether from step or direct."""
        if self.step:
            return self.step.config
        return self._direct_config or {}

    def _load_extensions(self) -> List[str]:
        return self.config.get('file_extensions', [])

    def _save_extensions(self):
        self.config['file_extensions'] = self.selected_extensions

        # Also update the implicit output variable 'files[]' description to reflect the filter
        # Only for step-based context (flow editor)
        if self.step:
            files_var = OutputField(
                name='files',
                label=self.t('file_filter.output_label'),
                type=InputType.FILES,
                description=self.t('file_filter.output_desc', exts=', '.join(self.selected_extensions) if self.selected_extensions else self.t('file_filter.all'))
            )
            self.step.config['output_variables'] = [files_var.model_dump()]

        if self.on_change:
            self.on_change()

    @ui.refreshable
    def render(self):
        with ui.column().classes('w-full gap-1'):
            with ui.row().classes('w-full items-baseline gap-2 mb-1 border-b pb-1 no-wrap'):
                ui.label(self.t('file_filter.title')).classes('text-xs font-bold text-gray-700 uppercase flex-shrink-0')
                ui.label(self.t('file_filter.subtitle')).classes('text-[11px] text-gray-500 leading-tight')
                ui.element('div').classes('flex-grow')
                ui.icon('filter_alt', color='primary', size='xs').classes('flex-shrink-0')


            # Render Groups
            for group_key, exts in self.COMMON_EXTENSIONS.items():
                with ui.row().classes('w-full items-start gap-1 mb-1 p-1 bg-slate-50 rounded border border-slate-100 no-wrap'):
                    ui.label(self.t(f'file_filter.{group_key}')).classes('text-[11px] font-bold text-gray-600 pt-1 min-w-[70px]')
                    with ui.row().classes('flex-wrap gap-1'):
                        for ext in exts:
                            selected = ext in self.selected_extensions
                            ui.chip(
                                ext.upper(), 
                                icon='check' if selected else 'add',
                                color='primary' if selected else 'grey-3',
                                text_color='white' if selected else 'black',
                                on_click=lambda e, x=ext: self.toggle_extension(x)
                            ).props('clickable dense').classes('font-bold text-[10px] h-6 px-1 shadow-sm')

            # Custom Extension Input
            with ui.row().classes('w-full items-center gap-1 mt-1'):
                custom_input = ui.input(placeholder=self.t('file_filter.custom_ext')).classes('flex-1 text-xs').props('dense outlined')
                def add_custom():
                    val = custom_input.value.strip().lower().replace('.', '')
                    if val and val not in self.selected_extensions:
                        self.toggle_extension(val)
                        custom_input.value = ''
                ui.button(icon='add', on_click=add_custom).props('flat round dense color=primary size=sm')
 
            # Summary
            if self.selected_extensions:
                ui.label(f"{self.t('file_filter.selected')}{', '.join(self.selected_extensions)}").classes('text-[11px] text-green-600 font-bold mt-1')
            else:
                ui.label(self.t('file_filter.no_filters')).classes('text-[11px] text-orange-600 font-bold mt-1 italic leading-tight')

    def toggle_extension(self, ext):
        if ext in self.selected_extensions:
            self.selected_extensions.remove(ext)
        else:
            self.selected_extensions.append(ext)
        self._save_extensions()
        self.render.refresh()
