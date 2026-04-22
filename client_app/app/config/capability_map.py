from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from automatia_shared.enums import StepType

@dataclass
class AtomCapability:
    """
    Define las capacidades de UI para un tipo de átomo en el Drawer de Diseño.
    Permite configurar qué pasos se muestran, si tiene variables de salida,
    y la acción principal.
    """
    steps: List[Dict[str, Any]]  # Lista de pasos del wizard [{'name': str, 'hint': str, ...}]
    has_stepper: bool = True     # Si debe mostrar la pestaña/sección de ajustes
    has_variables: bool = True   # Si debe mostrar la pestaña/sección de variables
    variables_view_mode: str = 'select_inputs'  # 'select_inputs' or 'define_outputs'
    primary_action_label: str = "Sellar y Guardar"
    primary_action_icon: str = "verified"
    primary_action_color: str = "indigo"
    contextual_help: List[Dict[str, str]] = field(default_factory=list) # [{'title': str, 'message': str, 'icon': str}]

# Configuración por defecto para átomos estándar
DEFAULT_CAPABILITY = AtomCapability(
    steps=[
        {'name': 'Descripción', 'hint': 'Define qué debe hacer', 'current': True, 'completed': False},
        {'name': 'Generación', 'hint': 'Código generado por IA', 'current': False, 'completed': False},
        {'name': 'Validación', 'hint': 'Prueba y sella', 'current': False, 'completed': False},
    ],
    has_stepper=True,
    has_variables=True,
    variables_view_mode='select_inputs',
    primary_action_label="Sellar y Guardar",
    primary_action_icon="verified",
    primary_action_color="indigo"
)

