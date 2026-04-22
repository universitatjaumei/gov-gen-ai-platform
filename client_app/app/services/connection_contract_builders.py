from typing import Dict, Any, List, Optional
from automatia_shared.contracts.ui_contract import (
    DataContract, 
    UIContract, 
    InputDefinition, 
    InputType, 
    OutputSchema, 
    OutputField
)
from client_app.app.database.models import APIEndpointConfig, DatabaseCredentialConfig

def build_api_fetch_contract(config: Optional[APIEndpointConfig] = None) -> DataContract:
    """
    Construye el DataContract para un átomo de API Fetch.
    """
    inputs = [
        InputDefinition(
            name="endpoint_id",
            label="ID de Endpoint",
            type=InputType.INT,
            required=True,
            description="ID de la configuración de API pre-registrada"
        ),
        InputDefinition(
            name="query_params",
            label="Parámetros de Consulta",
            type=InputType.JSON,
            required=False,
            default={},
            description="Diccionario de parámetros dinámicos para la URL"
        ),
        InputDefinition(
            name="request_body",
            label="Cuerpo de Petición",
            type=InputType.JSON,
            required=False,
            default={},
            description="Payload para peticiones POST, PUT o PATCH"
        )
    ]
    
    outputs = [
        OutputField(
            name="response_body",
            label="Cuerpo de Respuesta",
            type=InputType.JSON,
            description="Datos devueltos por la API"
        ),
        OutputField(
            name="status_code",
            label="Código de Estado",
            type=InputType.INT,
            description="Código de respuesta HTTP (ej: 200, 404)"
        ),
        OutputField(
            name="headers",
            label="Cabeceras",
            type=InputType.JSON,
            description="Headers de la respuesta HTTP"
        ),
        OutputField(
            name="success",
            label="Éxito",
            type=InputType.BOOL,
            description="Indica si el código de estado es 2xx"
        )
    ]
    
    description = f"Consulta a API: {config.name}" if config else "Llamada a servicio REST externo"
    
    return DataContract(
        inputs=UIContract(inputs=inputs),
        outputs=OutputSchema(fields=outputs),
        description=description
    )

def build_sql_query_contract(config: Optional[DatabaseCredentialConfig] = None) -> DataContract:
    """
    Construye el DataContract para un átomo de SQL Query.
    """
    inputs = [
        InputDefinition(
            name="credential_id",
            label="ID de Credencial",
            type=InputType.INT,
            required=True,
            description="ID de la conexión a base de datos guardada"
        ),
        InputDefinition(
            name="query",
            label="Consulta SQL",
            type=InputType.STR,
            required=True,
            description="Sentencia SQL a ejecutar (soporta placeholders :param)"
        ),
        InputDefinition(
            name="parameters",
            label="Parámetros SQL",
            type=InputType.JSON,
            required=False,
            default={},
            description="Valores para los parámetros de la consulta"
        )
    ]
    
    outputs = [
        OutputField(
            name="result_set",
            label="Registros",
            type=InputType.JSON,
            description="Lista de objetos con los resultados de la consulta"
        ),
        OutputField(
            name="row_count",
            label="Número de Filas",
            type=InputType.INT,
            description="Cantidad de registros devueltos o afectados"
        ),
        OutputField(
            name="columns",
            label="Columnas",
            type=InputType.JSON,
            description="Lista de nombres de columnas detectadas"
        )
    ]
    
    description = f"Consulta SQL en: {config.name}" if config else "Ejecuta consultas en base de datos relacional"
    
    return DataContract(
        inputs=UIContract(inputs=inputs),
        outputs=OutputSchema(fields=outputs),
        description=description
    )

def build_email_watcher_contract(config: Dict[str, Any]) -> DataContract:
    """
    Construye el DataContract para un Email Watcher.
    Nota: Se apoya en asset_finishing_service.build_mail_watcher_contract 
    pero aquí definimos la estructura base para el sellado.
    """
    # Usamos la lógica de asset_finishing_service para la parte de outputs que es compleja
    from client_app.app.services.asset_finishing_service import BASE_EMAIL_OUTPUTS
    
    outputs = []
    for f in BASE_EMAIL_OUTPUTS:
        outputs.append(OutputField(**f))
        
    return DataContract(
        inputs=UIContract(inputs=[]), # Disparado por evento, no tiene inputs de usuario directos en el flujo
        outputs=OutputSchema(fields=outputs),
        description=f"Monitor de correo para: {config.get('name', 'Email')}"
    )

def build_folder_watcher_contract(config: Dict[str, Any]) -> DataContract:
    """
    Construye el DataContract para un Folder Watcher.
    """
    outputs = [
        OutputField(
            name="trigger_file",
            label="Archivo",
            type=InputType.FILE,
            description="Ruta del archivo que disparó el evento"
        ),
        OutputField(
            name="file_path",
            label="Ruta Completa",
            type=InputType.STR,
            description="Path absoluto del archivo"
        ),
        OutputField(
            name="file_name",
            label="Nombre de Archivo",
            type=InputType.STR,
            description="Nombre con extensión"
        ),
        OutputField(
            name="file_extension",
            label="Extensión",
            type=InputType.STR,
            description="Extensión del archivo (ej: .pdf)"
        ),
        OutputField(
            name="folder_path",
            label="Carpeta Origen",
            type=InputType.STR,
            description="Ruta de la carpeta monitorizada"
        )
    ]
    
    return DataContract(
        inputs=UIContract(inputs=[]),
        outputs=OutputSchema(fields=outputs),
        description=f"Monitor de archivos en: {config.get('path', 'Ruta local')}"
    )

def build_webhook_contract(config: Dict[str, Any]) -> DataContract:
    """
    Construye el DataContract para un Webhook Entrante.
    """
    outputs = [
        OutputField(
            name="payload",
            label="Payload",
            type=InputType.JSON,
            description="Cuerpo de la petición recibida (JSON)"
        ),
        OutputField(
            name="headers",
            label="Cabeceras",
            type=InputType.JSON,
            description="Headers del request recibido"
        ),
        OutputField(
            name="method",
            label="Método HTTP",
            type=InputType.STR,
            description="Método usado por el emisor (POST, GET, etc.)"
        ),
        OutputField(
            name="timestamp",
            label="Recibido en",
            type=InputType.DATETIME,
            description="ISO Timestamp del momento de recepción"
        )
    ]
    
    return DataContract(
        inputs=UIContract(inputs=[]),
        outputs=OutputSchema(fields=outputs),
        description=f"Webhook listener: {config.get('name', 'Endpoint')}"
    )
