"""
Atom Catalog - Catálogo Centralizado de Tipos de Átomos.

Este módulo define TODOS los tipos de átomos disponibles en el sistema
con sus metadatos completos (nombre, icono, color, descripción, categoría).

Es la ÚNICA fuente de verdad para:
- flows_page.py (galería de añadir paso)
- atoms_page.py (catálogo de átomos guardados)
- Cualquier otro componente que necesite listar tipos de átomos

EXTENDIDO: Ahora incluye metadata para conexiones (Data Contracts Fase 1, Prompt 2).
"""
from automatia_shared.enums import StepType, AtomCategory
from typing import Dict, List, Any, Optional


class AtomMetadata:
    """Metadata completa de un tipo de átomo."""
    def __init__(
        self,
        step_type: StepType,
        label: str,
        icon: str,
        color: str,
        description: str,
        category: str,
        config_schema: Optional[Dict[str, Any]] = None,
        has_stepper: bool = True,
        has_variables: bool = True
    ):
        self.step_type = step_type
        self.label = label
        self.icon = icon
        self.color = color
        self.description = description
        self.category = category
        self.config_schema = config_schema
        self.has_stepper = has_stepper
        self.has_variables = has_variables

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para uso en UI."""
        result = {
            'step_type': self.step_type,
            'label': self.label,
            'icon': self.icon,
            'color': self.color,
            'description': self.description,
            'category': self.category,
            'has_stepper': self.has_stepper,
            'has_variables': self.has_variables
        }
        if self.config_schema:
            result['config_schema'] = self.config_schema
        return result


class ConnectionMetadata:
    """Metadata específica para subtipos de conexión."""
    def __init__(
        self,
        label: str,
        icon: str,
        color: str,
        description: str,
        config_schema: Dict[str, Any]
    ):
        self.label = label
        self.icon = icon
        self.color = color
        self.description = description
        self.config_schema = config_schema

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para uso en UI."""
        return {
            'label': self.label,
            'icon': self.icon,
            'color': self.color,
            'description': self.description,
            'config_schema': self.config_schema
        }


