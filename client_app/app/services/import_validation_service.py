"""
Servicio de validacion de paquetes para importacion.
Prompt 3.1 del sistema de exportacion/importacion de automatismos.

Valida la integridad, firma y permisos de paquetes .automatia antes de importar.
"""

import logging
import zipfile
import json
import hashlib

logger = logging.getLogger(__name__)
from io import BytesIO
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.database.models import (
    ServerConnection,
    CustomScript,
    RpaPlaybook
)
from client_app.app.services.manifest_signature_service import manifest_signature_service


class ImportPermission(Enum):
    """Permisos de importacion segun origen del paquete."""
    ALLOWED = "allowed"                    # Misma licencia, importar directo
    REQUIRES_PARTNER = "requires_partner"  # Mismo partner, necesita aprobacion
    DENIED = "denied"                      # Partner diferente, no permitido


@dataclass
class ValidationResult:
    """Resultado de la validacion de un paquete."""
    is_valid: bool
    permission: ImportPermission
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    manifest: Optional[Dict[str, Any]] = None
    source_info: Optional[Dict[str, str]] = None


class ImportValidationService:
    """
    Servicio para validar paquetes .automatia antes de importar.

    Realiza las siguientes verificaciones:
    1. Estructura del ZIP (valido, sin path traversal)
    2. Presencia y formato del manifest.json
    3. Firma del manifiesto (HMAC o RSA)
    4. Hashes de archivos
    5. Antiguedad del paquete (< 30 dias)
    6. Permisos segun origen (misma licencia/partner)
    7. Deteccion de conflictos con elementos existentes
    """

    # Campos requeridos en el manifest
    REQUIRED_MANIFEST_FIELDS = ["version", "name", "source", "contents", "file_hashes"]

    # Dias maximos de antiguedad antes de generar warning
    MAX_PACKAGE_AGE_DAYS = 30

    def __init__(self):
        """Inicializa el servicio con las dependencias necesarias."""
        self._signature_service = manifest_signature_service

    async def validate_package(self, package_bytes: bytes) -> ValidationResult:
        """
        Valida un paquete .automatia antes de importar.

        Verificaciones:
        1. Estructura del ZIP
        2. Presencia y formato del manifest
        3. Firma del manifiesto
        4. Hashes de archivos
        5. Antiguedad del paquete
        6. Permisos segun origen

        Args:
            package_bytes: Contenido del archivo .automatia en bytes

        Returns:
            ValidationResult con estado y detalles de la validacion
        """
        errors: List[str] = []
        warnings: List[str] = []
        conflicts: List[Dict[str, Any]] = []

        # 1. Extraer y verificar estructura del ZIP
        try:
            files = self._extract_zip(package_bytes)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                permission=ImportPermission.DENIED,
                errors=[f"ZIP invalido: {e}"],
                warnings=[],
                conflicts=[],
                manifest=None,
                source_info=None
            )

        # 2. Verificar que existe manifest.json
        if 'manifest.json' not in files:
            errors.append("Falta manifest.json en el paquete")
            return ValidationResult(
                is_valid=False,
                permission=ImportPermission.DENIED,
                errors=errors,
                warnings=warnings,
                conflicts=[],
                manifest=None,
                source_info=None
            )

        # 3. Parsear manifest
        try:
            manifest = json.loads(files['manifest.json'].decode('utf-8'))
        except json.JSONDecodeError as e:
            errors.append(f"manifest.json no es JSON valido: {e}")
            return ValidationResult(
                is_valid=False,
                permission=ImportPermission.DENIED,
                errors=errors,
                warnings=warnings,
                conflicts=[],
                manifest=None,
                source_info=None
            )

        # 4. Verificar campos requeridos del manifest
        missing_fields = self._check_required_fields(manifest)
        if missing_fields:
            errors.append(f"Campos requeridos faltantes en manifest: {', '.join(missing_fields)}")
            return ValidationResult(
                is_valid=False,
                permission=ImportPermission.DENIED,
                errors=errors,
                warnings=warnings,
                conflicts=[],
                manifest=manifest,
                source_info=manifest.get('source')
            )

        # 5. Verificar hashes de archivos
        hash_errors = self._verify_file_hashes(manifest, files)
        errors.extend(hash_errors)

        # 6. Verificar firma del manifiesto
        signature_valid = await self._verify_signature(manifest, files)
        if not signature_valid:
            errors.append("Firma del manifiesto invalida o no verificable")

        # 7. Verificar antiguedad
        age_days = self._calculate_package_age(manifest)
        if age_days > self.MAX_PACKAGE_AGE_DAYS:
            warnings.append(f"Paquete antiguo ({age_days} dias). Considere solicitar uno mas reciente.")

        # 8. Determinar permisos
        source_info = manifest.get('source', {})
        permission = await self._determine_permission(source_info)

        # 9. Detectar conflictos
        conflicts = await self._detect_conflicts(manifest)
        if conflicts:
            warnings.append(f"Se detectaron {len(conflicts)} conflictos con elementos existentes")

        return ValidationResult(
            is_valid=len(errors) == 0,
            permission=permission,
            errors=errors,
            warnings=warnings,
            conflicts=conflicts,
            manifest=manifest,
            source_info=source_info
        )

    def _extract_zip(self, package_bytes: bytes) -> Dict[str, bytes]:
        """
        Extrae el contenido del ZIP a un diccionario.

        Valida que no haya path traversal attacks.

        Args:
            package_bytes: Bytes del archivo ZIP

        Returns:
            Diccionario {ruta_relativa: contenido_bytes}

        Raises:
            ValueError: Si se detecta path traversal o ZIP invalido
        """
        files: Dict[str, bytes] = {}

        try:
            with zipfile.ZipFile(BytesIO(package_bytes), 'r') as zf:
                for name in zf.namelist():
                    # Verificar path traversal
                    if '..' in name or name.startswith('/') or name.startswith('\\'):
                        raise ValueError(f"Path traversal detectado: {name}")

                    # Normalizar separadores de ruta
                    normalized_name = name.replace('\\', '/')

                    # Leer contenido
                    files[normalized_name] = zf.read(name)

        except zipfile.BadZipFile as e:
            raise ValueError(f"Archivo ZIP corrupto: {e}")

        return files

    def _check_required_fields(self, manifest: Dict[str, Any]) -> List[str]:
        """
        Verifica que el manifest tenga todos los campos requeridos.

        Args:
            manifest: Diccionario del manifest

        Returns:
            Lista de campos faltantes
        """
        missing = []
        for field in self.REQUIRED_MANIFEST_FIELDS:
            if field not in manifest or manifest[field] is None:
                missing.append(field)
        return missing

    def _verify_file_hashes(
        self,
        manifest: Dict[str, Any],
        files: Dict[str, bytes]
    ) -> List[str]:
        """
        Verifica que los hashes de archivos coincidan con el manifest.

        Args:
            manifest: Diccionario del manifest con file_hashes
            files: Diccionario de archivos extraidos

        Returns:
            Lista de errores de hash
        """
        errors: List[str] = []
        file_hashes = manifest.get('file_hashes', {})

        for filepath, expected_hash in file_hashes.items():
            if filepath not in files:
                errors.append(f"Archivo faltante: {filepath}")
                continue

            actual_hash = hashlib.sha256(files[filepath]).hexdigest()
            if actual_hash != expected_hash:
                errors.append(
                    f"Hash incorrecto para {filepath}: "
                    f"esperado {expected_hash[:12]}..., "
                    f"obtenido {actual_hash[:12]}..."
                )

        return errors

    async def _verify_signature(
        self,
        manifest: Dict[str, Any],
        files: Dict[str, bytes]
    ) -> bool:
        """
        Verifica la firma del manifiesto.

        Para firma CLIENT: usa HMAC con license_key + machine_id local
        Para firma PARTNER: requiere conexion al servidor Brain

        Args:
            manifest: Diccionario del manifest con signature
            files: Diccionario de archivos (para reconstruir manifest original)

        Returns:
            True si la firma es valida, False en caso contrario
        """
        signature_data = manifest.get('signature')
        if not signature_data:
            return False

        signature_type = signature_data.get('type', 'CLIENT')

        if signature_type == 'PARTNER':
            # R-01 Security: Partner signature MUST be RSA. 
            # Reject if the algorithm is HMAC (which is for CLIENT)
            algorithm = signature_data.get('algorithm', 'HMAC-SHA256')
            if 'HMAC' in algorithm:
                logger.warning("Rechazada firma Partner con algoritmo HMAC (Inseguro)")
                return False
                
            # Realize RSA verification with Brain Server
            return await self._signature_service.verify_partner_signature(
                manifest_json=json.dumps(manifest.copy().pop('signature', None) or manifest, sort_keys=True),
                signature_data=signature_data,
                partner_id=manifest.get('source', {}).get('partner_id', '')
            )

        # Firma de cliente (HMAC)
        try:
            # Obtener credenciales locales
            license_key, machine_id = await self._get_local_credentials()
            if not license_key:
                # Sin license_key local, no podemos verificar
                return False

            # Reconstruir manifest sin firma ni package_hash
            manifest_copy = manifest.copy()
            manifest_copy.pop('signature', None)
            manifest_copy.pop('package_hash', None)
            manifest_json = json.dumps(manifest_copy, sort_keys=True, indent=2)

            # Verificar firma
            return self._signature_service.verify_client_signature(
                manifest_json,
                signature_data,
                license_key,
                machine_id
            )

        except Exception:
            return False

    def _calculate_package_age(self, manifest: Dict[str, Any]) -> int:
        """
        Calcula la antiguedad del paquete en dias.

        Args:
            manifest: Diccionario del manifest con export_date

        Returns:
            Numero de dias desde la exportacion
        """
        export_date_str = manifest.get('export_date', '')

        try:
            # Remover 'Z' final si existe
            if export_date_str.endswith('Z'):
                export_date_str = export_date_str[:-1]

            export_date = datetime.fromisoformat(export_date_str)
            age = datetime.utcnow() - export_date
            return age.days

        except (ValueError, TypeError):
            return 0

    async def _determine_permission(
        self,
        source_info: Dict[str, str]
    ) -> ImportPermission:
        """
        Determina los permisos de importacion segun el origen.

        Reglas:
        - Misma license_id -> ALLOWED (importar directo)
        - Mismo partner_id -> REQUIRES_PARTNER (necesita aprobacion)
        - Diferente partner_id -> DENIED (no permitido)

        Args:
            source_info: Diccionario con license_id, partner_id del origen

        Returns:
            ImportPermission correspondiente
        """
        source_license = source_info.get('license_id', '')
        source_partner = source_info.get('partner_id', '')

        local_license = await self._get_local_license_id()
        local_partner = await self._get_local_partner_id()

        # Misma licencia -> permitido
        if source_license == local_license:
            return ImportPermission.ALLOWED

        # Mismo partner pero diferente licencia -> requiere aprobacion
        if source_partner == local_partner:
            return ImportPermission.REQUIRES_PARTNER

        # Partner diferente -> denegado
        return ImportPermission.DENIED

    async def _detect_conflicts(
        self,
        manifest: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detecta conflictos con elementos existentes.

        Busca scripts y playbooks con el mismo nombre.

        Args:
            manifest: Diccionario del manifest con contents

        Returns:
            Lista de conflictos encontrados con estructura:
            [{name, type, local_id, action}]
        """
        conflicts: List[Dict[str, Any]] = []
        contents = manifest.get('contents', {})

        # Verificar scripts
        for script_name in contents.get('scripts', []):
            # Quitar extension .py si existe
            name = script_name.replace('.py', '')
            existing = await self._find_existing_script(name)
            if existing:
                conflicts.append({
                    'name': name,
                    'type': 'script',
                    'local_id': existing.get('id'),
                    'action': 'rename'  # Accion por defecto sugerida
                })

        # Verificar playbooks
        for playbook_name in contents.get('playbooks', []):
            # Quitar extension .json si existe
            name = playbook_name.replace('.json', '')
            existing = await self._find_existing_playbook(name)
            if existing:
                conflicts.append({
                    'name': name,
                    'type': 'playbook',
                    'local_id': existing.get('id'),
                    'action': 'rename'
                })

        return conflicts

    async def _get_local_credentials(self) -> tuple:
        """
        Obtiene las credenciales locales (license_key, machine_id).

        Returns:
            Tupla (license_key, machine_id) o (None, None) si no hay conexion
        """
        try:
            async with AsyncSession(client_engine) as session:
                result = await session.exec(
                    select(ServerConnection).where(ServerConnection.is_active == True)
                )
                connection = result.first()

                if connection:
                    # Generar machine_id de la misma forma que en export
                    machine_id = self._get_machine_id()
                    return connection.license_key, machine_id

        except Exception:
            pass

        return None, None

    async def _get_local_license_id(self) -> str:
        """
        Obtiene el ID de licencia local.

        Returns:
            ID de licencia derivado o cadena vacia
        """
        license_key, _ = await self._get_local_credentials()
        if license_key:
            # Derivar ID de la misma forma que en export
            hash_value = hashlib.sha256(license_key.encode()).hexdigest()
            return f"LIC-{hash_value[:8].upper()}"
        return ""

    async def _get_local_partner_id(self) -> str:
        """
        Obtiene el ID de partner local.

        Returns:
            ID de partner derivado o cadena vacia
        """
        license_key, _ = await self._get_local_credentials()
        if license_key:
            # Derivar ID de la misma forma que en export
            hash_value = hashlib.sha256(f"partner:{license_key}".encode()).hexdigest()
            return f"PARTNER-{hash_value[:6].upper()}"
        return ""

    def _get_machine_id(self) -> str:
        """
        Obtiene el ID de maquina local.

        Returns:
            ID unico de la maquina
        """
        import platform
        import uuid

        try:
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
                    if machine_uuid:
                        return f"WIN-{machine_uuid[:12]}"
        except Exception:
            pass

        try:
            mac = hex(uuid.getnode())[2:].upper()
            return f"MAC-{mac}"
        except Exception:
            pass

        return f"RND-{uuid.uuid4().hex[:12].upper()}"

    async def _find_existing_script(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Busca un script existente por nombre.

        Args:
            name: Nombre del script

        Returns:
            Diccionario con id y name si existe, None si no
        """
        try:
            async with AsyncSession(client_engine) as session:
                result = await session.exec(
                    select(CustomScript).where(CustomScript.name == name)
                )
                script = result.first()
                if script:
                    return {"id": script.id, "name": script.name}
        except Exception:
            pass
        return None

    async def _find_existing_playbook(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Busca un playbook existente por nombre.

        Args:
            name: Nombre del playbook

        Returns:
            Diccionario con id y name si existe, None si no
        """
        try:
            async with AsyncSession(client_engine) as session:
                result = await session.exec(
                    select(RpaPlaybook).where(RpaPlaybook.name == name)
                )
                playbook = result.first()
                if playbook:
                    return {"id": playbook.id, "name": playbook.name}
        except Exception:
            pass
        return None


# Singleton del servicio
import_validation_service = ImportValidationService()