# Mapa de capacidades específicas
CAPABILITY_MAP: Dict[StepType, AtomCapability] = {
    
    # --- DISPARADORES (Triggers) ---
    StepType.FOLDER_WATCHER: AtomCapability(
        steps=[], 
        has_stepper=False, 
        has_variables=True,
        variables_view_mode='file_filter',
        primary_action_label="Guardar Configuración",
        primary_action_icon="save",
        contextual_help=[
            {'title': 'Monitoreo en Tiempo Real', 'message': 'Este disparador detecta archivos nuevos inmediatamente. Asegúrate de que el proceso que copia los archivos los mueva de forma atómica para evitar lecturas parciales.', 'icon': 'speed'},
            {'title': 'Rutas Locales', 'message': 'Usa rutas absolutas completas (ej: C:\\AutomatIA\\Buzon).', 'icon': 'folder'}
        ]
    ),
    StepType.EMAIL_WATCHER: AtomCapability(
        steps=[], 
        has_stepper=False, 
        has_variables=True,
        variables_view_mode='select_inputs',
        primary_action_label="Guardar Configuración",
        primary_action_icon="save",
        contextual_help=[
            {'title': 'Contraseñas de App', 'message': 'Para Gmail o Outlook, usa una "Contraseña de Aplicación" en lugar de tu contraseña normal.', 'icon': 'security'},
            {'title': 'Carpeta de Lectura', 'message': 'Por defecto es INBOX, pero puedes usar cualquier carpeta existente en tu buzón.', 'icon': 'mail'}
        ]
    ),
    
    # --- OUTPUTS (Solo input selection) ---
    StepType.EMAIL_SEND: AtomCapability(
        steps=[],
        has_stepper=False,
        has_variables=True,
        variables_view_mode='select_inputs',
        contextual_help=[
            {
                'title': 'Cuentas Gmail/Outlook',
                'message': 'Si usas Gmail o Outlook, recuerda usar una "Contraseña de aplicación" y activar el puerto 587 con TLS.',
                'icon': 'security'
            }
        ],
        primary_action_label="Guardar Credencial",
        primary_action_icon="save"
    ),
    # TODO: Revisar si SMTP e EMAIL_SEND son duplicados o sutilmente diferentes
    StepType.SMTP: AtomCapability(
        steps=[],
        has_stepper=False,
        has_variables=True,
        variables_view_mode='select_inputs',
        primary_action_label="Guardar Configuración",
        primary_action_icon="save"
    ),
    StepType.ARCHIVE_FILE: AtomCapability(
        steps=[],
        has_stepper=False,
        has_variables=True,
        variables_view_mode='select_inputs',
        contextual_help=[
            {
                'title': 'Variables Dinámicas',
                'message': 'Usa {{archivos}} para referenciar el output de un paso anterior. También puedes usar {{fecha}}, {{hora}} para nombres dinámicos.',
                'icon': 'lightbulb'
            }
        ]
    ),

    # --- WATCHERS EXTRAS ---
    StepType.WEB_WATCHER: AtomCapability(
        steps=[], 
        has_stepper=False, 
        has_variables=True,
        primary_action_label="Guardar Configuración",
        primary_action_icon="save",
        contextual_help=[
            {'title': 'Selectores CSS', 'message': 'Usa el selector más específico posible para evitar falsos positivos.', 'icon': 'search'}
        ]
    ),
    StepType.SCHEDULER: AtomCapability(
        steps=[], 
        has_stepper=False, 
        has_variables=True,
        primary_action_label="Programar",
        primary_action_icon="event",
        contextual_help=[
            {'title': 'Sintaxis Cron', 'message': 'Usa * * * * * para representar Minuto, Hora, Día del mes, Mes, Día de la semana.', 'icon': 'schedule'}
        ]
    ),

    # --- INPUTS (Define outputs via specialized editors) ---
    StepType.API_FETCH: AtomCapability(
        steps=[],
        has_stepper=False,
        has_variables=True,
        variables_view_mode='schema_mapper', # New specialized mode
        primary_action_label="Guardar Configuración",
        primary_action_icon="save"
    ),
    StepType.SQL_QUERY: AtomCapability(
        steps=[],
        has_stepper=False,
        has_variables=True,
        variables_view_mode='schema_mapper', # New specialized mode
        primary_action_label="Guardar Query",
        primary_action_icon="save"
    ),
    StepType.FOLDER_SCAN: AtomCapability(
        steps=[],
        has_stepper=False,
        has_variables=False,
        variables_view_mode='file_filter',  # Filtro de tipos de archivo permitidos
        contextual_help=[
            {
                'title': 'Rutas de Red',
                'message': 'Puedes usar rutas UNC (ej: \\\\servidor\\carpeta) si el servicio tiene permisos de acceso.',
                'icon': 'lan'
            }
        ]
    ),
    StepType.SQL_INSERT: AtomCapability(
        steps=[],
        has_stepper=False,
        has_variables=True,
        variables_view_mode='select_inputs', 
        primary_action_label="Guardar Configuración",
        primary_action_icon="save"
    ),
    StepType.EMAIL_SCAN: AtomCapability(
        steps=[],
        has_stepper=False,
        has_variables=False,  # Output implícito: emails + adjuntos
        primary_action_label="Guardar Configuración",
        primary_action_icon="save"
    ),
    
    # --- PROCESSORS (Standard: Stepper + Input Vars) ---
    StepType.CUSTOM_SCRIPT: AtomCapability(
        steps=[
            {'name': 'Descripción', 'hint': 'Describe qué debe hacer el script', 'current': True, 'completed': False},
            {'name': 'Generación', 'hint': 'Código Python generado', 'current': False, 'completed': False},
            {'name': 'Validación y Sello', 'hint': 'Prueba y promociona', 'current': False, 'completed': False},
        ],
        has_stepper=True,
        has_variables=True,
        variables_view_mode='select_inputs'
    ),

    StepType.EXTRACTION: AtomCapability(
        steps=[
            {'name': 'Documento', 'hint': 'Sube documento de ejemplo', 'current': True, 'completed': False},
            {'name': 'Campos', 'hint': 'Define campos a extraer', 'current': False, 'completed': False},
            {'name': 'Generación', 'hint': 'Script de extracción', 'current': False, 'completed': False},
            {'name': 'Validación', 'hint': 'Verifica resultados', 'current': False, 'completed': False},
        ],
        has_stepper=True,
        has_variables=True,
        variables_view_mode='select_inputs',
        contextual_help=[
            {'title': 'Definición de Campos', 'message': 'Usa nombres de campo descriptivos (ej: "fecha_factura", "importe_total") para mejorar la precisión de la extracción.', 'icon': 'label'},
            {'title': 'Ejemplos', 'message': 'Sube un documento representativo. Si tienes varios formatos, crea múltiples átomos de extracción.', 'icon': 'description'}
        ]
    ),

    StepType.PDF_TOOLS: AtomCapability(
        steps=[
            {'name': 'Origen', 'hint': 'Selecciona fuente de PDFs', 'current': True, 'completed': False},
            {'name': 'Operación', 'hint': 'Configura merge/split/optimize', 'current': False, 'completed': False},
            {'name': 'Resultado', 'hint': 'Revisa y guarda', 'current': False, 'completed': False},
        ],
        has_stepper=True,
        has_variables=True,
        variables_view_mode='select_inputs',
        primary_action_label='Guardar Configuración',
        primary_action_icon='save',
        contextual_help=[
            {
                'title': 'Operación Merge',
                'message': 'La operación de unir PDFs solo se ejecutará si el paso anterior proporciona múltiples archivos. Si solo hay un PDF, se omitirá automáticamente.',
                'icon': 'info'
            },
            {
                'title': 'Optimización',
                'message': 'La optimización nivel 3 reduce el tamaño del archivo sin pérdida de calidad. Recomendado para todos los casos.',
                'icon': 'lightbulb'
            }
        ]
    ),

    # --- NEW CAPABILITIES ---
    StepType.RPA_EXECUTE: AtomCapability(
        has_stepper=True,
        has_variables=True,
        primary_action_label='Sellar Robot',
        primary_action_icon='travel_explore',
        steps=[
            {'name': 'Configuración', 'hint': 'URL y Variables', 'current': True},
            {'name': 'Grabación', 'hint': 'Interactúa con el navegador', 'current': False},
            {'name': 'Revisión', 'hint': 'Edita el Playbook', 'current': False},
        ],
        contextual_help=[
            {'title': 'Grabación', 'message': 'Realiza las acciones lentamente. Si te equivocas, detén la grabación y edita los pasos después.', 'icon': 'videocam'},
            {'title': 'Selectores', 'message': 'La IA intenta encontrar selectores robustos. Si falla, usa "Reparar con IA" en la revisión.', 'icon': 'build'}
        ]
    ),
    StepType.ETL_TRANSFORM: AtomCapability(
        has_stepper=True,
        has_variables=True,
        steps=[
            {'name': 'Datos', 'hint': 'Sube archivo origen', 'current': True},
            {'name': 'Configuración', 'hint': 'Define transformación', 'current': False},
            {'name': 'Vista Previa', 'hint': 'Valida resultados', 'current': False},
            {'name': 'Privacidad', 'hint': 'Anonimización opcional', 'current': False},
        ],
        contextual_help=[
            {'title': 'Instrucciones', 'message': 'Sé específico (ej: "Convierte la columna fecha a formato DD/MM/YYYY").', 'icon': 'chat'}
        ]
    ),
    StepType.ANONYMIZATION: AtomCapability(
        has_stepper=False,
        has_variables=True,
        steps=[],
        primary_action_label='Aplicar Anonimización',
        contextual_help=[
            {'title': 'Presidio Analyzer', 'message': 'Usamos el motor de Microsoft Presidio para detectar PII en texto no estructurado.', 'icon': 'policy'},
            {'title': 'Validación', 'message': 'Revisa la vista previa para asegurarte de que no se oculta información crítica del negocio.', 'icon': 'visibility'}
        ]
    ),
    StepType.REPORT_GENERATE: AtomCapability(
        has_stepper=True,
        has_variables=True,
        steps=[
            {'name': 'Estructura', 'hint': 'Define bloques del informe', 'current': True},
            {'name': 'Datos', 'hint': 'Vincula fuentes a cada bloque', 'current': False},
            {'name': 'Preview', 'hint': 'Vista previa y guardado', 'current': False},
        ],
        primary_action_label='Guardar Informe',
        primary_action_icon='save',
        primary_action_color='primary',
        contextual_help=[
            {'title': 'Bloques', 'message': 'Añade bloques de texto, tablas y gráficos. Cada bloque puede tener su propia fuente de datos.', 'icon': 'dashboard'},
            {'title': 'Múltiples Fuentes', 'message': 'Puedes vincular cada tabla o gráfico a un paso diferente del flujo, combinando datos de múltiples orígenes.', 'icon': 'merge'},
            {'title': 'Copiloto', 'message': 'Usa el Copiloto para sugerir estructura y visualizaciones basadas en tus datos.', 'icon': 'auto_awesome'}
        ]
    ),
    StepType.LLM_PROCESS: AtomCapability(
        has_stepper=True,
        has_variables=True,
        steps=[
            {'name': 'Instrucción', 'hint': 'Define el prompt para el LLM', 'current': True},
            {'name': 'Configuración', 'hint': 'Formato y parámetros', 'current': False},
            {'name': 'Prueba', 'hint': 'Valida con datos de ejemplo', 'current': False},
        ],
        variables_view_mode='select_inputs',
        primary_action_label='Guardar Prompt',
        primary_action_icon='save',
        primary_action_color='primary',
        contextual_help=[
            {'title': 'Asistente de Prompt', 'message': 'Describe qué quieres hacer con los datos y el copiloto te sugerirá un prompt. Podrás editarlo en el formulario principal.', 'icon': 'auto_awesome'},
            {'title': 'Variables Dinámicas', 'message': 'Usa {{variable}} para insertar datos del flujo en tu prompt. Las variables disponibles aparecen en la pestaña "Variables".', 'icon': 'data_object'},
            {'title': 'Privacidad Garantizada', 'message': 'Los datos personales (emails, DNIs, nombres) se enmascaran automáticamente antes de enviarse al LLM y se restauran en la respuesta.', 'icon': 'security'}
        ]
    ),
}

def get_atom_capability(step_type: Any) -> AtomCapability:
    """
    Obtiene la capacidad de UI para un tipo de átomo.
    Retorna la configuración específica o la por defecto.
    """
    if isinstance(step_type, str):
        try:
            from automatia_shared.enums import StepType
            step_type = StepType(step_type)
        except ValueError:
            pass
    return CAPABILITY_MAP.get(step_type, DEFAULT_CAPABILITY)