# === METADATA DE CONEXIONES (Data Contracts Fase 1, Prompt 2) ===
CONNECTION_METADATA: Dict[str, ConnectionMetadata] = {
    "EMAIL": ConnectionMetadata(
        label="Conexión Email",
        description="Credenciales IMAP/SMTP para acceso a correo electrónico",
        icon="email",
        color="blue",
        config_schema={
            "type": "object",
            "required": ["host", "port", "username", "password"],
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Servidor IMAP (ej: imap.gmail.com)"
                },
                "port": {
                    "type": "integer",
                    "default": 993,
                    "description": "Puerto IMAP (993 para SSL)"
                },
                "username": {
                    "type": "string",
                    "description": "Usuario de correo"
                },
                "password": {
                    "type": "string",
                    "format": "password",
                    "description": "Contraseña (se encriptará)"
                },
                "use_ssl": {
                    "type": "boolean",
                    "default": True
                }
            }
        }
    ),
    "API": ConnectionMetadata(
        label="Conexión API",
        description="Credenciales para API REST/SOAP",
        icon="api",
        color="green",
        config_schema={
            "type": "object",
            "required": ["base_url"],
            "properties": {
                "base_url": {
                    "type": "string",
                    "description": "URL base de la API"
                },
                "api_key": {
                    "type": "string",
                    "format": "password",
                    "description": "Clave de API (opcional)"
                },
                "headers": {
                    "type": "object",
                    "description": "Headers HTTP adicionales",
                    "default": {}
                },
                "auth_type": {
                    "type": "string",
                    "enum": ["none", "api_key", "bearer", "basic"],
                    "default": "none"
                }
            }
        }
    ),
    "DATABASE": ConnectionMetadata(
        label="Conexión Base de Datos",
        description="Credenciales para SQL/NoSQL",
        icon="storage",
        color="purple",
        config_schema={
            "type": "object",
            "required": ["db_type", "host", "database"],
            "properties": {
                "db_type": {
                    "type": "string",
                    "enum": ["postgresql", "mysql", "sqlite", "mongodb"],
                    "description": "Tipo de base de datos"
                },
                "host": {
                    "type": "string",
                    "description": "Host del servidor"
                },
                "port": {
                    "type": "integer",
                    "description": "Puerto (opcional, usa default del DB)"
                },
                "database": {
                    "type": "string",
                    "description": "Nombre de la base de datos"
                },
                "username": {
                    "type": "string"
                },
                "password": {
                    "type": "string",
                    "format": "password"
                }
            }
        }
    ),
    "FTP": ConnectionMetadata(
        label="Conexión FTP/SFTP",
        description="Credenciales para servidor de archivos",
        icon="folder_shared",
        color="orange",
        config_schema={
            "type": "object",
            "required": ["host", "username"],
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Servidor FTP"
                },
                "port": {
                    "type": "integer",
                    "default": 21
                },
                "username": {
                    "type": "string"
                },
                "password": {
                    "type": "string",
                    "format": "password"
                },
                "use_sftp": {
                    "type": "boolean",
                    "default": False,
                    "description": "Usar SFTP (más seguro)"
                }
            }
        }
    ),
    "SMTP": ConnectionMetadata(
        label="Conexión SMTP",
        description="Credenciales para envío de correo electrónico",
        icon="send",
        color="teal",
        config_schema={
            "type": "object",
            "required": ["server", "port", "username", "password"],
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Servidor SMTP (ej: smtp.gmail.com)",
                    "examples": ["smtp.gmail.com", "smtp.office365.com"]
                },
                "port": {
                    "type": "integer",
                    "default": 587,
                    "description": "Puerto SMTP (587 para STARTTLS, 465 para SSL)",
                    "enum": [25, 465, 587, 2525]
                },
                "username": {
                    "type": "string",
                    "description": "Usuario/Email de la cuenta"
                },
                "password": {
                    "type": "string",
                    "format": "password",
                    "description": "Contraseña o App Password"
                },
                "use_tls": {
                    "type": "boolean",
                    "default": True,
                    "description": "Usar STARTTLS"
                },
                "from_name": {
                    "type": "string",
                    "description": "Nombre del remitente (opcional)"
                }
            }
        }
    )
}


