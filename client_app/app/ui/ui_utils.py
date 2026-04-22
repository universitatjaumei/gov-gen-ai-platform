from nicegui import ui
import json
from typing import Any

def ui_emit(event: str, data: Any = None):
    """
    Emite un evento personalizado de JavaScript hacia el navegador.
    Facilita la comunicación entre componentes de NiceGUI que requieren
    interacción del lado del cliente o integración con componentes de Quasar.

    Args:
        event: Nombre del evento a disparar (CustomEvent).
        data: Carga útil de datos opcional (será convertida a JSON).
    """
    payload = json.dumps(data) if data is not None else 'null'
    ui.run_javascript(f"window.dispatchEvent(new CustomEvent('{event}', {{detail: {payload}}}))")
