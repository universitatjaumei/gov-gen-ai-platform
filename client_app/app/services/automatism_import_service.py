"""
Servicio de importacion de automatismos.
Prompt 3.2 del sistema de exportacion/importacion de automatismos.

Importa scripts, playbooks y workflows desde paquetes .automatia validados.
"""

import zipfile
import json
import hashlib
import uuid
from io import BytesIO
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.database.models import (
    CustomScript,
    RpaPlaybook,
    FlowRegistry,
    AutomatismPackage,
    PackageType,
    PackageStatus,
    calculate_playbook_hash
)
from client_app.app.services.import_validation_service import (
    import_validation_service,
    ImportPermission,
    ValidationResult
)


class ConflictResolution(str, Enum):
    """Estrategias de resolucion de conflictos."""
    RENAME = "rename"       # Renombrar el elemento importado
    OVERWRITE = "overwrite" # Sobrescribir el elemento local
    SKIP = "skip"           # Omitir la importacion de este elemento


@dataclass
class ImportResult:
    """Resultado de la importacion de un paquete."""
    success: bool
    scripts_imported: int = 0
    playbooks_imported: int = 0
    workflows_imported: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    imported_ids: Dict[str, List[int]] = field(default_factory=lambda: {
        "scripts": [],
        "playbooks": [],
        "workflows": []
    })