# Catálogo COMPLETO de átomos
# IMPORTANTE: Incluir TODOS los StepType existentes
ATOM_CATALOG: Dict[StepType, AtomMetadata] = {
    StepType.EXTRACTION: AtomMetadata(
        step_type=StepType.EXTRACTION,
        label='Extracción IA',
        icon='description',
        color='blue',
        description='Extraer datos estructurados de documentos PDF o imágenes usando IA.',
        category='Inteligencia Artificial'
    ),
    StepType.ANONYMIZATION: AtomMetadata(
        step_type=StepType.ANONYMIZATION,
        label='Anonimización',
        icon='security',
        color='purple',
        description='Detectar y ocultar datos personales (PII/GDPR) antes del procesamiento.',
        category='Inteligencia Artificial'
    ),
    StepType.MASKING: AtomMetadata(
        step_type=StepType.MASKING,
        label='Enmascaramiento',
        icon='visibility_off',
        color='purple',
        description='Enmascarar datos sensibles con patrones de ocultación.',
        category='Inteligencia Artificial'
    ),
    StepType.CUSTOM_SCRIPT: AtomMetadata(
        step_type=StepType.CUSTOM_SCRIPT,
        label='Personalizada',
        icon='code',
        color='emerald',
        description='Ejecutar lógica personalizada o scripts Python.',
        category='Lógica y Código'
    ),
    StepType.ETL_TRANSFORM: AtomMetadata(
        step_type=StepType.ETL_TRANSFORM,
        label='Transformación ETL',
        icon='transform',
        color='pink',
        description='Limpieza, reestructuración y mapeo de datos tabulares.',
        category='Datos'
    ),
    StepType.SQL_QUERY: AtomMetadata(
        step_type=StepType.SQL_QUERY,
        label='Consulta SQL',
        icon='storage',
        color='blue-grey',
        description='Ejecutar consultas SELECT a bases de datos relacionales. Requiere conexión DATABASE.',
        category='Datos',
        config_schema={
            "type": "object",
            "required": ["connection_id", "query"],
            "properties": {
                "connection_id": {
                    "type": "integer",
                    "description": "ID del átomo CONNECTION (subtipo DATABASE) a utilizar",
                    "ui_widget": "connection_selector",
                    "connection_subtype": "DATABASE"
                },
                "query": {
                    "type": "string",
                    "description": "Consulta SQL SELECT a ejecutar",
                    "ui_widget": "sql_editor",
                    "default": "SELECT * FROM tabla LIMIT 100"
                },
                "parameters": {
                    "type": "object",
                    "description": "Parámetros nombrados para la query (:param_name)",
                    "additionalProperties": {"type": "string"},
                    "default": {}
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Timeout máximo de ejecución en segundos",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 300
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Número máximo de filas a retornar (0 = sin límite)",
                    "default": 1000,
                    "minimum": 0
                }
            }
        }
    ),
    StepType.REPORT_GENERATE: AtomMetadata(
        step_type=StepType.REPORT_GENERATE,
        label='Generar Informe PDF',
        icon='picture_as_pdf',
        color='red',
        description='Generar informes PDF profesionales con plantillas personalizables.',
        category='Salida'
    ),
    StepType.EMAIL: AtomMetadata(
        step_type=StepType.EMAIL,
        label='Email (Leer)',
        icon='mark_email_unread',
        color='indigo',
        description='Monitorizar y descargar correos de una cuenta IMAP.',
        category='Conectores'
    ),
    StepType.EMAIL_SEND: AtomMetadata(
        step_type=StepType.EMAIL_SEND,
        label='Email (Enviar)',
        icon='send',
        color='teal',
        description='Enviar notificaciones o resultados por correo SMTP.',
        category='Salida'
    ),
    StepType.API_FETCH: AtomMetadata(
        step_type=StepType.API_FETCH,
        label='Llamada API',
        icon='api',
        color='cyan',
        description='Consultar servicios web externos (REST/JSON).',
        category='Conectores'
    ),
    # WEBHOOK: Eliminado - No viable en instalaciones locales detrás de firewall
    StepType.NAVIGATION: AtomMetadata(
        step_type=StepType.NAVIGATION,
        label='Navegación RPA',
        icon='public',
        color='amber',
        description='Controlar navegador web para interactuar con sitios automáticamente.',
        category='Automatización Web'
    ),
    StepType.RPA_EXECUTE: AtomMetadata(
        step_type=StepType.RPA_EXECUTE,
        label='Ejecutar Playbook RPA',
        icon='travel_explore',
        color='deep-orange',
        description='Ejecutar grabaciones de RPA complejas (clicks, inputs, etc).',
        category='Automatización Web'
    ),
    # === NUEVAS ACCIONES (Refactorización Taxonomía 2026) ===
    StepType.SCHEDULER: AtomMetadata(
        step_type=StepType.SCHEDULER,
        label='Programador',
        icon='schedule',
        color='amber',
        description='Programar ejecuciones automáticas de flujos (diario, semanal, cron).',
        category='Disparadores',
        has_stepper=False,
        has_variables=False
    ),
    StepType.FOLDER_SCAN: AtomMetadata(
        step_type=StepType.FOLDER_SCAN,
        label='Escaneo de Carpeta',
        icon='folder_open',
        color='orange',
        description='Escanear carpeta y listar archivos según patrón (sin monitoreo continuo).',
        category='Entradas'
    ),
    StepType.EMAIL_SCAN: AtomMetadata(
        step_type=StepType.EMAIL_SCAN,
        label='Recolector de Emails',
        icon='attach_email',
        color='indigo',
        description='Buscar correos por criterio y descargar adjuntos para procesamiento.',
        category='Entradas'
    ),
    StepType.ARCHIVE_FILE: AtomMetadata(
        step_type=StepType.ARCHIVE_FILE,
        label='Archivar Resultado',
        icon='save_alt',
        color='teal',
        description='Guardar archivos de salida en carpeta destino con soporte de variables.',
        category='Salidas'
    ),
    StepType.GRAPHICS: AtomMetadata(
        step_type=StepType.GRAPHICS,
        label='Gráficos',
        icon='bar_chart',
        color='pink',
        description='Generar visualizaciones y gráficos a partir de datos procesados.',
        category='Salidas'
    ),
    StepType.PDF_TOOLS: AtomMetadata(
        step_type=StepType.PDF_TOOLS,
        label='Herramientas PDF',
        icon='picture_as_pdf',
        color='red',
        description='Une, divide u optimiza documentos PDF.',
        category='Utilidades',
        config_schema={
            'operation': {
                'type': 'string',
                'enum': ['merge', 'split', 'optimize'],
                'description': 'Tipo de operación a realizar'
            },
            'optimize': {
                'type': 'boolean',
                'default': True,
                'description': 'Aplicar optimización al guardar (nivel 3)'
            },
            'split_mode': {
                'type': 'string',
                'enum': ['ranges', 'pages', 'all'],
                'description': 'Modo de división: rangos, páginas específicas o todas'
            },
            'ranges': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'start': {'type': 'integer', 'minimum': 1},
                        'end': {'type': 'integer', 'minimum': 1}
                    }
                },
                'description': 'Lista de rangos de páginas para división'
            },
            'pages': {
                'type': 'array',
                'items': {'type': 'integer', 'minimum': 1},
                'description': 'Lista de números de página para extraer'
            },
            'optimization_level': {
                'type': 'integer',
                'minimum': 1,
                'maximum': 4,
                'default': 3,
                'description': 'Nivel de optimización (1=básico, 4=agresivo)'
            },
            'output_name': {
                'type': 'string',
                'description': 'Nombre del archivo de salida (para merge)'
            }
        },
        has_stepper=True,
        has_variables=True
    ),
    StepType.LLM_PROCESS: AtomMetadata(
        step_type=StepType.LLM_PROCESS,
        label='Procesamiento LLM',
        icon='psychology',
        color='purple',
        description='Procesa texto con IA generativa: resume, clasifica, traduce o transforma.',
        category='Inteligencia Artificial',
        config_schema={
            'instruction': {
                'type': 'string',
                'description': 'Instrucción principal para el LLM',
                'required': True
            },
            'system_prompt': {
                'type': 'string',
                'description': 'Contexto adicional del sistema (opcional)',
                'default': ''
            },
            'output_format': {
                'type': 'string',
                'enum': ['text', 'json'],
                'default': 'text',
                'description': 'Formato de salida esperado'
            },
            'json_schema': {
                'type': 'object',
                'description': 'Schema JSON para validar salida estructurada',
                'default': None
            },
            'temperature': {
                'type': 'number',
                'minimum': 0,
                'maximum': 1,
                'default': 0.3,
                'description': 'Creatividad del modelo (0=determinista, 1=creativo)'
            },
            'max_tokens': {
                'type': 'integer',
                'minimum': 100,
                'maximum': 4000,
                'default': 1000,
                'description': 'Límite de tokens en la respuesta'
            }
        },
        has_stepper=True,
        has_variables=True
    ),
    StepType.FOLDER_WATCHER: AtomMetadata(
        step_type=StepType.FOLDER_WATCHER,
        label='Monitor de Carpeta',
        icon='folder',
        color='orange',
        description='Monitorear carpeta y disparar flujo cuando aparezcan nuevos archivos.',
        category='Disparadores',
        has_stepper=False,
        has_variables=False
    ),
    StepType.EMAIL_WATCHER: AtomMetadata(
        step_type=StepType.EMAIL_WATCHER,
        label='Monitor de Email',
        icon='mark_email_unread',
        color='blue',
        description='Monitorear bandeja de correo y disparar flujo con nuevos emails.',
        category='Disparadores',
        has_stepper=False,
        has_variables=False
    ),
    StepType.WEB_WATCHER: AtomMetadata(
        step_type=StepType.WEB_WATCHER,
        label='Monitor Web',
        icon='public',
        color='green',
        description='Monitorear páginas web y disparar flujo cuando detecte cambios.',
        category='Disparadores',
        has_stepper=False,
        has_variables=False
    ),
    # === SALIDAS (continuación) ===
    StepType.SQL_INSERT: AtomMetadata(
        step_type=StepType.SQL_INSERT,
        label='Inserción SQL',
        icon='add_box',
        color='indigo',
        description='Insertar o actualizar datos en bases de datos relacionales.',
        category='Salidas'
    ),
    # === LEGACY (mantener por compatibilidad) ===
    StepType.CONNECTION: AtomMetadata(
        step_type=StepType.CONNECTION,
        label='Conexión',
        icon='link',
        color='gray',
        description='Credenciales reutilizables para servicios externos (Email, API, BD, FTP).',
        category='Conectores'
    ),
}

