from nicegui import ui

def page_header(title: str, subtitle: str, classes: str = 'w-full gap-0 mb-6'):
    """
    Componente centralizado para los encabezados de página.
    Aplica una estructura de 'Título + Subtítulo' con estilo unificado.
    
    Regras:
    - Título: Sentence case, color primario, text-3xl font-bold mb-1.
    - Subtítulo: Color gris medio, text-base mb-6.
    - Sin iconos en el título.
    """
    with ui.column().classes(classes):
        # Título en Sentence case (forzado por código si es necesario, pero se espera que el llamador lo pase bien)
        # formatted_title = title[0].upper() + title[1:].lower() if title else ""
        ui.label(title).classes('text-3xl font-bold text-primary mb-1')
        
        # Subtítulo (Descripción)
        ui.label(subtitle).classes('text-slate-500 text-base')
