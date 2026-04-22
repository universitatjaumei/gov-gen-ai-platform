"""
AssetFinishingService - Servicio de "Sellado Atomico"
Prompt #2: Coordina la promocion de un recurso a "atomo completo".
Prompt #6: Añade soporte para MailWatchers con herencia de contratos.

Este servicio garantiza que cualquier automatismo (Script, Extraccion, API, MailWatcher)
tenga:
1. UIContract: Contrato de datos inferido del codigo fuente
2. README.md: Documentacion tecnica generada automaticamente

Uso:
    service = AssetFinishingService(session=db_session)
    sealed_script = await service.seal_resource(script_id=123)
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from client_app.app.database.models import (
    ScriptLibrary,
    UserExtractionConfig,
    APIEndpointConfig,
    DatabaseCredentialConfig,
    FlowRegistry,
    TriggerConfig
)
from client_app.app.services.doc_generator_service import doc_generator
from automatia_shared.utils.inference import infer_contract_from_source
from automatia_shared.contracts.ui_contract import InputType, DataContract
from automatia_shared.enums import StepType
from client_app.app.services.connection_contract_builders import (
    build_api_fetch_contract,
    build_sql_query_contract,
    build_email_watcher_contract,
    build_folder_watcher_contract,
    build_webhook_contract
)


logger = logging.getLogger(__name__)


# === PROMPT #6: MailWatcher Contract Building ===

# Base email fields that every MailWatcher exposes
BASE_EMAIL_OUTPUTS = [
    {
        "name": "email_sender",
        "label": "Remitente",
        "type": InputType.STR.value,
        "required": True,
        "description": "Dirección de correo del remitente"
    },
    {
        "name": "email_subject",
        "label": "Asunto",
        "type": InputType.STR.value,
        "required": True,
        "description": "Asunto del correo electrónico"
    },
    {
        "name": "email_date",
        "label": "Fecha",
        "type": InputType.DATETIME.value,
        "required": True,
        "description": "Fecha y hora de recepción del correo"
    },
    {
        "name": "email_body",
        "label": "Cuerpo",
        "type": InputType.STR.value,
        "required": False,
        "description": "Contenido del cuerpo del correo (legacy)"
    },
    {
        "name": "email_body_plain",
        "label": "Cuerpo (Texto)",
        "type": InputType.STR.value,
        "required": False,
        "description": "Cuerpo del correo en texto plano limpio (sin HTML)"
    },
    {
        "name": "email_body_html",
        "label": "Cuerpo (HTML)",
        "type": InputType.STR.value,
        "required": False,
        "description": "Cuerpo del correo en formato HTML (opcional)"
    },
    {
        "name": "attachments",
        "label": "Adjuntos",
        "type": InputType.FILES.value,
        "required": False,
        "description": "Archivos adjuntos del correo"
    },
]


async def get_template_contract(
    session,
    template_id: str
) -> Optional[Dict[str, Any]]:
    """
    Recupera el UIContract desde una plantilla de configuración de extracción (UserExtractionConfig).

    Args:
        session: Sesión de base de datos.
        template_id: Identificador de la plantilla de extracción.

    Returns:
        Diccionario con el contrato (inputs/outputs) o None si no se encuentra o hay error.
    """
    try:
        config = await session.get(UserExtractionConfig, template_id)
        if not config:
            return None

        # Extract fields from expected_schema
        schema = config.expected_schema or {}
        fields = schema.get("fields", [])

        if not fields:
            return None

        # Build contract from fields
        outputs = []
        for field in fields:
            outputs.append({
                "name": field.get("name", ""),
                "label": field.get("description", field.get("name", "")),
                "type": _map_type_to_input_type(field.get("type", "string")),
                "required": not field.get("is_optional", False),
                "description": field.get("description", "")
            })

        return {
            "inputs": [],
            "outputs": outputs
        }

    except Exception as e:
        logger.warning(f"Error getting template contract {template_id}: {e}")
        return None


def _map_type_to_input_type(type_str: str) -> str:
    """
    Mapea una cadena de texto que representa un tipo de dato a un valor del enum InputType.
    
    Args:
        type_str: Cadena con el nombre del tipo (ej: 'string', 'integer').
        
    Returns:
        Valor string del InputType correspondiente.
    """
    type_map = {
        'string': InputType.STR.value,
        'str': InputType.STR.value,
        'text': InputType.STR.value,
        'int': InputType.INT.value,
        'integer': InputType.INT.value,
        'float': InputType.FLOAT.value,
        'decimal': InputType.FLOAT.value,
        'date': InputType.DATE.value,
        'datetime': InputType.DATETIME.value,
        'bool': InputType.BOOL.value,
        'boolean': InputType.BOOL.value,
    }
    return type_map.get(str(type_str).lower(), InputType.STR.value)


def build_mail_watcher_contract(
    name: str,
    template_contract: Optional[Dict[str, Any]],
    email_account: str,
    folder: str = "INBOX",
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Construye un UIContract completo para un MailWatcher, combinando los campos
    estándar de correo con los campos heredados de una plantilla de extracción.

    Args:
        name: Nombre del MailWatcher.
        template_contract: Contrato de la plantilla de extracción vinculada.
        email_account: Cuenta de correo monitorizada.
        folder: Carpeta IMAP monitorizada.
        filters: Filtros de activación configurados.

    Returns:
        Diccionario que representa el UIContract completo.
    """
    # Start with base email outputs
    outputs = [dict(field) for field in BASE_EMAIL_OUTPUTS]

    # Inherit fields from template contract
    if template_contract and template_contract.get("outputs"):
        for field in template_contract["outputs"]:
            # Mark inherited fields as optional (attachment might not be present)
            inherited_field = dict(field)
            inherited_field["required"] = False
            inherited_field["description"] = (
                f"{field.get('description', '')} (heredado del template de extracción)"
            ).strip()
            outputs.append(inherited_field)

    # Build metadata (exclude sensitive data)
    metadata = {
        "type": "mail_watcher",
        "email_account": email_account,
        "folder": folder,
        "has_extraction_template": template_contract is not None,
        "field_count": len(outputs)
    }

    if filters:
        # Include filter info but sanitize
        safe_filters = {
            k: v for k, v in filters.items()
            if k not in ('password', 'token', 'secret', 'credential')
        }
        metadata["filters"] = safe_filters

    return {
        "version": "1.0.0",
        "inputs": [],  # MailWatcher has no user inputs, it's event-driven
        "outputs": outputs,
        "metadata": metadata
    }