# Aliases for backward/forward compatibility
ATOM_CATALOG[StepType.SMTP] = ATOM_CATALOG[StepType.EMAIL_SEND]
# EMAIL_WATCHER ya tiene su propia entrada en el catálogo


# ============================================================================
# NUEVA TAXONOMÍA: 4 Capas Funcionales (Refactorización 2026)
# ============================================================================

# Mapeo de categoría funcional → tipos de átomo
ATOM_CATEGORIES_V2: Dict[AtomCategory, List[StepType]] = {
    AtomCategory.TRIGGER: [
        # Ocultos de la galería - solo se usan en configuración de flujos
        StepType.FOLDER_WATCHER,
        StepType.EMAIL_WATCHER,
        StepType.WEB_WATCHER,
        StepType.SCHEDULER,
    ],
    AtomCategory.INPUT: [
        StepType.SQL_QUERY,
        StepType.API_FETCH,
        StepType.FOLDER_SCAN,
        StepType.EMAIL_SCAN,
    ],
    AtomCategory.PROCESSOR: [
        StepType.EXTRACTION,
        StepType.RPA_EXECUTE,        # Incluye navegación web
        StepType.ETL_TRANSFORM,
        StepType.CUSTOM_SCRIPT,
        StepType.LLM_PROCESS,        # Procesamiento de texto con LLM
        StepType.GRAPHICS,           # Genera visualizaciones (antes de informes)
        StepType.REPORT_GENERATE,    # Genera informes (puede incluir gráficos)
    ],
    AtomCategory.OUTPUT: [
        StepType.SMTP,
        StepType.SQL_INSERT,         # Inserción/actualización en BD
        StepType.API_FETCH,          # APIs también pueden enviar datos (POST/PUT)
        StepType.ARCHIVE_FILE,
    ],
    AtomCategory.UTILITY: [
        StepType.ANONYMIZATION,      # Anonimización y enmascaramiento
        StepType.PDF_TOOLS,          # Herramientas PDF: unir, dividir, optimizar
    ],
}

