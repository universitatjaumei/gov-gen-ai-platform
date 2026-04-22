"""
Menu Configuration - Estructura de Navegación de AutomatIA

Define la estructura del menú lateral usando la nueva taxonomía de 4 capas:
- Disparadores (Triggers)
- Entradas (Inputs)
- Procesadores (Processors)
- Salidas (Outputs)

Refactorizado como parte de la Fase 3 del Plan de Taxonomía.
"""
from client_app.app.core.state import state


def get_menu_structure():
    """
    Retorna la estructura del menú lateral de navegación.

    Organización:
    - Dashboard
    - Flujos (gestión central de automatizaciones)
    - 4 categorías funcionales de átomos
    - Configuración (incluye Paquetes como pestaña)
    """
    t = state.i18n.t
    return {
        # === INICIO ===
        'dashboard': {
            'route': '/',
            'icon': 'dashboard',
            'label': t('menu_dashboard')
        },

        # === GESTIÓN DE FLUJOS ===
        'flujos': {
            'type': 'expansion',
            'icon': 'account_tree',
            'label': t('menu_flows'),
            'items': [
                {'route': '/flows', 'icon': 'account_tree', 'label': t('menu_flows_list', 'Gestor de flujos')},
                {'route': '/atoms', 'icon': 'category', 'label': t('menu_atoms', 'Catálogo de acciones')},
                {'route': '/triggers', 'icon': 'bolt', 'label': t('gallery.trigger', 'Disparadores')}
            ]
        },

        # === ENTRADAS (Inputs) ===
        'entradas': {
            'type': 'expansion',
            'icon': 'login',
            'label': t('gallery.input', 'Entradas'),
            'items': [
                {'route': '/inputs/sql', 'icon': 'storage', 'label': t('menu_items.sql_query', 'Consulta SQL')},
                {'route': '/inputs/api', 'icon': 'api', 'label': t('menu_items.api_fetch', 'API fetch')},
                {'route': '/inputs/folder-scan', 'icon': 'folder_open', 'label': t('menu_items.folder_scan', 'Escaneo carpeta')},
                {'route': '/inputs/email-scan', 'icon': 'attach_email', 'label': t('menu_items.email_collector', 'Recolector email')},
            ]
        },

        # === PROCESADORES (Processors) ===
        'procesadores': {
            'type': 'expansion',
            'icon': 'psychology',
            'label': t('gallery.processor', 'Procesadores'),
            'items': [
                {'route': '/documents', 'icon': 'description', 'label': t('menu_items.documents', 'Extracción PDF')},
                {'route': '/rpa', 'icon': 'travel_explore', 'label': t('menu_items.rpa', 'RPA web')},
                {'route': '/etl', 'icon': 'transform', 'label': t('menu_items.etl', 'Transformación ETL')},
                {'route': '/custom-scripts', 'icon': 'code', 'label': t('menu_items.custom_script', 'Script personalizado')},
                {'route': '/llm-process', 'icon': 'psychology', 'label': t('menu_items.llm_process', 'Procesamiento LLM')},
                {'route': '/graphics', 'icon': 'bar_chart', 'label': t('menu_items.graphics', 'Gráficos')},
                {'route': '/reports/designer', 'icon': 'description', 'label': t('menu_items.report_generator', 'Generador informes')},
            ]
        },

        # === SALIDAS (Outputs) ===
        'salidas': {
            'type': 'expansion',
            'icon': 'logout',
            'label': t('gallery.output', 'Salidas'),
            'items': [
                {'route': '/connections/smtp', 'icon': 'send', 'label': t('menu_items.smtp_send', 'Email (SMTP)')},
                {'route': '/outputs/sql', 'icon': 'storage', 'label': t('menu_items.sql_insert', 'SQL insert')},
                {'route': '/inputs/api', 'icon': 'cloud_upload', 'label': t('menu_items.api_post', 'API (POST)')},
                {'route': '/outputs/archive', 'icon': 'save_alt', 'label': t('menu_items.archive_result', 'Archivar resultado')},
            ]
        },

        # === UTILIDADES (Direct-use tools) ===
        'utilidades': {
            'type': 'expansion',
            'icon': 'handyman',
            'label': t('gallery.utility', 'Utilidades'),
            'items': [
                {'route': '/utilities/pdf-tools', 'icon': 'picture_as_pdf', 'label': t('gallery.modules.pdf_tools', 'Herramientas PDF')},
                {'route': '/utilities/anonymizer', 'icon': 'security', 'label': t('menu_items.anonymizer', 'Anonimizar')},
            ]
        },

        # === CONFIGURACIÓN ===
        'config': {
            'route': '/config',
            'icon': 'settings',
            'label': t('menu_config')
        },
    }
