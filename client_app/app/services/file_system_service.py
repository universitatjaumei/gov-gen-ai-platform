"""
FileSystemService - Operaciones de Sistema de Archivos para Flujos

Servicio unificado para operaciones de sistema de archivos:
- FolderScan: Escaneo pasivo de carpetas (sin monitoreo continuo)
- ArchiveFile: Mover/copiar archivos a destino con soporte de variables

Incluye protección contra Path Traversal y auditoría de operaciones.
"""

import os
import shutil
import asyncio
import fnmatch
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from client_app.app.services.enterprise_audit_service import enterprise_audit_service
from automatia_shared.core.audit_models import RiskLevel


class FileOperation(str, Enum):
    """Tipos de operaciones de archivo."""
    COPY = "copy"
    MOVE = "move"


@dataclass
class FileInfo:
    """Información de un archivo encontrado."""
    path: str
    name: str
    extension: str
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    is_directory: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para Data Pills."""
        return {
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "is_directory": self.is_directory,
        }


@dataclass
class ScanResult:
    """Resultado de un escaneo de carpeta."""
    success: bool
    files: List[FileInfo] = field(default_factory=list)
    total_count: int = 0
    total_size_bytes: int = 0
    scan_path: str = ""
    pattern: str = "*"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para output contract."""
        return {
            "success": self.success,
            "files": [f.to_dict() for f in self.files],
            "total_count": self.total_count,
            "total_size_bytes": self.total_size_bytes,
            "scan_path": self.scan_path,
            "pattern": self.pattern,
            "error": self.error,
        }