# Iconos de Material Design para cada categoría
CATEGORY_ICONS: Dict[AtomCategory, str] = {
    AtomCategory.TRIGGER: "bolt",
    AtomCategory.INPUT: "login",
    AtomCategory.PROCESSOR: "psychology",
    AtomCategory.OUTPUT: "logout",
    AtomCategory.UTILITY: "build",
}

# Etiquetas legibles para cada categoría
CATEGORY_LABELS: Dict[AtomCategory, str] = {
    AtomCategory.TRIGGER: "gallery.trigger",
    AtomCategory.INPUT: "gallery.input",
    AtomCategory.PROCESSOR: "gallery.processor",
    AtomCategory.OUTPUT: "gallery.output",
    AtomCategory.UTILITY: "gallery.utility",
}

ATOM_CATEGORIES: Dict[str, List[StepType]] = {
    'Disparadores': ATOM_CATEGORIES_V2[AtomCategory.TRIGGER],
    'Entradas': ATOM_CATEGORIES_V2[AtomCategory.INPUT],
    'Procesadores': ATOM_CATEGORIES_V2[AtomCategory.PROCESSOR],
    'Salidas': ATOM_CATEGORIES_V2[AtomCategory.OUTPUT],
    'Utilidades': ATOM_CATEGORIES_V2[AtomCategory.UTILITY],
}


