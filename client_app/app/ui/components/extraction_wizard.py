"""
Wizard simplificado para crear configuraciones de extracción desde el editor de flujos.
Prompt 5.3 del plan de refactorización.

Proporciona un formulario para crear configuraciones de extracción que puede renderizarse
dentro de un drawer sin salir del editor de flujos.
"""
import uuid
from typing import Callable, Optional, List, Dict, Any
from nicegui import ui


async def render_extraction_wizard(
    on_save: Callable[[str], None],
    on_cancel: Optional[Callable[[], None]] = None
):
    """
    Renderiza un asistente (wizard) de 4 pasos para configurar extracciones de documentos.
    
    Flujo:
    1. Información: Nombre y tipo de documento (Factura, Albarán, etc.).
    2. Campos: Definición de claves JSON a extraer y su obligatoriedad.
    3. Probar: Carga de ejemplo y verificación real mediante el servicio de extracción.
    4. Guardar: Persistencia de la configuración en el ExtractionServiceClient.

    Args:
        on_save: Callback que recibe el ID de la nueva configuración guardada.
        on_cancel: Callback opcional para gestionar la interrupción del asistente.
    """
    # Estado del wizard
    wizard_state = {
        'step': 1,
        'name': '',
        'description': '',
        'document_type': 'factura',
        'fields': [],  # Lista de campos a extraer
        'example_file': None,
        'example_text': '',
        'test_result': None,
        'testing': False,
        'saving': False,
        'error': None,
    }

    # Campos predefinidos por tipo de documento
    PRESET_FIELDS = {
        'factura': [
            {'name': 'numero_factura', 'description': 'Número de factura', 'required': True},
            {'name': 'fecha', 'description': 'Fecha de emisión', 'required': True},
            {'name': 'proveedor', 'description': 'Nombre del proveedor', 'required': True},
            {'name': 'importe_total', 'description': 'Importe total con IVA', 'required': True},
            {'name': 'base_imponible', 'description': 'Base imponible', 'required': False},
            {'name': 'iva', 'description': 'Importe del IVA', 'required': False},
        ],
        'albaran': [
            {'name': 'numero_albaran', 'description': 'Número de albarán', 'required': True},
            {'name': 'fecha', 'description': 'Fecha de entrega', 'required': True},
            {'name': 'cliente', 'description': 'Nombre del cliente', 'required': True},
            {'name': 'direccion_entrega', 'description': 'Dirección de entrega', 'required': False},
            {'name': 'productos', 'description': 'Lista de productos', 'required': True},
        ],
        'contrato': [
            {'name': 'partes', 'description': 'Partes del contrato', 'required': True},
            {'name': 'fecha_firma', 'description': 'Fecha de firma', 'required': True},
            {'name': 'objeto', 'description': 'Objeto del contrato', 'required': True},
            {'name': 'duracion', 'description': 'Duración del contrato', 'required': False},
            {'name': 'importe', 'description': 'Importe del contrato', 'required': False},
        ],
        'custom': [],
    }

    @ui.refreshable
    def wizard_content():
        step = wizard_state['step']

        # Indicador de pasos
        with ui.row().classes('w-full justify-center gap-4 mb-4'):
            for i, label in enumerate(['Información', 'Campos', 'Probar', 'Guardar'], 1):
                is_current = i == step
                is_completed = i < step

                if is_completed:
                    color = 'green'
                elif is_current:
                    color = 'primary'
                else:
                    color = 'grey'

                with ui.column().classes('items-center'):
                    ui.badge(str(i), color=color).props('rounded')
                    ui.label(label).classes(f'text-xs {"font-bold" if is_current else ""}')

        ui.separator().classes('mb-4')

        if step == 1:
            render_step_info()
        elif step == 2:
            render_step_fields()
        elif step == 3:
            render_step_test()
        elif step == 4:
            render_step_save()

    def render_step_info():
        """Paso 1: Información básica de la configuración."""
        ui.label('Información de la Configuración').classes('text-lg font-bold mb-2')
        ui.label('Define el nombre y tipo de documento a extraer').classes('text-sm text-gray-600 mb-4')

        # Nombre
        ui.label('Nombre de la configuración *').classes('font-bold text-sm')
        ui.input(
            value=wizard_state['name'],
            placeholder='Ej: Facturas Proveedor XYZ',
            on_change=lambda e: wizard_state.update({'name': e.value})
        ).classes('w-full mb-3').props('outlined dense')

        # Descripción
        ui.label('Descripción').classes('font-bold text-sm')
        ui.textarea(
            value=wizard_state['description'],
            placeholder='Describe qué tipo de documentos procesará esta configuración...',
            on_change=lambda e: wizard_state.update({'description': e.value})
        ).classes('w-full mb-3').props('outlined rows=2')

        # Tipo de documento
        ui.label('Tipo de documento').classes('font-bold text-sm')
        ui.select(
            options={
                'factura': 'Factura',
                'albaran': 'Albarán',
                'contrato': 'Contrato',
                'custom': 'Personalizado',
            },
            value=wizard_state['document_type'],
            on_change=lambda e: handle_doc_type_change(e.value)
        ).classes('w-full mb-4').props('outlined dense')

        # Hint sobre campos predefinidos
        if wizard_state['document_type'] != 'custom':
            preset = PRESET_FIELDS.get(wizard_state['document_type'], [])
            with ui.row().classes('items-center gap-2 p-2 bg-blue-50 rounded'):
                ui.icon('info', color='blue')
                ui.label(f'Se cargarán {len(preset)} campos predefinidos para este tipo de documento').classes('text-sm text-blue-700')

        # Botones
        with ui.row().classes('w-full justify-between mt-4'):
            ui.button('Cancelar', on_click=lambda: on_cancel() if on_cancel else None).props('flat color=grey')

            def next_step():
                if not wizard_state['name'].strip():
                    ui.notify('El nombre es obligatorio', type='warning')
                    return
                # Cargar campos predefinidos si no hay
                if not wizard_state['fields']:
                    wizard_state['fields'] = [
                        dict(f) for f in PRESET_FIELDS.get(wizard_state['document_type'], [])
                    ]
                wizard_state['step'] = 2
                wizard_content.refresh()

            ui.button('Siguiente', icon='arrow_forward', on_click=next_step).props('color=primary')

    def handle_doc_type_change(doc_type: str):
        wizard_state['document_type'] = doc_type
        # Resetear campos al cambiar tipo
        wizard_state['fields'] = [
            dict(f) for f in PRESET_FIELDS.get(doc_type, [])
        ]
        wizard_content.refresh()

    def render_step_fields():
        """Paso 2: Definir campos a extraer."""
        ui.label('Campos a Extraer').classes('text-lg font-bold mb-2')
        ui.label('Define los datos que quieres extraer del documento').classes('text-sm text-gray-600 mb-4')

        fields = wizard_state['fields']

        # Lista de campos
        if fields:
            with ui.column().classes('w-full gap-2 mb-4'):
                for idx, field in enumerate(fields):
                    with ui.card().classes('w-full p-3 bg-gray-50'):
                        with ui.row().classes('w-full items-center gap-2'):
                            # Nombre del campo
                            ui.input(
                                value=field.get('name', ''),
                                placeholder='nombre_campo',
                                on_change=lambda e, i=idx: update_field(i, 'name', e.value)
                            ).classes('flex-1').props('outlined dense label="Nombre"')

                            # Descripción
                            ui.input(
                                value=field.get('description', ''),
                                placeholder='Descripción del campo',
                                on_change=lambda e, i=idx: update_field(i, 'description', e.value)
                            ).classes('flex-1').props('outlined dense label="Descripción"')

                            # Obligatorio
                            ui.checkbox(
                                'Req.',
                                value=field.get('required', False),
                                on_change=lambda e, i=idx: update_field(i, 'required', e.value)
                            ).tooltip('Campo obligatorio')

                            # Eliminar
                            ui.button(
                                icon='delete',
                                on_click=lambda i=idx: remove_field(i)
                            ).props('flat dense color=red')
        else:
            with ui.row().classes('items-center gap-2 p-4 bg-gray-50 rounded'):
                ui.icon('info', color='grey')
                ui.label('No hay campos definidos. Añade al menos uno.').classes('text-sm text-gray-500')

        # Botón añadir campo
        ui.button(
            'Añadir campo',
            icon='add',
            on_click=add_field
        ).props('flat color=primary')

        # Botones navegación
        with ui.row().classes('w-full justify-between mt-6'):
            def prev_step():
                wizard_state['step'] = 1
                wizard_content.refresh()

            ui.button('Anterior', icon='arrow_back', on_click=prev_step).props('flat')

            def next_step():
                if not wizard_state['fields']:
                    ui.notify('Añade al menos un campo a extraer', type='warning')
                    return
                # Verificar que todos los campos tienen nombre
                for f in wizard_state['fields']:
                    if not f.get('name', '').strip():
                        ui.notify('Todos los campos deben tener un nombre', type='warning')
                        return
                wizard_state['step'] = 3
                wizard_content.refresh()

            ui.button('Siguiente', icon='arrow_forward', on_click=next_step).props('color=primary')

    def update_field(idx: int, key: str, value):
        if idx < len(wizard_state['fields']):
            wizard_state['fields'][idx][key] = value

    def add_field():
        wizard_state['fields'].append({
            'name': '',
            'description': '',
            'required': False
        })
        wizard_content.refresh()

    def remove_field(idx: int):
        if idx < len(wizard_state['fields']):
            wizard_state['fields'].pop(idx)
            wizard_content.refresh()

    def render_step_test():
        """Paso 3: Probar extracción con documento de ejemplo."""
        ui.label('Probar Extracción').classes('text-lg font-bold mb-2')
        ui.label('Sube un documento de ejemplo para verificar la configuración').classes('text-sm text-gray-600 mb-4')

        # Resumen de campos
        with ui.card().classes('w-full p-3 bg-blue-50 mb-4'):
            ui.label(f'Configuración: {wizard_state["name"]}').classes('font-bold text-blue-800')
            ui.label(f'{len(wizard_state["fields"])} campos a extraer:').classes('text-sm text-gray-600')
            with ui.row().classes('flex-wrap gap-1 mt-2'):
                for f in wizard_state['fields'][:8]:
                    icon = 'check_circle' if f.get('required') else 'radio_button_unchecked'
                    ui.chip(f.get('name', ''), icon=icon).props('dense size=sm')
                if len(wizard_state['fields']) > 8:
                    ui.chip(f'+{len(wizard_state["fields"]) - 8} más').props('dense size=sm color=grey')

        # Subir archivo o pegar texto
        ui.label('Documento de prueba (opcional)').classes('font-bold text-sm')

        with ui.tabs().classes('w-full') as tabs:
            file_tab = ui.tab('Subir archivo')
            text_tab = ui.tab('Pegar texto')

        with ui.tab_panels(tabs, value=file_tab).classes('w-full'):
            with ui.tab_panel(file_tab):
                ui.upload(
                    label='Arrastra un PDF aquí',
                    on_upload=handle_file_upload,
                    auto_upload=True
                ).classes('w-full').props('accept=".pdf,.png,.jpg,.jpeg"')

                if wizard_state.get('example_file'):
                    with ui.row().classes('items-center gap-2 mt-2'):
                        ui.icon('check_circle', color='green')
                        ui.label(f'Archivo cargado: {wizard_state["example_file"]}').classes('text-sm text-green-700')

            with ui.tab_panel(text_tab):
                ui.textarea(
                    value=wizard_state.get('example_text', ''),
                    placeholder='Pega aquí el texto del documento de ejemplo...',
                    on_change=lambda e: wizard_state.update({'example_text': e.value})
                ).classes('w-full').props('outlined rows=6')

        # Resultado del test
        if wizard_state['testing']:
            with ui.row().classes('w-full justify-center mt-4'):
                ui.spinner('dots', size='lg')
                ui.label('Probando extracción...').classes('ml-2')
        elif wizard_state['test_result']:
            result = wizard_state['test_result']
            if result.get('success'):
                with ui.card().classes('w-full p-3 bg-green-50 border border-green-200 mt-4'):
                    ui.label('✓ Extracción exitosa').classes('font-bold text-green-800')
                    with ui.scroll_area().classes('w-full max-h-40'):
                        ui.json_editor({'content': {'json': result.get('data', {})}}).classes('w-full')
            else:
                with ui.card().classes('w-full p-3 bg-red-50 border border-red-200 mt-4'):
                    ui.label('✗ Error en extracción').classes('font-bold text-red-800')
                    ui.label(result.get('error', 'Error desconocido')).classes('text-sm text-red-700')

        # Botones
        with ui.row().classes('w-full justify-between mt-6'):
            def prev_step():
                wizard_state['step'] = 2
                wizard_state['test_result'] = None
                wizard_content.refresh()

            ui.button('Anterior', icon='arrow_back', on_click=prev_step).props('flat')

            with ui.row().classes('gap-2'):
                async def run_test():
                    if not wizard_state.get('example_file') and not wizard_state.get('example_text'):
                        ui.notify('Sube un archivo o pega texto para probar', type='warning')
                        return

                    wizard_state['testing'] = True
                    wizard_state['test_result'] = None
                    wizard_content.refresh()

                    try:
                        # Simular test de extracción (en producción conectaría al servicio real)
                        await simulate_extraction_test()
                    except Exception as e:
                        wizard_state['test_result'] = {'success': False, 'error': str(e)}
                    finally:
                        wizard_state['testing'] = False
                        wizard_content.refresh()

                ui.button(
                    'Probar',
                    icon='science',
                    on_click=run_test
                ).props('color=purple')

                def next_step():
                    wizard_state['step'] = 4
                    wizard_content.refresh()

                ui.button('Siguiente', icon='arrow_forward', on_click=next_step).props('color=primary')

    async def handle_file_upload(e):
        """Maneja la subida de archivo de ejemplo."""
        wizard_state['example_file'] = e.name
        # En producción, guardaríamos el archivo temporalmente
        ui.notify(f'Archivo {e.name} cargado', type='positive')
        wizard_content.refresh()

    async def simulate_extraction_test():
        """Simula un test de extracción (placeholder)."""
        import asyncio
        await asyncio.sleep(1.5)

        # Simular resultado basado en los campos definidos
        mock_data = {}
        for f in wizard_state['fields']:
            field_name = f.get('name', '')
            if 'fecha' in field_name.lower():
                mock_data[field_name] = '15/01/2025'
            elif 'importe' in field_name.lower() or 'total' in field_name.lower():
                mock_data[field_name] = '1.234,56 €'
            elif 'numero' in field_name.lower():
                mock_data[field_name] = 'F-2025-001234'
            else:
                mock_data[field_name] = f'[Valor de {field_name}]'

        wizard_state['test_result'] = {
            'success': True,
            'data': mock_data
        }

    def render_step_save():
        """Paso 4: Revisar y guardar."""
        ui.label('Guardar Configuración').classes('text-lg font-bold mb-2')
        ui.label('Revisa los detalles y guarda la configuración').classes('text-sm text-gray-600 mb-4')

        # Resumen completo
        with ui.card().classes('w-full p-4 bg-blue-50 border border-blue-200 mb-4'):
            ui.label(wizard_state['name']).classes('text-xl font-bold text-blue-800')
            if wizard_state['description']:
                ui.label(wizard_state['description']).classes('text-sm text-gray-600 mt-1')

            ui.separator().classes('my-3')

            with ui.row().classes('gap-4'):
                with ui.column().classes('gap-1'):
                    ui.label('Tipo de documento').classes('text-xs text-gray-500')
                    ui.chip(wizard_state['document_type'].capitalize(), icon='description').props('dense')

                with ui.column().classes('gap-1'):
                    ui.label('Campos').classes('text-xs text-gray-500')
                    ui.chip(f'{len(wizard_state["fields"])} campos', icon='list').props('dense')

            ui.separator().classes('my-3')

            ui.label('Campos a extraer:').classes('font-bold text-sm text-blue-700')
            with ui.column().classes('gap-1 mt-2'):
                for f in wizard_state['fields']:
                    icon = 'check_circle' if f.get('required') else 'radio_button_unchecked'
                    color = 'green' if f.get('required') else 'grey'
                    with ui.row().classes('items-center gap-2'):
                        ui.icon(icon, color=color).classes('text-sm')
                        ui.label(f.get('name', '')).classes('font-mono text-sm')
                        if f.get('description'):
                            ui.label(f"- {f.get('description')}").classes('text-xs text-gray-500')

        # Advertencia
        with ui.row().classes('items-center gap-2 p-2 bg-orange-50 rounded mb-4'):
            ui.icon('info', color='orange')
            ui.label('La configuración estará disponible inmediatamente en el selector.').classes('text-xs text-orange-700')

        # Botones
        with ui.row().classes('w-full justify-between mt-4'):
            def prev_step():
                wizard_state['step'] = 3
                wizard_content.refresh()

            ui.button('Anterior', icon='arrow_back', on_click=prev_step).props('flat')

            if wizard_state['saving']:
                ui.spinner('dots')
            else:
                async def save_config():
                    wizard_state['saving'] = True
                    wizard_content.refresh()

                    try:
                        from client_app.app.services.extraction_service import ExtractionServiceClient

                        # Generar ID único
                        service_id = f"user_{uuid.uuid4().hex[:8]}"

                        # Construir schema esperado
                        expected_schema = {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                        for f in wizard_state['fields']:
                            fname = f.get('name', '')
                            expected_schema["properties"][fname] = {
                                "type": "string",
                                "description": f.get('description', '')
                            }
                            if f.get('required'):
                                expected_schema["required"].append(fname)

                        config_data = {
                            'service_id': service_id,
                            'name': wizard_state['name'],
                            'description': wizard_state['description'] or f"Configuración para {wizard_state['document_type']}",
                            'expected_schema': expected_schema,
                        }

                        service = ExtractionServiceClient()
                        await service.save_user_config(config_data)

                        ui.notify(f'Configuración "{wizard_state["name"]}" creada correctamente', type='positive')

                        # Llamar callback con el ID
                        on_save(service_id)

                    except Exception as e:
                        ui.notify(f'Error al guardar: {str(e)}', type='negative')
                        wizard_state['saving'] = False
                        wizard_content.refresh()

                ui.button(
                    'Guardar Configuración',
                    icon='save',
                    on_click=save_config
                ).props('color=green')

    # Renderizar contenido inicial
    wizard_content()