@dataclass
class ArchiveResult:
    """Resultado de una operación de archivado."""
    success: bool
    source_path: str
    destination_path: str
    operation: FileOperation
    file_size_bytes: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para output contract."""
        return {
            "success": self.success,
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "operation": self.operation.value,
            "file_size_bytes": self.file_size_bytes,
            "error": self.error,
        }


class FileSystemService:
    """
    Servicio para operaciones de sistema de archivos en flujos.

    Proporciona funcionalidad para:
    - Escaneo pasivo de carpetas (FolderScan)
    - Archivado de resultados (ArchiveFile)

    Incluye:
    - Protección contra Path Traversal
    - Auditoría de todas las operaciones
    - Soporte para variables {{...}} en rutas
    """

    # Rutas base permitidas (configurable)
    ALLOWED_BASE_PATHS: List[str] = [
        os.path.expanduser("~"),  # Home del usuario
        os.getcwd(),  # Directorio de trabajo
        "C:\\",  # Windows root (restringir en producción)
        "/",  # Unix root (restringir en producción)
    ]

    # Rutas prohibidas (siempre bloqueadas)
    BLOCKED_PATHS: List[str] = [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "/etc",
        "/bin",
        "/sbin",
        "/usr/bin",
        "/usr/sbin",
        "/var",
        "/root",
    ]

    def __init__(self):
        self._audit_enabled = True

    # =========================================================================
    # PATH VALIDATION (Protección contra Path Traversal)
    # =========================================================================

    def _validate_path(self, path: str, check_exists: bool = False) -> tuple[bool, str]:
        """
        Valida una ruta contra ataques de Path Traversal.

        Args:
            path: Ruta a validar
            check_exists: Si True, verifica que la ruta exista

        Returns:
            Tupla (is_valid, error_message)
        """
        if not path:
            return False, "Ruta vacía"

        try:
            # Resolver ruta absoluta y normalizar
            resolved = Path(path).resolve()
            resolved_str = str(resolved)

            # Verificar path traversal (../)
            if ".." in path:
                return False, "Path traversal detectado: '..' no permitido"

            # Verificar rutas bloqueadas
            for blocked in self.BLOCKED_PATHS:
                blocked_resolved = str(Path(blocked).resolve())
                if resolved_str.startswith(blocked_resolved):
                    return False, f"Ruta bloqueada: {blocked}"

            # Verificar existencia si se requiere
            if check_exists and not resolved.exists():
                return False, f"La ruta no existe: {resolved_str}"

            return True, ""

        except Exception as e:
            return False, f"Error validando ruta: {str(e)}"

    def _resolve_variables(self, path: str, variables: Dict[str, Any]) -> str:
        """
        Resuelve variables {{...}} en una ruta.

        Args:
            path: Ruta con posibles variables
            variables: Diccionario de variables disponibles

        Returns:
            Ruta con variables resueltas
        """
        result = path
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result

    # =========================================================================
    # FOLDER SCAN (Escaneo Pasivo)
    # =========================================================================

    async def scan_folder(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False,
        include_directories: bool = False,
        max_files: int = 1000,
        variables: Optional[Dict[str, Any]] = None,
        flow_id: Optional[int] = None,
        execution_id: Optional[str] = None,
    ) -> ScanResult:
        """
        Escanea una carpeta y lista archivos según patrón.

        Args:
            path: Ruta de la carpeta a escanear
            pattern: Patrón glob (ej: "*.pdf", "report_*.xlsx")
            recursive: Si True, escanea subcarpetas
            include_directories: Si True, incluye directorios en resultados
            max_files: Límite máximo de archivos a retornar
            variables: Variables para resolver en la ruta
            flow_id: ID del flujo (para auditoría)
            execution_id: ID de ejecución (para auditoría)

        Returns:
            ScanResult con lista de archivos encontrados
        """
        # Resolver variables en la ruta
        if variables:
            path = self._resolve_variables(path, variables)

        # Validar ruta
        is_valid, error = self._validate_path(path, check_exists=True)
        if not is_valid:
            return ScanResult(
                success=False,
                scan_path=path,
                pattern=pattern,
                error=error
            )

        try:
            resolved_path = Path(path).resolve()

            if not resolved_path.is_dir():
                return ScanResult(
                    success=False,
                    scan_path=str(resolved_path),
                    pattern=pattern,
                    error="La ruta no es un directorio"
                )

            files: List[FileInfo] = []
            total_size = 0

            # Función de escaneo
            def scan_dir(dir_path: Path, depth: int = 0):
                nonlocal total_size
                if len(files) >= max_files:
                    return

                try:
                    for entry in dir_path.iterdir():
                        if len(files) >= max_files:
                            break

                        # Aplicar patrón
                        if not fnmatch.fnmatch(entry.name, pattern):
                            if not (entry.is_dir() and recursive):
                                continue

                        if entry.is_file():
                            stat = entry.stat()
                            files.append(FileInfo(
                                path=str(entry),
                                name=entry.name,
                                extension=entry.suffix.lower(),
                                size_bytes=stat.st_size,
                                created_at=datetime.fromtimestamp(stat.st_ctime),
                                modified_at=datetime.fromtimestamp(stat.st_mtime),
                                is_directory=False
                            ))
                            total_size += stat.st_size

                        elif entry.is_dir():
                            if include_directories and fnmatch.fnmatch(entry.name, pattern):
                                stat = entry.stat()
                                files.append(FileInfo(
                                    path=str(entry),
                                    name=entry.name,
                                    extension="",
                                    size_bytes=0,
                                    created_at=datetime.fromtimestamp(stat.st_ctime),
                                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                                    is_directory=True
                                ))

                            if recursive:
                                scan_dir(entry, depth + 1)

                except PermissionError:
                    pass  # Ignorar carpetas sin permisos

            # Ejecutar escaneo en thread pool para no bloquear
            await asyncio.get_event_loop().run_in_executor(
                None, scan_dir, resolved_path
            )

            # Ordenar por fecha de modificación (más reciente primero)
            files.sort(key=lambda f: f.modified_at, reverse=True)

            result = ScanResult(
                success=True,
                files=files,
                total_count=len(files),
                total_size_bytes=total_size,
                scan_path=str(resolved_path),
                pattern=pattern
            )

            # Auditoría
            if self._audit_enabled:
                await enterprise_audit_service.log_event(
                    action_type="FOLDER_SCAN_EXECUTED",
                    module="file_system_service",
                    source_description=str(resolved_path),
                    target_description=f"Pattern: {pattern}",
                    risk_level=RiskLevel.LOW.value,
                    execution_id=execution_id,
                    additional_context={
                        "pattern": pattern,
                        "recursive": recursive,
                        "files_found": len(files),
                        "total_size_bytes": total_size,
                        "flow_id": flow_id,
                    }
                )

            return result

        except Exception as e:
            return ScanResult(
                success=False,
                scan_path=path,
                pattern=pattern,
                error=str(e)
            )

    # =========================================================================
    # ARCHIVE FILE (Guardar Resultados)
    # =========================================================================

    async def archive_file(
        self,
        source: str,
        destination: str,
        operation: FileOperation = FileOperation.COPY,
        create_dirs: bool = True,
        overwrite: bool = False,
        prefix: str = "",
        suffix: str = "",
        variables: Optional[Dict[str, Any]] = None,
        flow_id: Optional[int] = None,
        execution_id: Optional[str] = None,
    ) -> ArchiveResult:
        """
        Mueve o copia un archivo a una ruta destino.

        Args:
            source: Ruta del archivo origen
            destination: Ruta destino (puede incluir nombre de archivo)
            operation: COPY o MOVE
            create_dirs: Si True, crea directorios destino si no existen
            overwrite: Si True, sobrescribe archivo existente
            prefix: Prefijo para añadir al nombre del archivo
            suffix: Sufijo para añadir al nombre del archivo antes de la extensión
            variables: Variables para resolver en rutas
            flow_id: ID del flujo (para auditoría)
            execution_id: ID de ejecución (para auditoría)

        Returns:
            ArchiveResult con resultado de la operación
        """
        # Resolver variables
        if variables:
            source = self._resolve_variables(source, variables)
            destination = self._resolve_variables(destination, variables)
            prefix = self._resolve_variables(prefix, variables)
            suffix = self._resolve_variables(suffix, variables)

        # Validar ruta origen
        is_valid, error = self._validate_path(source, check_exists=True)
        if not is_valid:
            return ArchiveResult(
                success=False,
                source_path=source,
                destination_path=destination,
                operation=operation,
                error=f"Origen inválido: {error}"
            )

        # Validar ruta destino
        is_valid, error = self._validate_path(destination, check_exists=False)
        if not is_valid:
            return ArchiveResult(
                success=False,
                source_path=source,
                destination_path=destination,
                operation=operation,
                error=f"Destino inválido: {error}"
            )

        try:
            source_path = Path(source).resolve()
            dest_path = Path(destination).resolve()

            if not source_path.is_file():
                return ArchiveResult(
                    success=False,
                    source_path=str(source_path),
                    destination_path=str(dest_path),
                    operation=operation,
                    error="El origen no es un archivo"
                )

            # Preparar nombre de archivo destino
            original_stem = source_path.stem
            original_ext = source_path.suffix
            new_filename = f"{prefix}{original_stem}{suffix}{original_ext}"

            # Si destino es directorio, usar el (nuevo) nombre del archivo origen
            if dest_path.is_dir() or (not dest_path.exists() and not dest_path.suffix):
                dest_path = dest_path / new_filename
            else:
                # Si destino es un archivo, aplicamos el renombrado a su nombre
                # (aunque usualmente el destination_path sería la carpeta)
                dest_stem = dest_path.stem
                dest_ext = dest_path.suffix
                dest_filename = f"{prefix}{dest_stem}{suffix}{dest_ext}"
                dest_path = dest_path.with_name(dest_filename)

            # Crear directorios si no existen
            if create_dirs:
                dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Verificar si existe y no se permite sobrescribir
            if dest_path.exists() and not overwrite:
                return ArchiveResult(
                    success=False,
                    source_path=str(source_path),
                    destination_path=str(dest_path),
                    operation=operation,
                    error="El archivo destino ya existe y overwrite=False"
                )

            # Obtener tamaño antes de operación
            file_size = source_path.stat().st_size

            # Ejecutar operación en thread pool
            def do_operation():
                if operation == FileOperation.COPY:
                    shutil.copy2(source_path, dest_path)
                else:  # MOVE
                    shutil.move(str(source_path), str(dest_path))

            await asyncio.get_event_loop().run_in_executor(None, do_operation)

            result = ArchiveResult(
                success=True,
                source_path=str(source_path),
                destination_path=str(dest_path),
                operation=operation,
                file_size_bytes=file_size
            )

            # Auditoría
            if self._audit_enabled:
                await enterprise_audit_service.log_event(
                    action_type="FILE_ARCHIVED",
                    module="file_system_service",
                    source_description=str(source_path),
                    target_description=str(dest_path),
                    risk_level=RiskLevel.LOW.value,
                    execution_id=execution_id,
                    additional_context={
                        "operation": operation.value,
                        "file_size_bytes": file_size,
                        "flow_id": flow_id,
                    }
                )

            return result

        except Exception as e:
            return ArchiveResult(
                success=False,
                source_path=source,
                destination_path=destination,
                operation=operation,
                error=str(e)
            )

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    async def archive_files(
        self,
        files: List[FileInfo],
        destination_folder: str,
        operation: FileOperation = FileOperation.COPY,
        create_dirs: bool = True,
        overwrite: bool = False,
        prefix: str = "",
        suffix: str = "",
        variables: Optional[Dict[str, Any]] = None,
        flow_id: Optional[int] = None,
        execution_id: Optional[str] = None,
    ) -> List[ArchiveResult]:
        """
        Archiva múltiples archivos a una carpeta destino.

        Args:
            files: Lista de FileInfo a archivar
            destination_folder: Carpeta destino
            operation: COPY o MOVE
            create_dirs: Si True, crea directorios
            overwrite: Si True, sobrescribe existentes
            prefix: Prefijo a aplicar a cada archivo
            suffix: Sufijo a aplicar a cada archivo
            variables: Variables para resolver en ruta destino
            flow_id: ID del flujo
            execution_id: ID de ejecución

        Returns:
            Lista de ArchiveResult por cada archivo
        """
        results = []
        for file_info in files:
            result = await self.archive_file(
                source=file_info.path,
                destination=destination_folder,
                operation=operation,
                create_dirs=create_dirs,
                overwrite=overwrite,
                prefix=prefix,
                suffix=suffix,
                variables=variables,
                flow_id=flow_id,
                execution_id=execution_id
            )
            results.append(result)
        return results


# Singleton
file_system_service = FileSystemService()
