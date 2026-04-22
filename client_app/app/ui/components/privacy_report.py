from nicegui import ui
from typing import Dict

def render_privacy_report(stats: Dict[str, int]):
    """
    Dibuja una tarjeta estética con el resumen de datos protegidos.
    """
    if not stats or sum(stats.values()) == 0:
        return

    # Mapeo de iconos y etiquetas amigables
    TYPE_MAP = {
        "DNI": {"icon": "badge", "label": "Números de DNI (Anonimizados mediante máscara AEPD)"},
        "NIE": {"icon": "badge", "label": "Números de NIE (Anonimizados mediante máscara AEPD)"},
        "PERSON_NAME": {"icon": "person", "label": "Nombres de personas (Sustituidos por identidades aleatorias)"},
        "EMAIL": {"icon": "email", "label": "Direcciones de Email (Sustituidos por correos sintéticos)"},
        "PHONE": {"icon": "phone", "label": "Teléfonos (Anonimizados mediante máscara)"},
        "IBAN": {"icon": "account_balance", "label": "Cuentas Bancarias (IBAN sintético generado)"},
        "ADDRESS": {"icon": "home", "label": "Direcciones postales (Sustituidas por direcciones ficticias)"},
        "ORGANIZATION": {"icon": "business", "label": "Nombres de Empresas (Sustituidos por nombres sintéticos)"},
        "CREDIT_CARD": {"icon": "payment", "label": "Tarjetas de Crédito (Enmascaradas)"},
        "NSS": {"icon": "work", "label": "Números de Seguridad Social"},
        "DATE": {"icon": "calendar_today", "label": "Fechas (Ofuscadas)"},
        "POSTAL_CODE": {"icon": "map", "label": "Códigos Postales"}
    }

    with ui.card().classes('w-full p-6 border-l-8 border-green-600 shadow-lg bg-green-50'):
        with ui.row().classes('items-center gap-3 mb-4'):
            ui.icon('shield', color='green-700', size='2rem')
            ui.label('🛡️ Informe de Protección de Datos').classes('text-xl font-bold text-green-800')
        
        ui.label('Durante este proceso, se han protegido los siguientes datos sensibles:').classes('text-slate-700 mb-4 italic')
        
        with ui.column().classes('w-full gap-3'):
            for entity_type, count in stats.items():
                if count == 0: continue
                
                info = TYPE_MAP.get(entity_type, {"icon": "info", "label": f"Datos de tipo {entity_type}"})
                
                with ui.row().classes('items-center gap-4 p-2 bg-white rounded-lg border border-green-100'):
                    ui.icon(info['icon'], color='green-600').classes('text-xl')
                    with ui.column().classes('gap-0'):
                        ui.label(f"{count} {info['label']}").classes('text-sm font-semibold text-slate-800')
        
        ui.separator().classes('my-4')
        
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('Soberanía de datos garantizada: Estos datos fueron sustituidos por valores sintéticos antes de la consulta a la IA.').classes('text-xs text-green-700 font-medium max-w-[70%]')
            with ui.row().classes('items-center gap-1'):
                ui.label('Resultado:').classes('text-xs font-bold text-green-900')
                ui.badge('0% PII ENVIADA', color='green-700').classes('text-xs font-bold')
