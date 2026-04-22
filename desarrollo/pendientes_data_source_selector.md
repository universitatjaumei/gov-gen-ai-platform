# Pendientes: DataSourceSelector y manejo de fuentes de datos

Este documento registra los aspectos pendientes identificados durante la revisión del manejo de fuentes de datos en las distintas páginas de la aplicación.

## Fecha: 2026-02-27

---

## Resumen de correcciones aplicadas

| Página | Estado | Descripción |
|--------|--------|-------------|
| `etl_page.py` | ✅ Corregido | `source_file=None` para flow_step - se guarda preview a archivo temporal |
| `graphics_page.py` | ✅ OK | Usa DataFrame directamente, no archivos |
| `extraction_page.py` | ✅ Corregido | Ahora extrae archivos PDF del preview de folder_scan |
| `anonymizer_page.py` | ✅ Corregido | Ahora maneja file_content para uploads y preview_data para flow_step |

---

## Pendientes a revisar en próximas sesiones

### 1. SMTP - Adjuntos no implementados

**Archivo:** `client_app/app/ui/smtp_page.py`

**Problema:**
El DataSourceSelector se renderiza para seleccionar adjuntos (líneas 406-412), pero la función `handle_send_test()` (línea 224) no utiliza `exec_state.attachment_source` para nada. El envío de emails con adjuntos NO está implementado.

**Código actual:**
```python
# Línea 397-404: Se guarda la selección pero no se usa
elif selection.source_type == 'flow_step':
    ui.notify(f'Adjunto del paso: {selection.step_name}', type='info')

# Línea 248-254: El envío no incluye adjuntos
message_id = await asyncio.to_thread(
    sender.send,
    from_addr=creds['user'],
    to_addrs=[exec_state.to],
    subject=exec_state.subject,
    body=exec_state.body,
    html=False
    # ❌ No hay parámetro de attachments
)
```

**Acción requerida:**
1. Modificar `EmailSender.send()` para aceptar adjuntos
2. Procesar `exec_state.attachment_source` según su tipo:
   - `manual`: usar `file_content` directamente
   - `flow_step`: obtener archivo del preview_data (path del paso anterior)
   - `catalog`: obtener datos de ejemplo o path del átomo
3. Pasar adjuntos al método de envío

---

### 2. custom_script_page.py - Por revisar

**Archivo:** `client_app/app/ui/custom_script_page.py`

**Estado:** No revisado en detalle

**Acción requerida:**
Verificar si el DataSourceSelector funciona correctamente para todos los source_types (manual, catalog, flow_step).

---

### 3. pdf_tools_atom_page.py - Por revisar

**Archivo:** `client_app/app/ui/pdf_tools_atom_page.py`

**Estado:** No revisado en detalle

**Acción requerida:**
Verificar que el manejo de archivos PDF funcione correctamente cuando vienen de flow_step (ej: folder_scan).

---

### 4. rpa_page.py - Por revisar

**Archivo:** `client_app/app/ui/rpa_page.py`

**Estado:** No revisado en detalle

**Acción requerida:**
Verificar el uso del DataSourceSelector y si requiere correcciones similares.

---

## Notas técnicas

### Patrón correcto para manejar DataSourceSelector

```python
# 1. Importar
from client_app.app.ui.components.data_source_selector import (
    render_data_source_selector,
    DataSourceSelection,
    DataSourceSelectorState  # ← Importante para acceder a preview_data
)

# 2. Añadir selector_state al estado de la página
class PageState:
    def __init__(self):
        self.data_source: Optional[DataSourceSelection] = None
        self.data_source_selector_state = DataSourceSelectorState()

# 3. Pasar selector_state al renderizar
render_data_source_selector(
    consumer_type=StepType.XXX,
    on_source_selected=handle_selection,
    flow_context=state.flow_context,
    selector_state_override=page_state.data_source_selector_state  # ← Importante
)

# 4. En el handler, manejar todos los tipos
async def handle_selection(selection: DataSourceSelection):
    if selection.source_type == 'manual' and selection.file_content:
        # Leer desde file_content (bytes)
        df = pd.read_csv(io.BytesIO(selection.file_content))

    elif selection.source_type == 'flow_step':
        # Obtener del preview_data (requiere que usuario haya cargado datos)
        selector_state = page_state.data_source_selector_state
        if selector_state.preview_data:
            df = selector_state.preview_data.to_dataframe()

    elif selection.source_type == 'catalog':
        # Similar a flow_step
        selector_state = page_state.data_source_selector_state
        if selector_state.preview_data:
            df = selector_state.preview_data.to_dataframe()
```

### Para archivos (no DataFrames)

Cuando el consumidor necesita archivos (como extraction con PDFs):

```python
def extract_files_from_flow_step():
    """Extrae lista de archivos del preview_data (ej: folder_scan)."""
    selector_state = design_state.data_source_selector_state
    if not selector_state.preview_data:
        return []

    preview = selector_state.preview_data
    files = []

    # folder_scan devuelve columna 'path' con rutas de archivos
    if 'path' in preview.columns:
        for row in preview.rows:
            file_path = row.get('path', '')
            if file_path and file_path.lower().endswith('.pdf'):
                files.append(file_path)

    return files
```
