"""
Servicio de exportación de automatismos.
Prompts 2.1 y 2.2 del sistema de exportación/importación de automatismos.

Permite exportar scripts, playbooks y workflows a paquetes .automatia (ZIP) con:
- Firma del manifiesto para verificación de integridad
- Metadatos de origen (licencia, cliente, partner)
- Estructura de carpetas organizada
- Resolución de dependencias recursivas para workflows
"""

import zipfile
import json
import hashlib
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from io import BytesIO

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.database.models import (
    CustomScript,
    RpaPlaybook,
    FlowRegistry,
    ServerConnection,
    calculate_playbook_hash
)
from client_app.app.services.manifest_generator import manifest_generator
from client_app.app.services.manifest_signature_service import manifest_signature_service


class AutomatismExportService:
    """
    Servicio para exportar automatismos a paquetes .automatia.

    Un paquete .automatia es un archivo ZIP con la siguiente estructura:
    ```
    package.automatia
    |- manifest.json          # Metadatos y firma
    |- scripts/
    |  |- script_name.py      # Codigo de scripts
    |- playbooks/
    |  |- playbook_name.json  # Acciones de playbooks
    |- metadata/
    |  |- scripts/
    |  |  |- script_name.json # Metadatos del script
    |  |- playbooks/
    |     |- playbook_name.json # Metadatos del playbook
    ```
    """

    def __init__(self):
        """Inicializa el servicio con las dependencias necesarias."""
        self.manifest_generator = manifest_generator
        self.signature_service = manifest_signature_service

    async def export_package(
        self,
        name: str,
        script_ids: Optional[List[int]] = None,
        playbook_ids: Optional[List[int]] = None,
        description: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Union[bytes, str]:
        """
        Exporta scripts y/o playbooks a un paquete .automatia.

        Este metodo:
        1. Carga los scripts y playbooks solicitados de la BD
        2. Genera metadatos para cada elemento
        3. Crea el manifiesto con hashes de todos los archivos
        4. Firma el manifiesto con las credenciales del cliente
        5. Empaqueta todo en un archivo ZIP

        Args:
            name: Nombre descriptivo del paquete
            script_ids: Lista de IDs de CustomScript a exportar
            playbook_ids: Lista de IDs de RpaPlaybook a exportar
            description: Descripcion opcional del paquete
            output_path: Ruta de salida (si None, retorna bytes)

        Returns:
            bytes del ZIP si output_path es None, o la ruta al archivo guardado

        Raises:
            ValueError: Si no se especifican scripts ni playbooks
        """
        if not script_ids and not playbook_ids:
            raise ValueError("Debe especificar al menos un script o playbook para exportar")

        files: Dict[str, bytes] = {}

        # 1. Recopilar scripts
        if script_ids:
            scripts = await self._load_scripts(script_ids)
            for script in scripts:
                # Archivo de codigo
                files[f"scripts/{script.name}.py"] = script.code.encode('utf-8')

                # Metadatos del script
                meta = self._create_script_metadata(script)
                files[f"metadata/scripts/{script.name}.json"] = json.dumps(
                    meta, indent=2, ensure_ascii=False
                ).encode('utf-8')

        # 2. Recopilar playbooks
        if playbook_ids:
            playbooks = await self._load_playbooks(playbook_ids)
            for playbook in playbooks:
                # Archivo de acciones
                actions_json = self._get_playbook_actions_json(playbook)
                files[f"playbooks/{playbook.name}.json"] = actions_json.encode('utf-8')

                # Metadatos del playbook
                meta = self._create_playbook_metadata(playbook, actions_json)
                files[f"metadata/playbooks/{playbook.name}.json"] = json.dumps(
                    meta, indent=2, ensure_ascii=False
                ).encode('utf-8')

        # 3. Obtener informacion de origen
        source_info = await self._get_source_info()

        # 4. Generar manifiesto
        manifest_json = self.manifest_generator.generate(
            package_name=name,
            source_info=source_info,
            files=files,
            description=description
        )

        # 5. Firmar manifiesto (como cliente)
        signature = self.signature_service.sign_as_client(
            manifest_json,
            source_info['license_key'],
            source_info['machine_id']
        )
        signed_manifest = self.manifest_generator.add_signature(manifest_json, signature)
        files['manifest.json'] = signed_manifest.encode('utf-8')

        # 6. Crear ZIP
        return self._create_zip(files, output_path)

    async def _load_scripts(self, script_ids: List[int]) -> List[CustomScript]:
        """
        Carga scripts de la base de datos por sus IDs.

        Args:
            script_ids: Lista de IDs de scripts a cargar

        Returns:
            Lista de objetos CustomScript
        """
        async with AsyncSession(client_engine) as session:
            result = await session.exec(
                select(CustomScript).where(CustomScript.id.in_(script_ids))
            )
            return list(result.all())

    async def _load_playbooks(self, playbook_ids: List[int]) -> List[RpaPlaybook]:
        """
        Carga playbooks de la base de datos por sus IDs.

        Args:
            playbook_ids: Lista de IDs de playbooks a cargar

        Returns:
            Lista de objetos RpaPlaybook
        """
        async with AsyncSession(client_engine) as session:
            result = await session.exec(
                select(RpaPlaybook).where(RpaPlaybook.id.in_(playbook_ids))
            )
            return list(result.all())

    async def _get_source_info(self) -> Dict[str, str]:
        """
        Obtiene informacion del cliente para el manifiesto.

        Obtiene de la configuracion local:
        - license_id: Derivado de license_key
        - client_id: Derivado de license_key (simplificado)
        - partner_id: Default si no hay servidor conectado
        - machine_id: Generado o almacenado localmente
        - license_key: Clave de licencia para firmar

        Returns:
            Diccionario con informacion de origen
        """
        async with AsyncSession(client_engine) as session:
            result = await session.exec(
                select(ServerConnection).where(ServerConnection.is_active == True)
            )
            connection = result.first()

            if connection:
                # Derivar IDs de la licencia
                license_key = connection.license_key
                license_id = self._derive_license_id(license_key)
                machine_id = self._get_or_create_machine_id()

                return {
                    "license_id": license_id,
                    "client_id": f"CLI-{license_id[:8]}",
                    "partner_id": self._extract_partner_id(license_key),
                    "machine_id": machine_id,
                    "license_key": license_key
                }
            else:
                # Sin conexion configurada, usar valores por defecto
                return {
                    "license_id": "LOCAL-NO-LICENSE",
                    "client_id": "LOCAL-CLIENT",
                    "partner_id": "LOCAL-PARTNER",
                    "machine_id": self._get_or_create_machine_id(),
                    "license_key": "local-export-key"
                }

    def _derive_license_id(self, license_key: str) -> str:
        """
        Deriva un ID de licencia del license_key.

        Usa SHA256 truncado para generar un identificador corto pero unico.

        Args:
            license_key: Clave de licencia

        Returns:
            ID de licencia derivado (12 caracteres)
        """
        hash_value = hashlib.sha256(license_key.encode()).hexdigest()
        return f"LIC-{hash_value[:8].upper()}"

    def _extract_partner_id(self, license_key: str) -> str:
        """
        Extrae o deriva el ID de partner del license_key.

        En un sistema completo, esto vendria del servidor.
        Por ahora, derivamos un ID del hash de la licencia.

        Args:
            license_key: Clave de licencia

        Returns:
            ID de partner
        """
        # Patron: usar parte diferente del hash para partner
        hash_value = hashlib.sha256(f"partner:{license_key}".encode()).hexdigest()
        return f"PARTNER-{hash_value[:6].upper()}"

    def _get_or_create_machine_id(self) -> str:
        """
        Obtiene o genera un ID unico para esta maquina.

        Intenta obtener un identificador estable de la maquina.
        Si no es posible, genera uno basado en el hardware disponible.

        Returns:
            ID de maquina unico
        """
        import platform
        import uuid

        # Intentar obtener ID de maquina del sistema
        try:
            # En Windows, usar el numero de serie del disco
            if platform.system() == "Windows":
                import subprocess
                result = subprocess.run(
                    ['wmic', 'csproduct', 'get', 'UUID'],
                    capture_output=True,
                    text=True
                )
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    machine_uuid = lines[1].strip()
                    if machine_uuid and machine_uuid != "":
                        return f"WIN-{machine_uuid[:12]}"
        except Exception:
            pass

        # Fallback: usar direccion MAC
        try:
            mac = hex(uuid.getnode())[2:].upper()
            return f"MAC-{mac}"
        except Exception:
            pass

        # Ultimo recurso: generar UUID aleatorio
        return f"RND-{uuid.uuid4().hex[:12].upper()}"

    def _create_script_metadata(self, script: CustomScript) -> Dict[str, Any]:
        """
        Crea el diccionario de metadatos para un script.

        Args:
            script: Objeto CustomScript

        Returns:
            Diccionario con metadatos del script
        """
        return {
            "id": script.id,
            "name": script.name,
            "status": script.status,
            "code_hash": script.code_hash,
            "description": script.description,
            "input_type": getattr(script, 'input_type', 'file'),
            "output_type": getattr(script, 'output_type', 'file'),
            "tags": getattr(script, 'tags', []),
            "required_libraries": getattr(script, 'required_libraries', [])
        }

    def _create_playbook_metadata(
        self,
        playbook: RpaPlaybook,
        actions_json: str
    ) -> Dict[str, Any]:
        """
        Crea el diccionario de metadatos para un playbook.

        Args:
            playbook: Objeto RpaPlaybook
            actions_json: JSON de las acciones (para calcular hash)

        Returns:
            Diccionario con metadatos del playbook
        """
        return {
            "id": playbook.id,
            "name": playbook.name,
            "description": playbook.description,
            "base_url": getattr(playbook, 'base_url', ''),
            "content_hash": calculate_playbook_hash(actions_json)
        }

    def _get_playbook_actions_json(self, playbook: RpaPlaybook) -> str:
        """
        Obtiene las acciones del playbook como JSON string.

        Maneja tanto el caso donde actions es un string como cuando es una lista.

        Args:
            playbook: Objeto RpaPlaybook

        Returns:
            JSON string de las acciones
        """
        actions = playbook.actions
        if isinstance(actions, str):
            return actions
        else:
            return json.dumps(actions, indent=2, ensure_ascii=False)

    # =========================================================================
    # EXPORTACION DE WORKFLOWS (Prompt 2.2)
    # =========================================================================

    async def export_workflow(
        self,
        flow_id: int,
        name: Optional[str] = None,
        include_dependencies: bool = True,
        description: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Union[bytes, str]:
        """
        Exporta un workflow completo con sus dependencias.

        Este metodo:
        1. Carga el workflow de la base de datos
        2. Analiza los pasos para encontrar dependencias (scripts, playbooks)
        3. Incluye todas las dependencias si se solicita
        4. Genera el manifiesto con la lista de dependencias
        5. Firma y empaqueta todo

        Args:
            flow_id: ID del FlowRegistry a exportar
            name: Nombre del paquete (default: nombre del workflow)
            include_dependencies: Si incluir scripts/playbooks referenciados
            description: Descripcion opcional del paquete
            output_path: Ruta de salida (si None, retorna bytes)

        Returns:
            bytes del ZIP si output_path es None, o la ruta al archivo guardado
        """
        files: Dict[str, bytes] = {}

        # 1. Cargar workflow
        flow = await self._load_flow(flow_id)
        if not flow:
            raise ValueError(f"Workflow con ID {flow_id} no encontrado")

        flow_name = name or flow.name

        # 2. Exportar definicion del workflow
        flow_spec = self._flow_to_spec(flow)
        files[f"workflows/{flow.name}.json"] = json.dumps(
            flow_spec, indent=2, ensure_ascii=False
        ).encode('utf-8')

        # 3. Resolver dependencias si aplica
        dependency_scripts: List[str] = []
        dependency_playbooks: List[str] = []

        if include_dependencies:
            deps = await self._resolve_workflow_dependencies(flow)

            # Scripts dependientes
            for script in deps['scripts']:
                files[f"scripts/{script.name}.py"] = script.code.encode('utf-8')
                meta = self._create_script_metadata(script)
                files[f"metadata/scripts/{script.name}.json"] = json.dumps(
                    meta, indent=2, ensure_ascii=False
                ).encode('utf-8')
                dependency_scripts.append(script.name)

            # Playbooks dependientes
            for playbook in deps['playbooks']:
                actions_json = self._get_playbook_actions_json(playbook)
                files[f"playbooks/{playbook.name}.json"] = actions_json.encode('utf-8')
                meta = self._create_playbook_metadata(playbook, actions_json)
                files[f"metadata/playbooks/{playbook.name}.json"] = json.dumps(
                    meta, indent=2, ensure_ascii=False
                ).encode('utf-8')
                dependency_playbooks.append(playbook.name)

        # 4. Obtener info de origen
        source_info = await self._get_source_info()

        # 5. Generar manifiesto (con dependencias)
        manifest_json = self.manifest_generator.generate(
            package_name=flow_name,
            source_info=source_info,
            files=files,
            description=description or flow.description
        )

        # Agregar dependencias al manifest
        if include_dependencies and (dependency_scripts or dependency_playbooks):
            manifest_json = self._add_dependencies_to_manifest(
                manifest_json,
                dependency_scripts,
                dependency_playbooks
            )

        # 6. Firmar manifiesto
        signature = self.signature_service.sign_as_client(
            manifest_json,
            source_info['license_key'],
            source_info['machine_id']
        )
        signed_manifest = self.manifest_generator.add_signature(manifest_json, signature)
        files['manifest.json'] = signed_manifest.encode('utf-8')

        # 7. Crear ZIP
        return self._create_zip(files, output_path)

    async def _load_flow(self, flow_id: int) -> Optional[FlowRegistry]:
        """
        Carga un workflow de la base de datos por su ID.

        Args:
            flow_id: ID del workflow a cargar

        Returns:
            Objeto FlowRegistry o None si no existe
        """
        async with AsyncSession(client_engine) as session:
            result = await session.exec(
                select(FlowRegistry).where(FlowRegistry.id == flow_id)
            )
            return result.first()

    async def _load_script(self, script_id: int) -> Optional[CustomScript]:
        """
        Carga un script individual de la base de datos.

        Args:
            script_id: ID del script a cargar

        Returns:
            Objeto CustomScript o None si no existe
        """
        async with AsyncSession(client_engine) as session:
            result = await session.exec(
                select(CustomScript).where(CustomScript.id == script_id)
            )
            return result.first()

    async def _load_playbook(self, playbook_id: int) -> Optional[RpaPlaybook]:
        """
        Carga un playbook individual de la base de datos.

        Args:
            playbook_id: ID del playbook a cargar

        Returns:
            Objeto RpaPlaybook o None si no existe
        """
        async with AsyncSession(client_engine) as session:
            result = await session.exec(
                select(RpaPlaybook).where(RpaPlaybook.id == playbook_id)
            )
            return result.first()

    async def _resolve_workflow_dependencies(self, flow: FlowRegistry) -> Dict[str, List]:
        """
        Analiza los pasos del workflow y extrae dependencias.

        Busca en step.config:
        - script_id -> CustomScript
        - playbook_id -> RpaPlaybook

        Args:
            flow: Objeto FlowRegistry a analizar

        Returns:
            Diccionario con listas de scripts y playbooks dependientes
        """
        scripts: List[CustomScript] = []
        playbooks: List[RpaPlaybook] = []
        seen_script_ids: set = set()
        seen_playbook_ids: set = set()

        # Parsear steps (puede ser string JSON o lista)
        steps = flow.steps
        if isinstance(steps, str):
            steps = json.loads(steps)

        for step in steps:
            config = step.get('config', {})

            # Script personalizado
            script_id = config.get('script_id')
            if script_id and script_id not in seen_script_ids:
                script = await self._load_script(script_id)
                if script:
                    scripts.append(script)
                    seen_script_ids.add(script_id)

            # Playbook RPA
            playbook_id = config.get('playbook_id')
            if playbook_id and playbook_id not in seen_playbook_ids:
                playbook = await self._load_playbook(playbook_id)
                if playbook:
                    playbooks.append(playbook)
                    seen_playbook_ids.add(playbook_id)

        return {'scripts': scripts, 'playbooks': playbooks}

    def _flow_to_spec(self, flow: FlowRegistry) -> Dict[str, Any]:
        """
        Convierte un FlowRegistry a diccionario exportable.

        Args:
            flow: Objeto FlowRegistry

        Returns:
            Diccionario con la especificacion del workflow
        """
        # Parsear steps
        steps = flow.steps
        if isinstance(steps, str):
            steps = json.loads(steps)

        # Parsear trigger_config
        trigger_config = flow.trigger_config
        if isinstance(trigger_config, str):
            try:
                trigger_config = json.loads(trigger_config)
            except json.JSONDecodeError:
                trigger_config = {}

        return {
            "name": flow.name,
            "description": flow.description,
            "version": flow.version,
            "status": flow.status,
            "trigger_type": flow.trigger_type,
            "trigger_config": trigger_config,
            "steps": steps,
            "is_active": flow.is_active,
            "owner_scope": flow.owner_scope
        }

    def _add_dependencies_to_manifest(
        self,
        manifest_json: str,
        scripts: List[str],
        playbooks: List[str]
    ) -> str:
        """
        Agrega la seccion de dependencias al manifiesto.

        Args:
            manifest_json: JSON del manifiesto sin dependencias
            scripts: Lista de nombres de scripts dependientes
            playbooks: Lista de nombres de playbooks dependientes

        Returns:
            JSON del manifiesto con dependencias agregadas
        """
        manifest = json.loads(manifest_json)
        manifest['dependencies'] = {
            'scripts': scripts,
            'playbooks': playbooks
        }
        return json.dumps(manifest, sort_keys=True, indent=2)

    def _create_zip(
        self,
        files: Dict[str, bytes],
        output_path: Optional[str] = None
    ) -> Union[bytes, str]:
        """
        Crea el archivo ZIP del paquete.

        Args:
            files: Diccionario {ruta: contenido} de archivos a incluir
            output_path: Ruta de salida opcional

        Returns:
            bytes del ZIP si output_path es None, o la ruta al archivo guardado
        """
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filepath, content in files.items():
                zf.writestr(filepath, content)

        if output_path:
            Path(output_path).write_bytes(buffer.getvalue())
            return output_path

        return buffer.getvalue()


# Singleton del servicio
automatism_export_service = AutomatismExportService()
