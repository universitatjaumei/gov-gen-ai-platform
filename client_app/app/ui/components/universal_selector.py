from nicegui import ui
from typing import List, Optional, Callable
from client_app.app.database.models import LocalAutomation

class UniversalSelector(ui.dialog):
    """
    Diálogo modal para la búsqueda y ejecución global de automatismos.
    Permite filtrar por nombre o tipo y lanzar cualquier recurso local de
    forma instantánea (Omnisearch).
    """
    def __init__(self, on_result: Optional[Callable] = None):
        """
        Inicializa el selector universal.

        Args:
            on_result: Una función de callback opcional que se invocará con el
                       item seleccionado cuando se lance un automatismo.
        """
        super().__init__()
        self.on_result = on_result
        self.items: List[LocalAutomation] = []
        self.filtered: List[LocalAutomation] = []
        self.search_term = ""

        with self, ui.card().classes('w-[600px] h-[500px] flex flex-col p-4'):
            # Header
            ui.label("Selector Universal").classes('text-xl font-bold mb-4')

            # Search
            self.search_input = ui.input(
                placeholder="Buscar automatismo...",
                on_change=self.update_filter
            ).props('autofocus outlined rounded dense icon=search').classes('w-full mb-4')

            # List Container
            self.list_container = ui.column().classes('w-full flex-1 overflow-y-auto gap-2 pr-2')

            # Footer
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button("Cerrar", on_click=self.close).props('flat')

        # Load data on open
        self.on('open', self.load_data)

    async def load_data(self):
        """
        Carga los datos de los automatismos locales desde la base de datos.

        Nota:
            Actualmente, la estrategia de sesión de base de datos para componentes
            de UI en NiceGUI es un prototipo. Se asume que los datos se cargarán
            o se simularán hasta que se defina una estrategia robusta de inyección
            de dependencias o paso de sesión.
        """
        # We need a session. Using global context or creating one.
        # Ideally passed in, but for UI component we can grab from dependency if available
        # or mock for now.
        # Assuming we can use internal logic or service pattern
        # Since this is a UI component, logic usually sits in page, but let's try to self-contain
        # using the database session pattern used elsewhere (db_session contextvar or get_db)

        # NOTE: In pure NiceGUI event loop it's tricky to get session if not passed.
        # For Prototype: We will use global_db_session if set, or just failing gracefully.

        # Real implementation: Page passes session or items.
        # Here we attempt to fetch from DB directly for "Universal" feel.
        pass # To be implemented if session strategy allows.

        # Let's assume data is passed or we simulate for now to verify UI structure
        # Or better, we query using `get_db` async generator logic if compatible
        # For simplicity in this step, I will mock the data loading or use a safer approach if possible.
        # Actually, let's look at `dashboard_page.py` usage later.
        # I'll implement the rendering logic assuming `self.items` is populated.

    def update_filter(self, e=None):
        """
        Actualiza la lista de automatismos filtrados basándose en el término de búsqueda.

        Args:
            e: Evento de NiceGUI (opcional, no utilizado directamente).
        """
        term = self.search_input.value.lower()
        self.filtered = [i for i in self.items if term in i.name.lower() or term in i.type.lower()]
        self.render_list()

    def render_list(self):
        """
        Renderiza la lista de automatismos filtrados en el contenedor de la UI.
        Muestra un mensaje si no hay resultados.
        """
        self.list_container.clear()
        with self.list_container:
            if not self.filtered:
                ui.label("No se encontraron resultados.").classes('text-gray-500 italic mx-auto mt-4')
                return

            for item in self.filtered:
                with ui.card().classes('w-full p-3 hover:bg-slate-50 cursor-pointer transition-colors border-l-4 border-slate-400').on('click', lambda i=item: self.launch_item(i)):
                    with ui.row().classes('justify-between items-center w-full'):
                        with ui.column().classes('gap-0'):
                            ui.label(item.name).classes('font-bold text-slate-800')
                            ui.label(item.type).classes('text-xs text-slate-500 uppercase tracking-wider')

                        ui.icon('play_arrow').classes('text-green-600')

    async def launch_item(self, item):
        """
        Inicia la ejecución del recurso seleccionado mediante el LauncherService.
        Notifica al usuario y cierra el selector tras invocar el callback de resultado.

        Args:
            item: El objeto LocalAutomation a ejecutar.
        """
        # Trigger launch via service
        # We need session again...
        # For Prototype UI: just notifying and closing.
        ui.notify(f"Lanzando: {item.name}...", type='info')
        if self.on_result:
             self.on_result(item)
        self.close()

    def set_items(self, items: List[LocalAutomation]):
        """
        Establece la lista de automatismos disponibles en el selector.

        Args:
            items: Una lista de objetos LocalAutomation.
        """
        self.items = items
        self.filtered = items
        self.render_list()