class AutomatismImportService:
    """
    Servicio para importar paquetes .automatia validados.

    Proceso de importacion:
    1. Validar el paquete (integridad, firma, permisos)
    2. Verificar permisos de importacion
    3. Resolver conflictos segun estrategia indicada
    4. Importar scripts, playbooks y workflows
    5. Registrar el paquete importado
    """

    def __init__(self):
        """Inicializa el servicio."""
        self._validation_service = import_validation_service

    async def import_package(
        self,
        package_bytes: bytes,
        conflict_resolutions: Optional[Dict[str, ConflictResolution]] = None,
        partner_approval_token: Optional[str] = None
    ) -> ImportResult:
        """
        Importa un paquete .automatia validado.

        Args:
            package_bytes: Contenido del archivo .automatia
            conflict_resolutions: {nombre: resolucion} para conflictos
            partner_approval_token: Token si requiere aprobacion partner

        Returns:
            ImportResult con estadisticas y errores

        Raises:
            ValueError: Si el paquete es invalido
            PermissionError: Si no tiene permiso para importar
        """
        conflict_resolutions = conflict_resolutions or {}

        # 1. Validar paquete
        validation = await self._validate_package(package_bytes)

        if not validation.is_valid:
            raise ValueError(f"Paquete invalido: {', '.join(validation.errors)}")

        # 2. Verificar permisos
        if validation.permission == ImportPermission.DENIED:
            raise PermissionError("No tiene permiso para importar de otro partner")

        if validation.permission == ImportPermission.REQUIRES_PARTNER:
            if not partner_approval_token:
                raise PermissionError("Requiere aprobacion del partner para importar")
            # Verificar token
            token_valid = await self._verify_partner_token(partner_approval_token)
            if not token_valid:
                raise PermissionError("Token de aprobacion invalido o expirado")

        # 3. Extraer archivos
        files = self._extract_zip(package_bytes)
        manifest = validation.manifest

        # 4. Generar UUID para el paquete
        package_id = str(uuid.uuid4())

        # 5. Determinar estado de scripts importados
        target_status = self._determine_import_status(manifest)

        # 6. Preparar tracking
        result = ImportResult(success=True)
        source_info = manifest.get("source", {})

        # 7. Importar scripts
        for script_file in manifest.get("contents", {}).get("scripts", []):
            script_name = script_file.replace(".py", "")

            # Verificar si hay conflicto
            conflict = self._find_conflict(script_name, "script", validation.conflicts)
            resolution = conflict_resolutions.get(script_name)

            if conflict:
                if resolution == ConflictResolution.SKIP:
                    result.skipped += 1
                    continue
                elif resolution == ConflictResolution.OVERWRITE:
                    script_id = await self._import_script_overwrite(
                        files, script_file, manifest, conflict["local_id"],
                        source_info, package_id, target_status
                    )
                else:  # RENAME por defecto
                    script_id = await self._import_script_rename(
                        files, script_file, manifest,
                        source_info, package_id, target_status
                    )
            else:
                script_id = await self._import_script(
                    files, script_file, manifest,
                    source_info, package_id, target_status
                )

            if script_id:
                result.scripts_imported += 1
                result.imported_ids["scripts"].append(script_id)

        # 8. Importar playbooks
        for playbook_file in manifest.get("contents", {}).get("playbooks", []):
            playbook_name = playbook_file.replace(".json", "")

            conflict = self._find_conflict(playbook_name, "playbook", validation.conflicts)
            resolution = conflict_resolutions.get(playbook_name)

            if conflict:
                if resolution == ConflictResolution.SKIP:
                    result.skipped += 1
                    continue
                elif resolution == ConflictResolution.OVERWRITE:
                    playbook_id = await self._import_playbook_overwrite(
                        files, playbook_file, manifest, conflict["local_id"],
                        source_info, package_id
                    )
                else:  # RENAME
                    playbook_id = await self._import_playbook_rename(
                        files, playbook_file, manifest,
                        source_info, package_id
                    )
            else:
                playbook_id = await self._import_playbook(
                    files, playbook_file, manifest,
                    source_info, package_id
                )

            if playbook_id:
                result.playbooks_imported += 1
                result.imported_ids["playbooks"].append(playbook_id)

        # 9. Importar workflows
        for workflow_file in manifest.get("contents", {}).get("workflows", []):
            workflow_id = await self._import_workflow(
                files, workflow_file, manifest,
                source_info, package_id
            )
            if workflow_id:
                result.workflows_imported += 1
                result.imported_ids["workflows"].append(workflow_id)

        # 10. Registrar paquete importado
        await self._record_import(manifest, validation, package_id)

        return result

    async def _validate_package(self, package_bytes: bytes) -> ValidationResult:
        """Valida el paquete usando el servicio de validacion."""
        return await self._validation_service.validate_package(package_bytes)

    def _extract_zip(self, package_bytes: bytes) -> Dict[str, bytes]:
        """Extrae el contenido del ZIP."""
        files = {}
        with zipfile.ZipFile(BytesIO(package_bytes), 'r') as zf:
            for name in zf.namelist():
                files[name.replace('\\', '/')] = zf.read(name)
        return files

    def _determine_import_status(self, manifest: Dict[str, Any]) -> str:
        """
        Determina el estado de los scripts importados.

        - Firma PARTNER -> published
        - Firma CLIENT misma licencia -> mantener original
        - Firma CLIENT otra licencia -> draft
        """
        signature = manifest.get("signature", {})
        if signature.get("type") == "PARTNER":
            return "published"
        return "draft"

    def _find_conflict(
        self,
        name: str,
        item_type: str,
        conflicts: List[Dict]
    ) -> Optional[Dict]:
        """Busca un conflicto por nombre y tipo."""
        for conflict in conflicts:
            if conflict["name"] == name and conflict["type"] == item_type:
                return conflict
        return None

    async def _import_script(
        self,
        files: Dict[str, bytes],
        script_file: str,
        manifest: Dict[str, Any],
        source_info: Dict[str, str],
        package_id: str,
        target_status: str
    ) -> Optional[int]:
        """Importa un script nuevo."""
        script_name = script_file.replace(".py", "")
        script_path = f"scripts/{script_file}"
        meta_path = f"metadata/scripts/{script_name}.json"

        if script_path not in files:
            return None

        code = files[script_path].decode('utf-8')

        # Cargar metadatos si existen
        metadata = {}
        if meta_path in files:
            try:
                metadata = json.loads(files[meta_path].decode('utf-8'))
            except json.JSONDecodeError:
                pass

        script_data = {
            'name': script_name,
            'code': code,
            'status': target_status,
            'description': metadata.get('description', f'Importado desde {manifest.get("name", "paquete")}'),
            'code_hash': hashlib.sha256(code.encode()).hexdigest(),
            'origin_license_id': source_info.get('license_id'),
            'origin_package_id': package_id,
            'original_status': metadata.get('status'),
            'input_type': metadata.get('input_type', 'file'),
            'output_type': metadata.get('output_type', 'file'),
            'tags': metadata.get('tags', []),
            'required_libraries': metadata.get('required_libraries', [])
        }

        return await self._save_script(script_data)

    async def _import_script_rename(
        self,
        files: Dict[str, bytes],
        script_file: str,
        manifest: Dict[str, Any],
        source_info: Dict[str, str],
        package_id: str,
        target_status: str
    ) -> Optional[int]:
        """Importa un script con nombre modificado."""
        script_name = script_file.replace(".py", "")
        script_path = f"scripts/{script_file}"
        meta_path = f"metadata/scripts/{script_name}.json"

        if script_path not in files:
            return None

        code = files[script_path].decode('utf-8')

        metadata = {}
        if meta_path in files:
            try:
                metadata = json.loads(files[meta_path].decode('utf-8'))
            except json.JSONDecodeError:
                pass

        # Generar nombre unico
        new_name = await self._generate_unique_name(script_name, "script")

        script_data = {
            'name': new_name,
            'code': code,
            'status': target_status,
            'description': metadata.get('description', f'Importado desde {manifest.get("name", "paquete")}'),
            'code_hash': hashlib.sha256(code.encode()).hexdigest(),
            'origin_license_id': source_info.get('license_id'),
            'origin_package_id': package_id,
            'original_status': metadata.get('status'),
            'input_type': metadata.get('input_type', 'file'),
            'output_type': metadata.get('output_type', 'file'),
            'tags': metadata.get('tags', []),
            'required_libraries': metadata.get('required_libraries', [])
        }

        return await self._save_script(script_data)

    async def _import_script_overwrite(
        self,
        files: Dict[str, bytes],
        script_file: str,
        manifest: Dict[str, Any],
        local_id: int,
        source_info: Dict[str, str],
        package_id: str,
        target_status: str
    ) -> Optional[int]:
        """Sobrescribe un script existente."""
        script_name = script_file.replace(".py", "")
        script_path = f"scripts/{script_file}"
        meta_path = f"metadata/scripts/{script_name}.json"

        if script_path not in files:
            return None

        code = files[script_path].decode('utf-8')

        metadata = {}
        if meta_path in files:
            try:
                metadata = json.loads(files[meta_path].decode('utf-8'))
            except json.JSONDecodeError:
                pass

        script_data = {
            'id': local_id,
            'name': script_name,
            'code': code,
            'status': target_status,
            'description': metadata.get('description', f'Actualizado desde {manifest.get("name", "paquete")}'),
            'code_hash': hashlib.sha256(code.encode()).hexdigest(),
            'origin_license_id': source_info.get('license_id'),
            'origin_package_id': package_id,
            'original_status': metadata.get('status')
        }

        return await self._update_script(script_data)

    async def _import_playbook(
        self,
        files: Dict[str, bytes],
        playbook_file: str,
        manifest: Dict[str, Any],
        source_info: Dict[str, str],
        package_id: str
    ) -> Optional[int]:
        """Importa un playbook nuevo."""
        playbook_name = playbook_file.replace(".json", "")
        playbook_path = f"playbooks/{playbook_file}"
        meta_path = f"metadata/playbooks/{playbook_name}.json"

        if playbook_path not in files:
            return None

        actions_json = files[playbook_path].decode('utf-8')

        metadata = {}
        if meta_path in files:
            try:
                metadata = json.loads(files[meta_path].decode('utf-8'))
            except json.JSONDecodeError:
                pass

        playbook_data = {
            'name': playbook_name,
            'actions': actions_json,
            'description': metadata.get('description', f'Importado desde {manifest.get("name", "paquete")}'),
            'base_url': metadata.get('base_url', ''),
            'content_hash': calculate_playbook_hash(actions_json),
            'origin_license_id': source_info.get('license_id'),
            'origin_package_id': package_id
        }

        return await self._save_playbook(playbook_data)

    async def _import_playbook_rename(
        self,
        files: Dict[str, bytes],
        playbook_file: str,
        manifest: Dict[str, Any],
        source_info: Dict[str, str],
        package_id: str
    ) -> Optional[int]:
        """Importa un playbook con nombre modificado."""
        playbook_name = playbook_file.replace(".json", "")
        playbook_path = f"playbooks/{playbook_file}"
        meta_path = f"metadata/playbooks/{playbook_name}.json"

        if playbook_path not in files:
            return None

        actions_json = files[playbook_path].decode('utf-8')

        metadata = {}
        if meta_path in files:
            try:
                metadata = json.loads(files[meta_path].decode('utf-8'))
            except json.JSONDecodeError:
                pass

        new_name = await self._generate_unique_name(playbook_name, "playbook")

        playbook_data = {
            'name': new_name,
            'actions': actions_json,
            'description': metadata.get('description', f'Importado desde {manifest.get("name", "paquete")}'),
            'base_url': metadata.get('base_url', ''),
            'content_hash': calculate_playbook_hash(actions_json),
            'origin_license_id': source_info.get('license_id'),
            'origin_package_id': package_id
        }

        return await self._save_playbook(playbook_data)

    async def _import_playbook_overwrite(
        self,
        files: Dict[str, bytes],
        playbook_file: str,
        manifest: Dict[str, Any],
        local_id: int,
        source_info: Dict[str, str],
        package_id: str
    ) -> Optional[int]:
        """Sobrescribe un playbook existente."""
        playbook_name = playbook_file.replace(".json", "")
        playbook_path = f"playbooks/{playbook_file}"
        meta_path = f"metadata/playbooks/{playbook_name}.json"

        if playbook_path not in files:
            return None

        actions_json = files[playbook_path].decode('utf-8')

        metadata = {}
        if meta_path in files:
            try:
                metadata = json.loads(files[meta_path].decode('utf-8'))
            except json.JSONDecodeError:
                pass

        playbook_data = {
            'id': local_id,
            'name': playbook_name,
            'actions': actions_json,
            'description': metadata.get('description', f'Actualizado desde {manifest.get("name", "paquete")}'),
            'base_url': metadata.get('base_url', ''),
            'content_hash': calculate_playbook_hash(actions_json),
            'origin_license_id': source_info.get('license_id'),
            'origin_package_id': package_id
        }

        return await self._update_playbook(playbook_data)

    async def _import_workflow(
        self,
        files: Dict[str, bytes],
        workflow_file: str,
        manifest: Dict[str, Any],
        source_info: Dict[str, str],
        package_id: str
    ) -> Optional[int]:
        """Importa un workflow."""
        workflow_name = workflow_file.replace(".json", "")
        workflow_path = f"workflows/{workflow_file}"

        if workflow_path not in files:
            return None

        try:
            workflow_spec = json.loads(files[workflow_path].decode('utf-8'))
        except json.JSONDecodeError:
            return None

        workflow_data = {
            'name': workflow_spec.get('name', workflow_name),
            'description': workflow_spec.get('description', f'Importado desde {manifest.get("name", "paquete")}'),
            'version': workflow_spec.get('version', '1.0.0'),
            'status': 'DRAFT',  # Workflows siempre empiezan como DRAFT
            'trigger_type': workflow_spec.get('trigger_type', 'manual'),
            'trigger_config': json.dumps(workflow_spec.get('trigger_config', {})),
            'steps': json.dumps(workflow_spec.get('steps', [])),
            'is_active': False,  # Desactivado hasta revision
            'owner_scope': workflow_spec.get('owner_scope')
        }

        return await self._save_workflow(workflow_data)

    async def _generate_unique_name(self, base_name: str, item_type: str) -> str:
        """Genera un nombre unico agregando sufijo."""
        suffix = "_imported"
        counter = 1
        new_name = f"{base_name}{suffix}"

        while True:
            exists = False
            if item_type == "script":
                exists = await self._script_exists(new_name)
            elif item_type == "playbook":
                exists = await self._playbook_exists(new_name)

            if not exists:
                return new_name

            counter += 1
            new_name = f"{base_name}{suffix}_{counter}"

    async def _script_exists(self, name: str) -> bool:
        """Verifica si existe un script con ese nombre."""
        try:
            async with AsyncSession(client_engine) as session:
                result = await session.exec(
                    select(CustomScript).where(CustomScript.name == name)
                )
                return result.first() is not None
        except Exception:
            return False

    async def _playbook_exists(self, name: str) -> bool:
        """Verifica si existe un playbook con ese nombre."""
        try:
            async with AsyncSession(client_engine) as session:
                result = await session.exec(
                    select(RpaPlaybook).where(RpaPlaybook.name == name)
                )
                return result.first() is not None
        except Exception:
            return False

    async def _save_script(self, script_data: Dict[str, Any]) -> int:
        """Guarda un script nuevo en la BD."""
        async with AsyncSession(client_engine) as session:
            script = CustomScript(
                name=script_data['name'],
                code=script_data['code'],
                code_hash=script_data['code_hash'],
                status=script_data['status'],
                description=script_data.get('description', ''),
                user_prompt=script_data.get('description', ''),
                origin_license_id=script_data.get('origin_license_id'),
                origin_package_id=script_data.get('origin_package_id'),
                original_status=script_data.get('original_status'),
                input_type=script_data.get('input_type', 'file'),
                output_type=script_data.get('output_type', 'file'),
                tags=script_data.get('tags', []),
                required_libraries=script_data.get('required_libraries', [])
            )
            session.add(script)
            await session.commit()
            await session.refresh(script)
            return script.id

    async def _update_script(self, script_data: Dict[str, Any]) -> int:
        """Actualiza un script existente."""
        async with AsyncSession(client_engine) as session:
            result = await session.exec(
                select(CustomScript).where(CustomScript.id == script_data['id'])
            )
            script = result.first()
            if script:
                script.code = script_data['code']
                script.code_hash = script_data['code_hash']
                script.status = script_data['status']
                script.description = script_data.get('description', script.description)
                script.origin_license_id = script_data.get('origin_license_id')
                script.origin_package_id = script_data.get('origin_package_id')
                script.original_status = script_data.get('original_status')
                script.updated_at = datetime.now(timezone.utc)
                await session.commit()
                return script.id
        return script_data['id']

    async def _save_playbook(self, playbook_data: Dict[str, Any]) -> int:
        """Guarda un playbook nuevo en la BD."""
        async with AsyncSession(client_engine) as session:
            # Parsear actions si es string
            actions = playbook_data['actions']
            if isinstance(actions, str):
                actions = json.loads(actions)

            playbook = RpaPlaybook(
                name=playbook_data['name'],
                description=playbook_data.get('description', ''),
                base_url=playbook_data.get('base_url', ''),
                actions=actions,
                content_hash=playbook_data.get('content_hash'),
                origin_license_id=playbook_data.get('origin_license_id'),
                origin_package_id=playbook_data.get('origin_package_id')
            )
            session.add(playbook)
            await session.commit()
            await session.refresh(playbook)
            return playbook.id

    async def _update_playbook(self, playbook_data: Dict[str, Any]) -> int:
        """Actualiza un playbook existente."""
        async with AsyncSession(client_engine) as session:
            result = await session.exec(
                select(RpaPlaybook).where(RpaPlaybook.id == playbook_data['id'])
            )
            playbook = result.first()
            if playbook:
                actions = playbook_data['actions']
                if isinstance(actions, str):
                    actions = json.loads(actions)
                playbook.actions = actions
                playbook.description = playbook_data.get('description', playbook.description)
                playbook.base_url = playbook_data.get('base_url', playbook.base_url)
                playbook.content_hash = playbook_data.get('content_hash')
                playbook.origin_license_id = playbook_data.get('origin_license_id')
                playbook.origin_package_id = playbook_data.get('origin_package_id')
                await session.commit()
                return playbook.id
        return playbook_data['id']

    async def _save_workflow(self, workflow_data: Dict[str, Any]) -> int:
        """Guarda un workflow nuevo en la BD."""
        async with AsyncSession(client_engine) as session:
            workflow = FlowRegistry(
                name=workflow_data['name'],
                description=workflow_data.get('description', ''),
                version=workflow_data.get('version', '1.0.0'),
                status=workflow_data.get('status', 'DRAFT'),
                trigger_type=workflow_data.get('trigger_type', 'manual'),
                trigger_config=workflow_data.get('trigger_config', '{}'),
                steps=workflow_data.get('steps', '[]'),
                is_active=workflow_data.get('is_active', False),
                owner_scope=workflow_data.get('owner_scope')
            )
            session.add(workflow)
            await session.commit()
            await session.refresh(workflow)
            return workflow.id

    async def _record_import(
        self,
        manifest: Dict[str, Any],
        validation: ValidationResult,
        package_id: str
    ):
        """Registra el paquete importado en la BD."""
        source = manifest.get("source", {})
        signature = manifest.get("signature", {})
        contents = manifest.get("contents", {})

        async with AsyncSession(client_engine) as session:
            # Determinar tipo de paquete
            has_scripts = len(contents.get("scripts", [])) > 0
            has_playbooks = len(contents.get("playbooks", [])) > 0
            has_workflows = len(contents.get("workflows", [])) > 0

            if has_workflows:
                package_type = PackageType.WORKFLOW
            elif has_scripts and has_playbooks:
                package_type = PackageType.MIXED
            elif has_scripts:
                package_type = PackageType.SCRIPTS
            else:
                package_type = PackageType.PLAYBOOKS

            package = AutomatismPackage(
                package_id=package_id,
                name=manifest.get("name", "Imported Package"),
                description=manifest.get("description"),
                package_type=package_type,
                source_license_id=source.get("license_id", ""),
                source_client_id=source.get("client_id", ""),
                source_partner_id=source.get("partner_id", ""),
                source_machine_id=source.get("machine_id"),
                signature_type=signature.get("type", "CLIENT"),
                signer_id=source.get("license_id", ""),
                signature_value=signature.get("value", ""),
                signed_at=datetime.fromisoformat(
                    signature.get("timestamp", datetime.now(timezone.utc).isoformat()).replace("Z", "")
                ),
                manifest_hash=manifest.get("package_hash", ""),
                package_hash=hashlib.sha256(
                    json.dumps(manifest, sort_keys=True).encode()
                ).hexdigest(),
                scripts_count=len(contents.get("scripts", [])),
                playbooks_count=len(contents.get("playbooks", [])),
                workflows_count=len(contents.get("workflows", [])),
                status=PackageStatus.IMPORTED,
                imported_at=datetime.now(timezone.utc),
                imported_by_license_id=await self._get_local_license_id()
            )
            session.add(package)
            await session.commit()

    async def _get_local_license_id(self) -> str:
        """Obtiene el ID de licencia local."""
        try:
            from client_app.app.database.models import ServerConnection
            async with AsyncSession(client_engine) as session:
                result = await session.exec(
                    select(ServerConnection).where(ServerConnection.is_active == True)
                )
                connection = result.first()
                if connection:
                    license_hash = hashlib.sha256(connection.license_key.encode()).hexdigest()
                    return f"LIC-{license_hash[:8].upper()}"
        except Exception:
            pass
        return "LOCAL"

    async def _verify_partner_token(self, token: str) -> bool:
        """
        Verifica un token de aprobacion del partner.
        R-01 Partner Identity.
        """
        if not token:
            return False
            
        try:
            # Usar BrainAPIClient para verificar con el servidor
            from client_app.app.clients.brain_client import BrainAPIClient
            from client_app.app.database.models import ServerConnection
            
            # Obtener URL del servidor Brain
            async with AsyncSession(client_engine) as session:
                result = await session.exec(
                    select(ServerConnection).where(ServerConnection.is_active == True)
                )
                connection = result.first()
                brain_url = connection.brain_url if connection else "http://localhost:8000"

            client = BrainAPIClient(base_url=brain_url)
            
            
            # Validar la licencia (token) del partner usando el endpoint específico
            is_valid = await client.verify_partner_token(token)
            return is_valid
            
        except Exception as e:
            logger.warning(f"Error verificando partner token: {e}")
            return False


# Singleton del servicio
automatism_import_service = AutomatismImportService()
