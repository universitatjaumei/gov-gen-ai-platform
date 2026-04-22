
from nicegui import ui
import uuid
from typing import Callable, Optional

def render_extraction_wizard(on_save: Callable[[str], None], context: Optional[str] = None):
    """
    Wizard simplificado para crear config de extracción.
    """
    # State
    config_name = ui.input("Nombre del Extractor").classes('w-full')
    doc_type = ui.select(['Factura', 'Albarán', 'Nómina', 'Genérico'], label="Tipo Documento").classes('w-full')
    
    if context:
        ui.label(f"Contexto Detectado: {context}").classes('text-xs text-blue-500 mb-2')
    
    # Fields builder (Simplified)
    fields = []
    
    fields_container = ui.column().classes('w-full border p-2 mt-2')
    
    def add_field():
        fields.append({"name": f"Campo {len(fields)+1}", "type": "text"})
        refresh_fields()
        
    def refresh_fields():
        fields_container.clear()
        with fields_container:
            for i, f in enumerate(fields):
                with ui.row().classes('w-full gap-2'):
                    ui.input(value=f['name'], on_change=lambda e, i=i: fields[i].update({'name': e.value})).props('dense')
                    ui.select(['text', 'number', 'date'], value=f['type'], on_change=lambda e, i=i: fields[i].update({'type': e.value})).props('dense')

    with ui.row():
        ui.button('Añadir Campo', icon='add', on_click=add_field).props('flat dense')
    
    refresh_fields()

    def save():
        if not config_name.value:
            ui.notify('Nombre requerido', type='warning')
            return
            
        # Mock creation logic -> In real app, call ExtractionService.create_config()
        # For this prototype, generate UUID
        new_id = str(uuid.uuid4())
        
        ui.notify(f"Extractor '{config_name.value}' creado (ID: {new_id})")
        on_save(new_id)

    ui.separator().classes('my-4')
    with ui.row().classes('w-full justify-end'):
        ui.button('Guardar y Vincular', on_click=save).props('color=primary')
