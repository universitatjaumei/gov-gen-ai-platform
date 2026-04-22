from nicegui import ui
from automatia_shared.contracts.ui_contract import UIContract, InputDefinition, InputType
from client_app.app.ui.components.dynamic_form import DynamicExecutorForm

@ui.page('/test_form')
def test_form_page():
    ui.label("Prueba de DynamicExecutorForm").classes('text-2xl font-bold mb-4')
    
    # 1. Definir Contrato de Prueba
    contract = UIContract(inputs=[
        InputDefinition(name="project_name", label="Nombre del Proyecto", type=InputType.STR, description="Nombre interno"),
        InputDefinition(name="max_retries", label="Reintentos", type=InputType.INT, default=3),
        InputDefinition(name="is_production", label="Modo Producción", type=InputType.BOOL, default=False),
        InputDefinition(name="environment", label="Entorno", type=InputType.SELECT, options=["DEV", "STAGING", "PROD"]),
        InputDefinition(name="source_file", label="Archivo Fuente (PDF)", type=InputType.FILE, required=True),
        InputDefinition(name="api_key", label="API Key", type=InputType.SECRET, required=False)
    ])

    # 2. Callback de Envío
    def on_submit(data):
        with ui.dialog() as dialog, ui.card():
            ui.label("Datos Enviados y Validados:")
            ui.json_editor({'content': {'json': data}}, )
            ui.button("Cerrar", on_click=dialog.close)
        dialog.open()

    # 3. Renderizar Formulario
    with ui.column().classes('w-full max-w-2xl mx-auto'):
        DynamicExecutorForm(contract, on_submit=on_submit)
        
    ui.button("Volver al Dashboard", on_click=lambda: ui.open('/')).classes('mt-8')