def generate_mail_watcher_readme(
    name: str,
    email_account: str,
    folder: str = "INBOX",
    template_name: Optional[str] = None,
    field_names: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    **kwargs  # Catch and ignore sensitive params
) -> str:
    """
    Genera el contenido Markdown para el archivo README.md de un MailWatcher,
    documentando la configuración de monitorización y los campos que extrae.

    Args:
        name: Nombre del MailWatcher.
        email_account: Cuenta de correo monitoreada.
        folder: Carpeta IMAP.
        template_name: Nombre de la plantilla de extracción vinculada.
        field_names: Lista de nombres de campos que serán extraídos.
        filters: Filtros de activación.

    Returns:
        Contenido del README en formato Markdown.
    """
    lines = [
        f"# {name}",
        "",
        "Automatismo de monitorización de correo electrónico.",
        "",
        "## Configuración",
        "",
        f"**Cuenta monitoreada:** `{email_account}`",
        f"**Carpeta:** `{folder}`",
        "",
    ]

    # Template info
    if template_name:
        lines.extend([
            "## Template de Extracción",
            "",
            f"Este MailWatcher procesa adjuntos usando el template **{template_name}**.",
            "",
        ])

    # Filters section
    if filters:
        lines.extend([
            "## Filtros de Activación",
            "",
            "El flujo solo se dispara cuando el correo cumple estas condiciones:",
            "",
        ])
        if filters.get("subject_contains"):
            lines.append(f"- Asunto contiene: `{filters['subject_contains']}`")
        if filters.get("has_attachments"):
            lines.append("- El correo tiene adjuntos")
        if filters.get("attachment_extensions"):
            exts = ", ".join(filters["attachment_extensions"])
            lines.append(f"- Extensiones permitidas: `{exts}`")
        if filters.get("whitelist_senders"):
            senders = ", ".join(filters["whitelist_senders"])
            lines.append(f"- Remitentes permitidos: `{senders}`")
        lines.append("")

    # Output fields section
    lines.extend([
        "## Campos de Salida",
        "",
        "### Campos del Correo",
        "",
        "| Campo | Tipo | Descripción |",
        "|-------|------|-------------|",
        "| email_sender | STR | Dirección del remitente |",
        "| email_subject | STR | Asunto del correo |",
        "| email_date | DATETIME | Fecha de recepción |",
        "| email_body | STR | Cuerpo del mensaje (legacy) |",
        "| email_body_plain | STR | Cuerpo en texto plano limpio |",
        "| email_body_html | STR | Cuerpo en formato HTML |",
        "| attachments | FILES | Archivos adjuntos |",
        "",
    ])

    # Extraction fields
    if field_names:
        lines.extend([
            "### Campos Extraídos del Adjunto",
            "",
            "| Campo | Obligatorio |",
            "|-------|-------------|",
        ])
        for fname in field_names:
            lines.append(f"| {fname} | No* |")
        lines.extend([
            "",
            "*Los campos extraídos son opcionales porque el adjunto podría no estar presente o tener formato incorrecto.",
            "",
        ])

    lines.extend([
        "---",
        "",
        "*Generado automáticamente por Gov Gen AI*"
    ])

    return "\n".join(lines)