# === PLANTILLAS DE CONTRATOS DE DATOS (Data Contracts Fase 2.5) ===
OUTPUT_CONTRACT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "SQL_QUERY": {
        "description": "Plantilla de output contract para consultas SQL. Personalizar según columnas de la query.",
        "template": {
            "type": "object",
            "properties": {
                "rows": {
                    "type": "array",
                    "description": "Filas retornadas por la consulta",
                    "items": {
                        "type": "object",
                        "description": "Cada fila es un objeto con las columnas como keys",
                        "additionalProperties": True
                    }
                },
                "row_count": {
                    "type": "integer",
                    "description": "Número total de filas retornadas"
                },
                "columns": {
                    "type": "array",
                    "description": "Lista de nombres de columnas",
                    "items": {"type": "string"}
                },
                "execution_time_ms": {
                    "type": "integer",
                    "description": "Tiempo de ejecución en milisegundos"
                }
            },
            "required": ["rows", "row_count", "columns"]
        },
        "example": {
            "rows": [
                {"id": 1, "nombre": "Juan", "email": "juan@example.com"},
                {"id": 2, "nombre": "María", "email": "maria@example.com"}
            ],
            "row_count": 2,
            "columns": ["id", "nombre", "email"],
            "execution_time_ms": 45
        }
    },
    "EMAIL": {
        "description": "Output contract para lectura de emails",
        "template": {
            "type": "object",
            "properties": {
                "emails": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "uid": {"type": "string"},
                            "subject": {"type": "string"},
                            "from": {"type": "string"},
                            "date": {"type": "string", "format": "date-time"},
                            "body_text": {"type": "string"},
                            "attachments": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "filename": {"type": "string"},
                                        "path": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                "count": {"type": "integer"}
            },
            "required": ["emails", "count"]
        }
    },
    "API_FETCH": {
        "description": "Output contract para llamadas API. Personalizar según endpoint.",
        "template": {
            "type": "object",
            "properties": {
                "status_code": {"type": "integer"},
                "data": {
                    "type": "any",
                    "description": "Datos de respuesta (estructura variable según API)"
                },
                "headers": {"type": "object"}
            },
            "required": ["status_code", "data"]
        }
    }
}


def get_output_contract_template(step_type: str) -> Optional[Dict[str, Any]]:
    """
    Obtener plantilla de output contract para un tipo de acción.

    Args:
        step_type: Tipo de acción (string, ej: 'SQL_QUERY', 'EMAIL')

    Returns:
        Dict con 'template' y 'example' o None si no hay plantilla
    """
    return OUTPUT_CONTRACT_TEMPLATES.get(step_type)


def get_atom_metadata(step_type: StepType) -> AtomMetadata:
    """
    Obtiene metadata de un tipo de átomo.
    
    Args:
        step_type: Tipo de átomo (StepType enum)
        
    Returns:
        AtomMetadata con toda la información del átomo
        
    Raises:
        KeyError si el tipo no está en el catálogo
    """
    return ATOM_CATALOG[step_type]


def get_all_atoms() -> List[AtomMetadata]:
    """Retorna lista de todos los átomos disponibles."""
    return list(ATOM_CATALOG.values())


def get_atoms_by_category() -> Dict[str, List[AtomMetadata]]:
    """
    Retorna átomos agrupados por categoría (versión legacy con strings).

    Returns:
        Dict donde key es categoría (string) y value es lista de AtomMetadata
    """
    result = {}
    for category, step_types in ATOM_CATEGORIES.items():
        result[category] = [ATOM_CATALOG[st] for st in step_types if st in ATOM_CATALOG]
    return result


def get_atoms_by_category_v2() -> Dict[AtomCategory, List[AtomMetadata]]:
    """
    Retorna átomos agrupados por AtomCategory (nueva taxonomía).

    Returns:
        Dict donde key es AtomCategory enum y value es lista de AtomMetadata
    """
    result = {}
    for category, step_types in ATOM_CATEGORIES_V2.items():
        result[category] = [ATOM_CATALOG[st] for st in step_types if st in ATOM_CATALOG]
    return result


def get_category_for_step_type(step_type: StepType) -> Optional[AtomCategory]:
    """
    Obtiene la categoría funcional de un tipo de átomo.

    Args:
        step_type: Tipo de átomo

    Returns:
        AtomCategory o None si no está categorizado
    """
    for category, step_types in ATOM_CATEGORIES_V2.items():
        if step_type in step_types:
            return category
    return None


