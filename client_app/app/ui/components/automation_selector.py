from nicegui import ui
from typing import Callable, Optional
from client_app.app.database.db import get_db
from client_app.app.database.models import LocalAutomation
from sqlmodel import select

async def render_automation_selector(automation_type: Optional[str], on_change: Callable, value: Optional[str] = None, create_label: str = '--- Crear Nuevo ---', label: Optional[str] = None):
    """
    Renders a standardized selector for automations filtered by type.
    
    Args:
        automation_type: The type of automation to filter by (e.g. 'pdf_extractor', 'python_script').
                         If None, it might list all (though specific logic for None might be needed).
        on_change: Callback function that receives the selected automation ID (or None).
        value: Currently selected ID (for state persistence).
        create_label: Label for the create new option.
        label: Custom label for the selector title (e.g. "Mis Scripts Personalizados").
    """
    async with get_db() as session:
        statement = select(LocalAutomation)
        if automation_type:
            statement = statement.where(LocalAutomation.type == automation_type)
        
        results = await session.exec(statement)
        automations = results.all()

    options = {None: create_label}
    for a in automations:
        options[a.id] = f"{a.name} ({a.local_status})"

    with ui.row().classes('w-full items-center justify-between bg-blue-50 p-4 rounded-lg mb-6'):
        if label:
            label_text = label
        else:
            label_text = f"Biblioteca de {automation_type.upper()}" if automation_type else "Biblioteca de Automatismos"
            
        ui.label(label_text).classes('font-bold text-lg text-slate-700')
        
        ui.select(
            options=options, 
            value=value, 
            on_change=lambda e: on_change(e.value)
        ).classes('w-64').props('outlined dense bg-white')
