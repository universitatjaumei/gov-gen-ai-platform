# client_app/app/services/design_sandbox_service.py
"""
Servicio Design Sandbox - Gestiona archivos temporales de prueba para la fase de diseño.
Permite el aislamiento de muestras de datos para cada script de forma independiente.
"""
This service handles file uploads for testing scripts during the design phase.
When a UIContract defines FILE or FILES inputs, users can upload sample files
that will be used during test executions.

Key responsibilities:
- Save uploaded test files to isolated sandbox directories
- Map uploaded files to contract input variables
- Prepare execution environment with file paths
- Clean up old sandbox files (TTL-based)

NOTE: This is separate from sandbox_service.py which handles secure script execution.
This service manages the design-time file storage and mapping.
"""
import os
import shutil
import logging
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from automatia_shared.contracts.ui_contract import UIContract, InputType

logger = logging.getLogger(__name__)

# Default sandbox location
DEFAULT_SANDBOX_PATH = Path(
    os.environ.get("SANDBOX_PATH", os.path.join(os.getcwd(), "data", "executions", "sandbox"))
)


def sanitize_filename(filename: str) -> str:
    """
    Sanea el nombre de un archivo para evitar ataques de path traversal y caracteres inválidos.

    Args:
        filename: Nombre original del archivo subido.

    Returns:
        Nombre de archivo saneado seguro para el sistema de archivos.
    """
    # Remove any path components
    filename = os.path.basename(filename)

    # Remove path traversal attempts
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")

    # Keep only safe characters
    safe_chars = re.sub(r'[^\w\-_\. ]', '', filename)

    # Replace spaces with underscores
    safe_chars = safe_chars.replace(' ', '_')

    # Ensure not empty
    if not safe_chars:
        safe_chars = "unnamed_file"

    return safe_chars


class DesignSandboxService:
    """
    Gestiona archivos de prueba temporales para el testing de scripts en tiempo de diseño.

    Cada script posee su propio directorio aislado donde los usuarios pueden
    subir archivos de muestra. Estos archivos se vinculan a las entradas del
    contrato UI del script mediante un sistema de mapeo persistente.

    Directory structure:
        {base_path}/{script_id}/
            files/           - Uploaded files
            mapping.json     - Input name to file mapping
    """

    def __init__(self, base_path: Path = None, user_id: str = "default"):
        """
        Inicializa el servicio de Sandbox de Diseño.

        Args:
            base_path: Directorio raíz para el almacenamiento del sandbox.
            user_id: ID de usuario para aislamiento en entornos multi-inquilino.
        """
        self.base_path = base_path or DEFAULT_SANDBOX_PATH
        self.user_id = user_id

        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_sandbox_path(self, script_id: str) -> Path:
        """
        Obtiene la ruta del directorio del sandbox para un script específico.

        Args:
            script_id: Identificador único del script.

        Returns:
            Ruta (Path) al directorio del sandbox del script.
        """
        # Sanitize script_id to prevent path traversal
        safe_id = re.sub(r'[^\w\-]', '_', str(script_id))
        return self.base_path / safe_id

    def _get_files_dir(self, script_id: str) -> Path:
        """Obtiene el subdirectorio donde se almacenan físicamente los archivos."""
        return self.get_sandbox_path(script_id) / "files"

    def _get_mapping_path(self, script_id: str) -> Path:
        """Obtiene la ruta al archivo JSON que mantiene el mapeo entre entradas y archivos."""
        return self.get_sandbox_path(script_id) / "mapping.json"

    def _load_mapping(self, script_id: str) -> Dict[str, str]:
        """Load the input name to filename mapping."""
        mapping_path = self._get_mapping_path(script_id)
        if mapping_path.exists():
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load mapping for {script_id}: {e}")
        return {}

    def _save_mapping(self, script_id: str, mapping: Dict[str, str]) -> None:
        """Save the input name to filename mapping."""
        mapping_path = self._get_mapping_path(script_id)
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2)

    def save_test_file(
        self,
        script_id: str,
        filename: str,
        content: bytes,
        input_name: Optional[str] = None
    ) -> Path:
        """
        Guarda un archivo de prueba en el sandbox del script.

        Args:
            script_id: Identificador del script.
            filename: Nombre original del archivo.
            content: Contenido del archivo en bytes.
            input_name: Nombre de la entrada del contrato a la que se debe mapear automáticamente.

        Returns:
            Ruta absoluta al archivo guardado.
        """
        # Sanitize filename
        safe_filename = sanitize_filename(filename)

        # Create sandbox directory
        files_dir = self._get_files_dir(script_id)
        files_dir.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path = files_dir / safe_filename
        with open(file_path, 'wb') as f:
            f.write(content)

        logger.info(f"Saved test file: {file_path}")

        # Update mapping if input_name provided
        if input_name:
            mapping = self._load_mapping(script_id)
            mapping[input_name] = safe_filename
            self._save_mapping(script_id, mapping)

        return str(file_path)

    def prepare_test_environment(
        self,
        script_id: str,
        contract: UIContract
    ) -> Dict[str, Any]:
        """
        Prepara las variables de entorno mapeando archivos del sandbox a las entradas del contrato.

        Para entradas tipo FILE: Retorna la ruta a un único archivo.
        Para entradas tipo FILES: Retorna una lista con todas las rutas de archivos.

        Args:
            script_id: Identificador del script.
            contract: Contrato de interfaz (UIContract) para validar entradas.

        Returns:
            Diccionario que mapea nombres de entradas con rutas de archivos.
        """
        env_vars: Dict[str, Any] = {}
        files_dir = self._get_files_dir(script_id)

        if not files_dir.exists():
            return env_vars

        # Get all files in sandbox
        all_files = list(files_dir.glob("*"))
        all_file_paths = [str(f) for f in all_files if f.is_file()]

        # Load explicit mappings
        mapping = self._load_mapping(script_id)

        for input_def in contract.inputs:
            if input_def.type == InputType.FILE:
                # Check for explicit mapping first
                if input_def.name in mapping:
                    mapped_file = files_dir / mapping[input_def.name]
                    if mapped_file.exists():
                        env_vars[input_def.name] = str(mapped_file)
                        continue

                # Fallback: Use first available file
                if all_file_paths:
                    env_vars[input_def.name] = all_file_paths[0]

            elif input_def.type == InputType.FILES:
                # Check for explicit mapping first
                if input_def.name in mapping:
                    # Mapping could be a list for FILES type
                    mapped = mapping[input_def.name]
                    if isinstance(mapped, list):
                        paths = []
                        for m in mapped:
                            mapped_file = files_dir / m
                            if mapped_file.exists():
                                paths.append(str(mapped_file))
                        if paths:
                            env_vars[input_def.name] = paths
                            continue

                # Fallback: Return all files
                env_vars[input_def.name] = all_file_paths

        return env_vars

    def clear_sandbox(self, script_id: str) -> None:
        """
        Elimina todos los archivos y el directorio del sandbox de un script.

        Args:
            script_id: Identificador del script.
        """
        sandbox_path = self.get_sandbox_path(script_id)
        if sandbox_path.exists():
            try:
                shutil.rmtree(sandbox_path)
                logger.info(f"Cleared sandbox for script {script_id}")
            except Exception as e:
                logger.error(f"Failed to clear sandbox for {script_id}: {e}")

    def list_sandbox_files(self, script_id: str) -> List[Dict[str, Any]]:
        """
        Lista todos los archivos presentes en el sandbox de un script.

        Args:
            script_id: Identificador del script.

        Returns:
            Lista de diccionarios con información de archivos (nombre, tamaño, fecha).
        """
        files_dir = self._get_files_dir(script_id)

        if not files_dir.exists():
            return []

        files = []
        mapping = self._load_mapping(script_id)

        # Reverse mapping: filename -> input_name
        reverse_mapping = {v: k for k, v in mapping.items() if isinstance(v, str)}

        for file_path in files_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "input_name": reverse_mapping.get(file_path.name)
                })

        return files

    def delete_file(self, script_id: str, filename: str) -> bool:
        """
        Elimina un archivo individual del sandbox y actualiza los mapeos.

        Args:
            script_id: Identificador del script.
            filename: Nombre del archivo a eliminar.

        Returns:
            True si el archivo fue eliminado, False en caso contrario.
        """
        safe_filename = sanitize_filename(filename)
        file_path = self._get_files_dir(script_id) / safe_filename

        if file_path.exists():
            try:
                file_path.unlink()

                # Remove from mapping if present
                mapping = self._load_mapping(script_id)
                keys_to_remove = [k for k, v in mapping.items() if v == safe_filename]
                for key in keys_to_remove:
                    del mapping[key]
                if keys_to_remove:
                    self._save_mapping(script_id, mapping)

                logger.info(f"Deleted file {safe_filename} from sandbox {script_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete {safe_filename}: {e}")
                return False

        return False

    def get_file_for_input(self, script_id: str, input_name: str) -> Optional[Path]:
        """
        Obtiene la ruta del archivo mapeado a una entrada específica.

        Args:
            script_id: Identificador del script.
            input_name: Nombre de la variable de entrada.

        Returns:
            Ruta (Path) al archivo mapeado, o None si no se encuentra.
        """
        mapping = self._load_mapping(script_id)

        if input_name in mapping:
            filename = mapping[input_name]
            file_path = self._get_files_dir(script_id) / filename
            if file_path.exists():
                return str(file_path)

        return None

    def set_file_mapping(
        self,
        script_id: str,
        input_name: str,
        filename: str
    ) -> bool:
        """
        Mapea explícitamente una variable de entrada a un archivo específico del sandbox.

        Args:
            script_id: Identificador del script.
            input_name: Nombre de la variable de entrada.
            filename: Nombre del archivo a mapear.

        Returns:
            True si el mapeo fue exitoso.
        """
        file_path = self._get_files_dir(script_id) / sanitize_filename(filename)

        if not file_path.exists():
            logger.warning(f"Cannot map {input_name} to non-existent file {filename}")
            return False

        mapping = self._load_mapping(script_id)
        mapping[input_name] = sanitize_filename(filename)
        self._save_mapping(script_id, mapping)

        return True

    def cleanup_old_sandboxes(self, max_age_hours: int = 2) -> int:
        """
        Limpia los directorios del sandbox más antiguos que la antigüedad especificada.

        Args:
            max_age_hours: Antigüedad máxima en horas permitida.

        Returns:
            Número de sandboxes eliminados.
        """
        if not self.base_path.exists():
            return 0

        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        cleaned = 0

        for sandbox_dir in self.base_path.iterdir():
            if sandbox_dir.is_dir():
                try:
                    # Check modification time
                    mtime = datetime.fromtimestamp(sandbox_dir.stat().st_mtime)
                    if mtime < cutoff:
                        shutil.rmtree(sandbox_dir)
                        cleaned += 1
                        logger.info(f"Cleaned up old sandbox: {sandbox_dir.name}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {sandbox_dir}: {e}")

        return cleaned

    def get_sandbox_stats(self, script_id: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas sobre el sandbox de un script.

        Args:
            script_id: Identificador del script.

        Returns:
            Diccionario con el conteo de archivos, tamaño total, etc.
        """
        files = self.list_sandbox_files(script_id)

        return {
            "script_id": script_id,
            "file_count": len(files),
            "total_size": sum(f["size"] for f in files),
            "files": files
        }


# Singleton instance
design_sandbox_service = DesignSandboxService()