def get_category_icon(category: AtomCategory) -> str:
    """Retorna el icono de Material Design para una categoría."""
    return CATEGORY_ICONS.get(category, "category")


def get_category_label(category: AtomCategory) -> str:
    """Retorna la etiqueta legible para una categoría."""
    from client_app.app.core.state import state
    t = state.i18n.t
    key = CATEGORY_LABELS.get(category, category.value)
    return t(key, key)


def get_atom_icon(step_type: StepType) -> str:
    """Retorna icono para un tipo de átomo."""
    return ATOM_CATALOG.get(step_type, AtomMetadata(
        step_type=step_type,
        label='Unknown',
        icon='extension',
        color='grey',
        description='Tipo desconocido',
        category='Otros'
    )).icon


def get_atom_color(step_type: StepType) -> str:
    """Retorna color para un tipo de átomo."""
    return ATOM_CATALOG.get(step_type, AtomMetadata(
        step_type=step_type,
        label='Unknown',
        icon='extension',
        color='grey',
        description='Tipo desconocido',
        category='Otros'
    )).color


def get_connection_metadata(subtype: str) -> ConnectionMetadata:
    """
    Obtener metadata de un subtipo de conexión.

    Args:
        subtype: Subtipo de conexión (EMAIL, API, DATABASE, FTP)

    Returns:
        ConnectionMetadata con información del subtipo

    Raises:
        KeyError: Si el subtipo no existe
    """
    return CONNECTION_METADATA[subtype]


def get_all_connection_subtypes() -> List[str]:
    """Retorna lista de todos los subtipos de conexión disponibles."""
    return list(CONNECTION_METADATA.keys())


def get_connection_config_schema(subtype: str) -> Dict[str, Any]:
    """
    Obtener JSON Schema de configuración para un subtipo de conexión.

    Args:
        subtype: Subtipo de conexión

    Returns:
        JSON Schema de configuración
    """
    return CONNECTION_METADATA[subtype].config_schema


# === MAPA DE RUTAS DE DISEÑO STANDALONE ===
# Mapea StepType → ruta de página de diseño standalone
# Usado por atom_gallery.py, atoms_page.py y flows_page.py
STEP_TYPE_ROUTES: Dict[StepType, str] = {
    # Procesadores
    StepType.EXTRACTION: '/documents',
    StepType.RPA_EXECUTE: '/rpa',
    StepType.ETL: '/etl',
    StepType.ETL_TRANSFORM: '/etl',
    StepType.CUSTOM_SCRIPT: '/custom-scripts',
    StepType.ANONYMIZATION: '/anonymizer',
    StepType.REPORT_GENERATE: '/reports/designer',
    # Disparadores (Triggers)
    StepType.EMAIL_WATCHER: '/connections/email?mode=design',
    StepType.EMAIL: '/connections/email?mode=design',
    StepType.FOLDER_WATCHER: '/connections/folders?mode=design',
    StepType.WEB_WATCHER: '/triggers/web-watcher?mode=design',
    StepType.SCHEDULER: '/triggers/scheduler?mode=design',
    # Entradas (Inputs)
    StepType.API_FETCH: '/connections/api',
    StepType.SQL_QUERY: '/connections/sql',
    StepType.FOLDER_SCAN: '/inputs/folder-scan',
    StepType.EMAIL_SCAN: '/inputs/email-scan',
    # Procesadores (continuación)
    StepType.GRAPHICS: '/graphics',
    StepType.LLM_PROCESS: '/llm-process',
    # Salidas (Outputs)
    StepType.SMTP: '/connections/smtp',
    StepType.EMAIL_SEND: '/connections/smtp',
    StepType.SQL_INSERT: '/outputs/sql',
    StepType.ARCHIVE_FILE: '/outputs/archive',
    # Utilidades
    StepType.PDF_TOOLS: '/atoms/pdf-tools/new',
}


def get_atom_route(step_type: StepType) -> Optional[str]:
    """
    Obtener ruta de página de diseño standalone para un tipo de átomo.

    Args:
        step_type: Tipo de átomo

    Returns:
        Ruta URL o None si no tiene página dedicada
    """
    return STEP_TYPE_ROUTES.get(step_type)