# === END PROMPT #6 ===

# Ruta base para documentacion (consistente con script_library_service)
STORAGE_ROOT = Path("data/storage/scripts")
SCRIPTS_DIR = STORAGE_ROOT / "src"
DOCS_DIR = STORAGE_ROOT / "docs"


class AssetFinishingService:
    """
    Servicio de Sellado Atomico.

    Coordina la "promocion" de un recurso desde un estado de "borrador"
    a un "atomo completo" de la biblioteca, garantizando que tenga:
    - UIContract inferido del codigo
    - README.md generado automaticamente

    Principios:
    - Atomicidad: usa transaccion de DB para evitar estados inconsistentes
    - Idempotencia: sellar dos veces actualiza el contrato existente
    - Robustez: codigo vacio o con errores genera contrato vacio sin fallar
    """

    def __init__(self, session):
        """
        Inicializa el servicio.

        Args:
            session: Sesion de SQLModel para operaciones de DB
        """
        self.session = session
        # Asegurar que existen los directorios
        DOCS_DIR.mkdir(parents=True, exist_ok=True)

    async def seal_resource(
        self,
        script_id: int,
        precalculated_contract: Optional[Dict[str, Any]] = None,
        target_status: Optional[str] = None
    ) -> ScriptLibrary:
        """
        Sella un recurso (Script) asignándole un UIContract y generando su documentación técnica.

        Este método:
        1. Carga el registro del script desde la base de datos.
        2. Infiere el UIContract del código fuente (o utiliza uno pre-calculado).
        3. Genera el archivo README.md correspondiente.
        4. Persiste la ruta de la documentación y el contrato en el registro del script.

        Args:
            script_id: Identificador único del script en la ScriptLibrary.
            precalculated_contract: Contrato de datos opcional si ya fue calculado previamente.
            target_status: Estado objetivo opcional (ej. 'published').

        Returns:
            El objeto ScriptLibrary actualizado con el contrato y la ruta de documentación.

        Raises:
            ValueError: Si no se encuentra el script con el ID proporcionado.
        """
        # 0. Si precalculated_contract es un StepType, estamos sellando una conexión
        if isinstance(precalculated_contract, StepType):
            return await self.seal_connection_resource(script_id, precalculated_contract, target_status)

        # 1. Cargar el script
        script = await self.session.get(ScriptLibrary, script_id)
        if not script:
            raise ValueError(f"Script con ID {script_id} no encontrado")

        # Prompt 6: Dispatch for MailWatcher
        if script.source_module == 'email':
            logger.info(f"Delegando sellado de {script_id} a seal_mail_watcher")
            return await self.seal_mail_watcher(script_id, target_status=target_status)

        # 2. Obtener el codigo fuente
        code = self._get_script_code(script)

        # 3. Generar o usar el contrato
        if precalculated_contract:
            # Usar contrato pre-calculado (Factory/Extraction)
            contract_dict = precalculated_contract
            logger.info(f"Usando contrato pre-calculado para script {script_id}")
        else:
            # Inferir contrato del codigo fuente
            contract = infer_contract_from_source(code)
            contract_dict = contract.model_dump()
            logger.info(
                f"Contrato inferido para script {script_id}: "
                f"{len(contract.inputs)} inputs detectados"
            )

        # 4. Actualizar el contrato en el script
        script.ui_contract = contract_dict

        # 5. Generar documentacion
        # 5. Generar documentacion (Prompt 5 Unification)
        try:
            # Re-validate contract to object
            if isinstance(contract_dict, dict):
                # If it's a UIContract (has 'inputs' as list), wrap it in a DataContract
                if 'inputs' in contract_dict and isinstance(contract_dict['inputs'], list):
                    contract_dict = {
                        "inputs": contract_dict,
                        "outputs": {"fields": []},
                        "version": contract_dict.get("version", "1.0.0")
                    }
                data_contract = DataContract(**contract_dict)
            else:
                data_contract = contract_dict

            # Generate content using unified method
            readme_content = doc_generator.build_readme_content(data_contract)
            
            # Save file
            doc_path = DOCS_DIR / f"{script.id}.md"
            doc_path.write_text(readme_content, encoding='utf-8')
            
            # Guardar ruta relativa
            script.doc_path = doc_path.name
            logger.info(f"Documentacion generada (Unified): {script.doc_path}")
        except Exception as e:
            logger.warning(f"Error generando documentacion para {script_id}: {e}")
            # No fallar el sellado si falla la doc
            script.doc_path = None
        
        # 5.1 Set status if requested
        if target_status:
            script.status = target_status
            logger.info(f"Promocionando script {script_id} a estado {target_status}")
            
            # Sync back to Source Resource if it's an extraction script
            if script.source_module == 'extraction' and script.source_automation_id:
                try:
                    # UserExtractionConfig use strings for IDs
                    source_id = str(script.source_automation_id)
                    source_config = await self.session.get(UserExtractionConfig, source_id)
                    if source_config:
                        source_config.status = target_status
                        self.session.add(source_config)
                        logger.info(f"Syncing status {target_status} back to UserExtractionConfig {source_id}")
                except Exception as sync_err:
                    logger.warning(f"Failed to sync status back to source: {sync_err}")

        # 6. Persistir cambios
        self.session.add(script)
        await self.session.commit()
        await self.session.refresh(script)

        logger.info(f"Script {script_id} sellado exitosamente")
        return script

    def get_seal_metadata(self, script: ScriptLibrary) -> Dict[str, Any]:
        """
        Obtiene metadatos estructurados sobre un recurso ya sellado para su visualización en la UI.

        Args:
            script: Objeto ScriptLibrary que ha sido sellado previamente.

        Returns:
            Diccionario con información resumida que incluye el ID, nombre, número de campos del contrato,
            la ruta absoluta al README.md y el UIContract completo.
        """
        contract = script.ui_contract or {}
        inputs = contract.get('inputs', [])
        
        # Get field names for preview
        field_names = [inp.get('name', '') for inp in inputs if inp.get('name')]
        
        # Build absolute README path
        readme_path = None
        if script.doc_path:
            readme_path = str(DOCS_DIR / script.doc_path)
        
        return {
            'script_id': script.id,
            'script_name': script.name,
            'contract_fields_count': len(inputs),
            'contract_fields': field_names,
            'readme_path': readme_path,
            'ui_contract': contract
        }

    async def seal_mail_watcher(
        self,
        script_id: int,
        target_status: Optional[str] = None
    ) -> ScriptLibrary:
        """
        Sella un recurso de tipo MailWatcher, construyendo un contrato heredado.

        Combina los metadatos de monitorización de correo con los campos definidos en
        la plantilla de extracción vinculada para generar un contrato de salida completo.

        Args:
            script_id: Identificador del MailWatcher en la ScriptLibrary.
            target_status: Estado objetivo opcional (ej. 'published').

        Returns:
            El objeto ScriptLibrary actualizado con el contrato combinado y su README.

        Raises:
            ValueError: Si no se encuentra el MailWatcher en la base de datos.
        """
        # 1. Load the MailWatcher script
        script = await self.session.get(ScriptLibrary, script_id)
        if not script:
            raise ValueError(f"MailWatcher con ID {script_id} no encontrado")

        # 2. Get metadata
        metadata = script.source_metadata or {}
        extraction_template_id = metadata.get('extraction_template_id')
        email_account = metadata.get('email_account', 'unknown@mail.com')
        folder = metadata.get('folder', 'INBOX')
        filters = metadata.get('filters', {})

        # 3. Get template contract if linked
        template_contract = None
        template_name = None
        if extraction_template_id:
            template_contract = await get_template_contract(
                session=self.session,
                template_id=extraction_template_id
            )
            # Get template name
            template_config = await self.session.get(UserExtractionConfig, extraction_template_id)
            if template_config:
                template_name = template_config.name

        # 4. Build combined contract
        combined_contract = build_mail_watcher_contract(
            name=script.name,
            template_contract=template_contract,
            email_account=email_account,
            folder=folder,
            filters=filters
        )

        # 5. Update script with contract
        script.ui_contract = combined_contract

        # 6. Generate README
        try:
            field_names = []
            if template_contract and template_contract.get("outputs"):
                field_names = [f["name"] for f in template_contract["outputs"]]

            readme_content = generate_mail_watcher_readme(
                name=script.name,
                email_account=email_account,
                folder=folder,
                template_name=template_name,
                field_names=field_names,
                filters=filters
            )

            # Save README
            doc_path = DOCS_DIR / f"{script_id}_mail_watcher.md"
            doc_path.write_text(readme_content, encoding='utf-8')
            script.doc_path = doc_path.name

            logger.info(f"MailWatcher README generated: {script.doc_path}")

        except Exception as e:
            logger.warning(f"Error generating MailWatcher README: {e}")
            script.doc_path = None

        # 7. Set status if requested
        if target_status:
            script.status = target_status
            logger.info(f"Promocionando MailWatcher {script_id} a estado {target_status}")

        # 8. Persistir cambios
        self.session.add(script)
        await self.session.commit()
        await self.session.refresh(script)

        logger.info(f"MailWatcher {script_id} sellado exitosamente")
        return script

    async def seal_connection_resource(
        self,
        connection_id: int,
        step_type: StepType,
        target_status: Optional[str] = None
    ) -> ScriptLibrary:
        """
        Sella una conexión (API, SQL, etc.) creando o actualizando su entrada en la biblioteca.
        """
        # 1. Obtener o crear el registro en la biblioteca
        script = await self._get_or_create_connection_script(connection_id, step_type)
        
        # 2. Delegar a MailWatcher si aplica (usa lógica heredada compleja)
        if step_type == StepType.EMAIL:
            return await self.seal_mail_watcher(script.id, target_status=target_status)
            
        # 3. Generar el contrato usando el builder apropiado
        contract = None
        if step_type == StepType.API_FETCH:
            config = await self.session.get(APIEndpointConfig, connection_id)
            contract = build_api_fetch_contract(config)
        elif step_type == StepType.SQL_QUERY:
            config = await self.session.get(DatabaseCredentialConfig, connection_id)
            contract = build_sql_query_contract(config)
        elif step_type == StepType.CONNECTION: # Folder Watcher
            trigger = await self.session.get(TriggerConfig, connection_id)
            if trigger and trigger.type == 'folder_watcher':
                config_data = {
                    'name': trigger.name,
                    'watch_path': trigger.configuration.get('watch_path', ''),
                    'file_patterns': ','.join(trigger.file_extensions or ['*']),
                    'recursive': trigger.configuration.get('recursive', False),
                }
            else:
                config_data = {}
            contract = build_folder_watcher_contract(config_data)
        elif step_type == StepType.WEBHOOK:
            flow = await self.session.get(FlowRegistry, connection_id)
            contract = build_webhook_contract({'name': flow.name if flow else 'Webhook'})
        elif step_type == StepType.WEB_WATCHER:
            from automatia_shared.contracts.ui_contract import DataContract, UIContract, OutputSchema
            contract = DataContract(
                version="1.0.0",
                inputs=UIContract(inputs=[]),
                outputs=OutputSchema(fields=[]),
                description="Monitor Web"
            )
        elif step_type == StepType.EMAIL_WATCHER:
            from automatia_shared.contracts.ui_contract import DataContract, UIContract, OutputSchema
            contract = DataContract(
                version="1.0.0",
                inputs=UIContract(inputs=[]),
                outputs=OutputSchema(fields=[]),
                description="Monitor de Email"
            )

        if not contract:
            raise ValueError(f"No se pudo construir contrato para {step_type}")
            
        # 4. Actualizar registro
        script.ui_contract = contract.model_dump()
        script.data_contract = contract.model_dump() # Por ahora usamos el mismo para ambos
        
        # 5. Generar README
        try:
            readme_content = doc_generator.build_readme_content(contract)
            doc_path = DOCS_DIR / f"conn_{script.source_module}_{connection_id}.md"
            doc_path.write_text(readme_content, encoding='utf-8')
            script.doc_path = doc_path.name
        except Exception as e:
            logger.warning(f"Error generando documentación de conexión: {e}")
            
        if target_status:
            script.status = target_status
            
        self.session.add(script)
        await self.session.commit()
        await self.session.refresh(script)
        
        return script

    async def _get_or_create_connection_script(self, connection_id: int, step_type: StepType) -> ScriptLibrary:
        """Busca o crea una entrada en ScriptLibrary para una conexión."""
        from sqlmodel import select
        
        mapping = {
            StepType.API_FETCH: 'api',
            StepType.SQL_QUERY: 'sql',
            StepType.EMAIL: 'email',
            StepType.CONNECTION: 'folders',
            StepType.WEBHOOK: 'webhook',
            StepType.WEB_WATCHER: 'web',
            StepType.EMAIL_WATCHER: 'email_watcher'
        }
        
        module = mapping.get(step_type)
        if not module:
            raise ValueError(f"Tipo de paso no soportado para sellado de conexión: {step_type}")
            
        stmt = select(ScriptLibrary).where(
            ScriptLibrary.source_module == module,
            ScriptLibrary.source_automation_id == connection_id
        )
        result = await self.session.execute(stmt)
        script = result.scalars().first()
        
        if not script:
            # Crear entrada básica
            name = f"Conexión {module.upper()} #{connection_id}"
            
            # Intentar obtener nombre real
            if step_type == StepType.API_FETCH:
                config = await self.session.get(APIEndpointConfig, connection_id)
                if config: name = config.name
            elif step_type == StepType.SQL_QUERY:
                config = await self.session.get(DatabaseCredentialConfig, connection_id)
                if config: name = config.name
            elif step_type == StepType.WEBHOOK:
                flow = await self.session.get(FlowRegistry, connection_id)
                if flow: name = flow.name
            elif step_type == StepType.EMAIL_WATCHER:
                config = await self.session.get(TriggerConfig, connection_id)
                if config: name = config.name
                
            script = ScriptLibrary(
                source_module=module,
                source_automation_id=connection_id,
                name=name,
                status='published',
                script_path="", # No hay archivo .py asociado
                code_hash=f"conn_{module}_{connection_id}",
                tags=['conexión', module]
            )
            self.session.add(script)
            await self.session.flush()
            await self.session.refresh(script)
            
        return script

    def _get_script_code(self, script: ScriptLibrary) -> str:
        """
        Recupera el código fuente de un script, priorizando el contenido en base de datos
        y recurriendo al archivo físico en disco si es necesario.

        Args:
            script: Objeto ScriptLibrary del cual obtener el código.

        Returns:
            El código fuente como cadena de texto. Si no hay código disponible, retorna una cadena vacía.
        """
        # Intentar obtener de memoria
        if script.code:
            return script.code

        # Intentar leer de archivo
        if script.script_path:
            file_path = SCRIPTS_DIR / script.script_path
            if file_path.exists():
                try:
                    return file_path.read_text(encoding='utf-8')
                except Exception as e:
                    logger.warning(f"Error leyendo archivo {file_path}: {e}")

        # Si no hay codigo disponible, retornar vacio
        return ""


# Instancia singleton para uso global
asset_finishing_service = AssetFinishingService
