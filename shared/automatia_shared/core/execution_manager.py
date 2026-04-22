import os
import json
import shutil
import hashlib
import platform
import subprocess
import tempfile
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from contextlib import contextmanager
import threading

# Load ENV
from dotenv import load_dotenv
load_dotenv()

# Try to import filelock for cross-platform locking
try:
    from filelock import FileLock
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False

# Fallback to msvcrt on Windows if filelock not available
try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

# Lock registry for thread-level safety within the same process
_THREAD_LOCKS: Dict[Path, threading.Lock] = {}
_REGISTRY_LOCK = threading.Lock()

class ExecutionLock:
    """
    Cross-platform file lock.

    Uses filelock library if available (recommended), falls back to
    msvcrt on Windows for compatibility.

    Limitations:
    - File-based locks do NOT work reliably on NFS v2/v3
    - For NFS, consider Redis or database locks for distributed locking
    """
    def __init__(self, lock_file: Path):
        """
        Inicializa el lock en base a un archivo.

        Args:
            lock_file: Ruta al archivo que servirá como lock.
        """
        self.lock_file = lock_file
        self.fd = None
        self._filelock = None

    def acquire(self, timeout: int = 10):
        """
        Acquire lock with timeout.

        Args:
            timeout: Max seconds to wait (default 10, 0 = non-blocking)

        Raises:
            TimeoutError: If lock cannot be acquired
        """
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)

        # 1. Thread-level lock (Same process)
        with _REGISTRY_LOCK:
            if self.lock_file not in _THREAD_LOCKS:
                _THREAD_LOCKS[self.lock_file] = threading.Lock()
            thread_lock = _THREAD_LOCKS[self.lock_file]

        # Non-blocking acquisition of thread lock for simplicity in this fallback
        # In a real scenario, we'd loop with timeout
        if not thread_lock.acquire(timeout=timeout):
            raise TimeoutError(f"Could not acquire thread lock on {self.lock_file}")

        # 2. File-level lock (Cross-process)
        try:
            if HAS_FILELOCK:
                # Use filelock (cross-platform)
                self._filelock = FileLock(str(self.lock_file), timeout=timeout)
                try:
                    self._filelock.acquire(timeout=timeout)
                except Exception:
                    thread_lock.release()
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file}")
            elif HAS_MSVCRT:
                # Fallback: Windows msvcrt
                try:
                    self.fd = open(self.lock_file, 'wb')
                    # We use LK_NBLCK because we don't want to hang the whole thread 
                    # if the thread_lock somehow succeeded but process_lock failed
                    msvcrt.locking(self.fd.fileno(), msvcrt.LK_NBLCK, 1)
                except (OSError, IOError):
                    if self.fd:
                        self.fd.close()
                        self.fd = None
                    thread_lock.release()
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file}")
            else:
                # No locking available - just create the file as marker
                self.lock_file.touch()
        except Exception as e:
            thread_lock.release()
            raise e

    def release(self):
        """Release the lock"""
        # 1. Release File Lock
        if self._filelock:
            try:
                self._filelock.release()
            except:
                pass
            self._filelock = None
        elif self.fd:
            try:
                if HAS_MSVCRT:
                    msvcrt.locking(self.fd.fileno(), msvcrt.LK_UNLCK, 1)
            except:
                pass
            self.fd.close()
            self.fd = None

        # 2. Release Thread Lock
        with _REGISTRY_LOCK:
            thread_lock = _THREAD_LOCKS.get(self.lock_file)
            if thread_lock:
                try:
                    thread_lock.release()
                except RuntimeError:
                    pass # Already released

    def __enter__(self):
        """
        Context manager entry: acquires the lock.
        """
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit: releases the lock.
        """
        self.release()

class RunManifest:
    """
    Wrapper para gestionar el archivo run_manifest.json de una ejecución.
    """
    def __init__(self, path: Path):
        """
        Inicializa el manifiesto indicando su ubicación.

        Args:
            path: Ruta al archivo run_manifest.json.
        """
        self.path = path
        self.data = {
            "run_id": "",
            "task": "",
            "status": "created",
            "created_at": "",
            "script": {
                "active": "",
                "versions": []
            },
            "batch_runs": [],
            "artifacts": {}
        }

    def load(self):
        """
        Carga el contenido del manifiesto desde el sistema de archivos si este existe.
        """
        if self.path.exists():
            with open(self.path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

    def save(self):
        """
        Guarda el manifiesto de forma atómica usando un archivo temporal y reemplazo posterior.
        """
        dirpath = self.path.parent
        dirpath.mkdir(parents=True, exist_ok=True)
        
        # Write to temp
        fd, tmppath = tempfile.mkstemp(dir=dirpath, prefix=".tmp_manifest_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            # Atomic Move (Replace)
            if os.path.exists(self.path):
                os.replace(tmppath, self.path)
            else:
                os.rename(tmppath, self.path)
                
        except Exception as e:
            # Cleanup temp if failed
            if os.path.exists(tmppath):
                os.remove(tmppath)
            raise e

    def update(self, updates: Dict[str, Any]):
        """
        Actualiza los datos del manifiesto y los guarda atómicamente.

        Args:
            updates: Diccionario con los cambios a aplicar.
        """
        self.data.update(updates)
        self.save()

    def add_script_version(self, filename: str, content_hash: str):
        """
        Añade una nueva versión de script al historial del manifiesto.

        Args:
            filename: Nombre del archivo de la versión.
            content_hash: Hash de integridad del contenido.
        """
        versions = self.data.setdefault('script', {}).setdefault('versions', [])
        # Avoid duplicates by hash
        if any(v['hash'] == content_hash for v in versions):
            return
            
        versions.append({
            "file": f"versions/{filename}",
            "hash": content_hash,
            "created_at": datetime.now().isoformat(),
            "security_status": "SAFE", # SAFE, WARNING, CRITICAL
            "security_logs": [],
            "user_authorized_at": None,
            "authorized_by": None
        })
        # Keep max 5 versions
        if len(versions) > 5:
            self.data['script']['versions'] = versions[-5:]
        
        self.data['script']['active'] = "script_current.py"
        self.save()

    def update_security_status(self, content_hash: str, status: str, logs: List[str] = None):
        """
        Actualiza el estado de seguridad y los logs para una versión específica del script identificada por su hash.

        Args:
            content_hash: Hash SHA256 del contenido del script.
            status: Nuevo estado (SAFE, WARNING, CRITICAL, APPROVED).
            logs: Lista opcional de hallazgos del auditor de seguridad.
        """
        versions = self.data.get('script', {}).get('versions', [])
        for v in versions:
            if v['hash'] == content_hash:
                v['security_status'] = status
                if logs: v['security_logs'] = logs
                self.save()
                return

    def authorize_script(self, content_hash: str, user_id: str):
        """
        Autoriza manualmente un script que tenía estado WARNING.

        Args:
            content_hash: Hash del script a autorizar.
            user_id: Identificador del usuario que concede la autorización.
        """
        versions = self.data.get('script', {}).get('versions', [])
        for v in versions:
            if v['hash'] == content_hash:
                v['security_status'] = 'APPROVED'
                v['user_authorized_at'] = datetime.now().isoformat()
                v['authorized_by'] = user_id
                self.save()
                return

    def add_batch_run(self, batch_info: Dict[str, Any]):
        """
        Registra una ejecución por lotes (batch) en el manifiesto.

        Args:
            batch_info: Información de la ejecución batch.
        """
        batches = self.data.setdefault('batch_runs', [])
        # Check idempotency?
        batches.append(batch_info)
        self.save()


class ExecutionPathManager:
    """
    Gestor de rutas y ciclo de vida de ejecuciones.
    Estructura: /executions/TASK_TYPE/run_ID/

    Features:
    - Rutas deterministas por execution_id
    - Sanitizacion de nombres (path traversal prevention)
    - Locks multiplataforma con filelock
    - Limpieza de ejecuciones antiguas

    Limitaciones:
    - Locks basados en archivos NO funcionan en NFS v2/v3
    - Para NFS, considerar Redis o base de datos para locks distribuidos
    """

    def __init__(self, app_name: str = 'automatia_suite'):
        # 1. Resolver STORAGE_ROOT
        env_root = os.getenv("STORAGE_ROOT")
        if env_root:
            self.base_dir = Path(env_root).resolve()
        else:
            self.base_dir = Path.home() / app_name / 'data'
            
        # 2. Definir Estructura Estandar (Prompt 1)
        self.executions_base = self.base_dir / 'executions'
        self.sessions_dir = self.base_dir / 'sessions'
        
        self.automations_dir = self.base_dir / 'automations'
        self.scripts_dir = self.automations_dir / 'scripts'
        self.docs_dir = self.automations_dir / 'docs'
        
        self.uploads_dir = self.base_dir / 'uploads'
        self.temp_dir = self.base_dir / 'tmp'

        # 3. Ensure base structure
        self.ensure_dirs()

    def ensure_dirs(self):
        """
        Crea de forma idempotente toda la estructura de directorios necesaria para la aplicación.
        """
        for d in [self.executions_base, self.sessions_dir, 
                  self.automations_dir, self.scripts_dir, self.docs_dir,
                  self.uploads_dir, self.temp_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def get_automations_dir(self) -> Path:
        """
        Retorna la ruta absoluta al directorio donde se guardan las automatizaciones (blueprints).
        """
        return self.automations_dir

    def get_scripts_dir(self) -> Path:
        """
        Retorna la ruta absoluta al directorio donde se guardan los scripts Python.
        """
        return self.scripts_dir

    def get_docs_dir(self) -> Path:
        """
        Retorna la ruta absoluta al directorio de documentación generada.
        """
        return self.docs_dir

    def get_uploads_dir(self) -> Path:
        """
        Retorna la ruta absoluta al directorio donde se almacenan los archivos subidos por el usuario.
        """
        return self.uploads_dir
        
    def get_temp_dir(self) -> Path:
        """
        Retorna la ruta absoluta al directorio temporal de trabajo.
        """
        return self.temp_dir

    def get_sandbox_dir(self, script_id: str) -> Path:
        """
        Retorna la ruta al sandbox específico de un script.
        """
        path = self.base_dir / "sandboxes" / self._sanitize_id(script_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _sanitize_id(self, execution_id: str) -> str:
        """
        Sanitiza execution_id para evitar path traversal.

        Elimina: ../, /, \\, <, >, :, |, ?, *
        """
        # Eliminar path separators y caracteres peligrosos
        safe_id = re.sub(r'[/\\<>:|?*]', '', execution_id)
        safe_id = safe_id.replace('..', '')

        # Asegurar que no este vacio
        if not safe_id.strip():
            safe_id = "default"

        return safe_id

    @contextmanager
    def lock(self, execution_id: str):
        """
        Context manager para lock de ejecucion.

        Usa filelock para locking multiplataforma.

        Usage:
            with manager.lock("exec_001"):
                # codigo protegido
                pass

        Args:
            execution_id: ID de la ejecucion a bloquear
        """
        run_dir = self.get_execution_path(execution_id)
        lock_path = run_dir / "execution.lock"
        lock = ExecutionLock(lock_path)

        try:
            lock.acquire()
            yield lock
        finally:
            lock.release()

    def cleanup_old_executions(self, max_age_days: int = 30) -> int:
        """
        Elimina ejecuciones mas antiguas que max_age_days.

        Args:
            max_age_days: Edad maxima en dias (0 = eliminar todas)

        Returns:
            Numero de ejecuciones eliminadas
        """
        deleted_count = 0
        cutoff = datetime.now() - timedelta(days=max_age_days)

        # Recorrer todas las carpetas de tareas
        if not self.executions_base.exists():
            return 0

        for task_dir in self.executions_base.iterdir():
            if not task_dir.is_dir():
                continue

            for run_dir in list(task_dir.iterdir()):
                if not run_dir.is_dir():
                    continue

                try:
                    # Verificar edad por fecha de modificacion
                    mtime = datetime.fromtimestamp(run_dir.stat().st_mtime)

                    if max_age_days == 0 or mtime < cutoff:
                        shutil.rmtree(run_dir)
                        deleted_count += 1
                        print(f"[ExecutionManager] Deleted old execution: {run_dir}")
                except Exception as e:
                    print(f"[ExecutionManager] Error deleting {run_dir}: {e}")

        return deleted_count

    # --- NEW LIFECYCLE API ---

    def create_run(self, task_type: str) -> str:
        """
        Crea un nuevo RUN con su estructura completa de directorios y su archivo de manifiesto inicial.
        
        Genera un identificador basado en el timestamp actual (YYYYMMDD_HHMM).
        Crea los subdirectorios: inputs, outputs, logs, scripts, versions y sandbox.

        Args:
            task_type: Tipo de tarea (ej. 'TASK_PDF_EXTRACTION').

        Returns:
            Identificador del run creado (ej. 'run_20260109_1243').
        """
        now = datetime.now()
        run_id_base = now.strftime("%Y%m%d_%H%M") # e.g. 20260109_1243
        
        # Try to resolve collision or reuse?
        # User implies: run_id = timestamp.
        # If folder exists, we might implicitly resume or fail.
        # Let's assume we want unique if lock fails.
        
        run_dir = self.executions_base / task_type / f"run_{run_id_base}"
        
        # Directories
        dirs = {
            "inputs": run_dir / "inputs",
            "outputs": run_dir / "outputs",
            "logs": run_dir / "logs",
            "scripts": run_dir / "scripts",
            "versions": run_dir / "scripts" / "versions",
            "sandbox": run_dir / "sandbox"
        }
        
        # 1. Create Structure
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)

        # 2. Acquire Lock (Try acquire)
        lock_path = run_dir / "RUNNING.lock"
        # We don't hold the lock object here permanently in class instance, 
        # usually run lifecycle is managed by caller context. 
        # But for 'creation' we strictly check if it's already running?
        # User says: "Usa un lock... para que solo un proceso cree/ejecute".
        # If we just create folders, we don't necessarily hold lock FOREVER.
        # But maybe we check if lock exists?
        # Let's write the lock check logic inside the service usage, 
        # or return a Lock object?
        # For now, just create manifest.

        # 3. Initialize Manifest
        manifest_path = run_dir / "run_manifest.json"
        manifest = RunManifest(manifest_path)
        if not manifest_path.exists():
            manifest.data = {
                "run_id": f"run_{run_id_base}",
                "task": task_type,
                "status": "created",
                "created_at": now.isoformat(),
                "script": {"active": "", "versions": []},
                "batch_runs": [],
                "artifacts": {k: v.name for k, v in dirs.items()}
            }
            manifest.save()
            
        print(f"[ExecutionManager] Created Run: {task_type}/run_{run_id_base}")
        return f"run_{run_id_base}" # Return ID

    def get_run_dir(self, task_type: str, run_id: str) -> Path:
        """
        Retorna la ruta de una ejecución específica.

        Args:
            task_type: Tipo de tarea (ej. TASK_PDF_EXTRACTION).
            run_id: Identificador de la ejecución.
        """
        return self.executions_base / task_type / run_id

    def get_execution_dir(self, execution_id: str) -> Path:
        """
        Alias para get_execution_path.
        Retorna la ruta absoluta al directorio de la ejecución.
        """
        return self.get_execution_path(execution_id)

    def get_execution_path(self, execution_id: str) -> Path:
        """
        Adaptador legado/genérico que intenta localizar la ruta de un RUN basado solo en su ID.
        Si el ID empieza por 'run_', busca en todas las subcarpetas de tareas.
        Si no, intenta la estructura plana legada.

        Args:
            execution_id: ID de la ejecución a localizar.

        Returns:
            Ruta absoluta (Path) al directorio de la ejecución.
        """
        # execution_id might be 'TASK_GENERIC_2024...' (Legacy) or 'run_2026...'
        # We need to know task_type if new schema.
        # For compatibility, we might assume execution_id contains cues
        # or we just return the Legacy path if not found in new structure.
        
        # If it looks like 'run_...', we need task_type... tricky.
        # Fallback: Search?
        if execution_id.startswith("run_"):
            # Try to find it in any subfolder
            for task_dir in self.executions_base.iterdir():
                if task_dir.is_dir():
                    candidate = task_dir / execution_id
                    if candidate.exists():
                        return candidate
        
        # Fallback to old flat structure for legacy IDs
        legacy = self.executions_base / execution_id
        if legacy.exists():
            return legacy
            
        # If generic creation, assume 'GENERIC' task default
        return self.executions_base / "TASK_PDF_EXTRACTION" / execution_id

    def get_input_dir(self, execution_id: str) -> Path:
        """Retorna el directorio de entradas de una ejecución."""
        base = self.get_execution_path(execution_id)
        # Check if 'inputs' exists (New) or 'input' (Old)
        if (base / "inputs").exists(): return base / "inputs"
        return base / "input"

    def get_output_dir(self, execution_id: str) -> Path:
        """Retorna el directorio de salidas de una ejecución."""
        base = self.get_execution_path(execution_id)
        if (base / "outputs").exists(): return base / "outputs"
        return base / "output"

    def save_script_version(self, execution_id: str, content: str, security_status: str = 'SAFE', logs: List[str] = None) -> str:
        """
        Guarda una versión inmutable del script (basada en el hash de su contenido) y actualiza
        el archivo 'script_current.py' que representa la versión activa para la ejecución.

        Args:
            execution_id: ID de la ejecución.
            content: Código fuente del script Python.
            security_status: Resultado de la auditoría de seguridad.
            logs: Hallazgos detallados de la auditoría.

        Returns:
            Nombre del archivo de la versión guardada (ej. 'script_abc123.py').
        """
        run_dir = self.get_execution_path(execution_id)
        if not run_dir.exists():
            # Fallback if creation didn't happen (should not happen in flow)
            # Create in PDF_EXTRACTION default?
            run_dir = self.executions_base / "TASK_PDF_EXTRACTION" / execution_id
            
        scripts_dir = run_dir / "scripts"
        versions_dir = run_dir / "scripts" / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir.mkdir(parents=True, exist_ok=True)
        
        # Hashtag
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:8]
        filename = f"script_{content_hash}.py"
        version_path = versions_dir / filename
        
        # Write Version (Idempotent)
        if not version_path.exists():
            with open(version_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Update Active (Copy)
        active_path = scripts_dir / "script_current.py"
        shutil.copy2(version_path, active_path)
        
        # Update Manifest
        manifest_path = run_dir / "run_manifest.json"
        # If manifest doesn't exist (Legacy run?), we check first
        if manifest_path.exists():
            manifest = RunManifest(manifest_path)
            manifest.load()
            manifest.add_script_version(filename, content_hash)
            # Update Security Metadata
            manifest.update_security_status(content_hash, security_status, logs)
        
        return str(active_path)

    def get_lock(self, execution_id: str) -> ExecutionLock:
        """
        Retorna un objeto de bloqueo (ExecutionLock) para la ejecución especificada.
        Se usa para sincronizar procesos que intenten operar sobre el mismo RUN.
        """
        run_dir = self.get_execution_path(execution_id)
        return ExecutionLock(run_dir / "RUNNING.lock")

    def open_output_folder(self, execution_id: str):
        """
        Abre el directorio de resultados (outputs) de una ejecución en el explorador de archivos
        nativo del sistema operativo (Explorer en Windows, Finder en macOS, etc).
        """
        path = self.get_output_dir(execution_id)
        if not path.exists(): return
        try:
            if platform.system() == "Windows": os.startfile(path)
            elif platform.system() == "Darwin": subprocess.Popen(["open", path])
            else: subprocess.Popen(["xdg-open", path])
        except Exception as e: print(f"Error opening folder: {e}")

    def get_pending_approvals(self) -> List[Dict]:
        """
        Escanea las ejecuciones recientes en busca de scripts cuyo estado sea 'WARNING'
        y que aún no hayan sido autorizados por un usuario.
        
        Returns:
            Lista de diccionarios con metadatos de los scripts pendientes.
        """
        pending = []
        # Scan Task folders
        for task_dir in self.executions_base.iterdir():
            if not task_dir.is_dir(): continue
            for run_dir in task_dir.iterdir():
                if not run_dir.is_dir(): continue
                
                manifest_path = run_dir / "run_manifest.json"
                if manifest_path.exists():
                    try:
                        m = RunManifest(manifest_path)
                        m.load()
                        versions = m.data.get('script', {}).get('versions', [])
                        if not versions: continue
                        
                        # Check latest version
                        latest = versions[-1]
                        if latest.get('security_status') == 'WARNING' and not latest.get('user_authorized_at'):
                            pending.append({
                                "execution_id": m.data.get('run_id'),
                                "task_type": m.data.get('task'),
                                "created_at": latest.get('created_at'),
                                "reasons": latest.get('security_logs', []),
                                "file_path": str(run_dir / "scripts" / "versions" / f"script_{latest['hash']}.py"), 
                                "hash": latest['hash']
                            })
                    except Exception as e:
                        print(f"Error reading manifest {manifest_path}: {e}")
        return pending

    # Legacy method for compatibility if still called
    def create_execution_context(self, task_type: str = 'GENERIC', workflow_id: Optional[str] = None) -> str:
        """
        Método legado para crear un contexto de ejecución.
        Mapea las llamadas a la nueva estructura de RUNs.
        """
        # Map legacy calls to new structure
        # If generic, map to PDF_EXTRACTION to align with Factory usage default
        if task_type == 'GENERIC': task_type = 'PDF_EXTRACTION'
        if task_type == 'GENERIC': task_type = 'PDF_EXTRACTION'
        return self.create_run(f"TASK_{task_type}")


# --- ORCHESTRATOR LOGIC (Prompt 12) ---

class MissingDataDependency(Exception):
    """
    Excepción lanzada cuando un paso de workflow requiere un dato de entrada
    que no está presente en el contexto de ejecución.
    """
    pass

class WorkflowContext:
    """
    Gestor de estado para el flujo de ejecución de un workflow.
    Almacena los resultados de pasos previos y resuelve variables dinámicas.
    """
    def __init__(self, execution_id: str):
        """
        Inicializa el contexto con un ID de ejecución.
        """
        self.execution_id = execution_id
        self._outputs: Dict[str, Any] = {} # step_name -> data

    def set_output(self, step_name: str, data: Any):
        """
        Registra el resultado de un paso en el almacén de datos del contexto.
        
        Args:
            step_name: Nombre o clave identificadora del resultado.
            data: Valor o estructura de datos a almacenar.
        """
        self._outputs[step_name] = data

    def get_output(self, step_name: str) -> Any:
        """
        Recupera el resultado de un paso previo almacenado en el contexto.
        """
        return self._outputs.get(step_name)
        
    def resolve_value(self, value_template: str) -> Any:
        """
        Resuelve una plantilla de variable (ej: {{mi_dato}}) contra el almacén del contexto.
        """
        if not isinstance(value_template, str):
            return value_template
            
        # Check if it matches {{variable}} pattern
        import re
        match = re.match(r'^\{\{(.+)\}\}$', value_template.strip())
        if match:
            var_name = match.group(1)
            if var_name in self._outputs:
                return self._outputs[var_name]
            else:
                # Return template as is? Or resolve to None?
                # Contract says: raises MissingDataDependency if strictly valid
                # But here we might just return keys.
                # The resolve_inputs method handles the Missing check.
                pass 
                
        return value_template

    def has_data(self, key: str) -> bool:
        """
        Verifica si existe un dato almacenado bajo la clave especificada.
        """
        return key in self._outputs


class ExecutionManager:
    """
    Orquestador central que ejecuta pasos de workflow basados en contratos (TaskSpec).
    """
    def __init__(self):
        """Inicializa el gestor con un registro vacío de ejecutores."""
        self._executors: Dict[str, Callable] = {}

    def register_executor(self, step_type: Any, executor_func: Callable):
        """
        Registra una función o corrutina encargada de procesar un tipo de paso específico.
        
        Args:
            step_type: El tipo de paso (instancia de StepType enum o string).
            executor_func: Función a la que se delegará la ejecución.
        """
        # Handle Enum or String
        key = step_type.value if hasattr(step_type, 'value') else str(step_type)
        self._executors[key] = executor_func

    def resolve_inputs(self, task, context: WorkflowContext) -> Dict[str, Any]:
        """
        Mapea los requisitos de entrada definidos en un TaskSpec a los valores reales
        disponibles en el contexto de ejecución.

        Args:
            task: El objeto TaskSpec que define las entradas requeridas.
            context: El contexto de flujo actual.

        Raises:
            MissingDataDependency: Si falta algún dato requerido.
        """
        resolved = {}
        if not task.inputs:
            return resolved
            
        for var_name in task.inputs:
            # var_name is expected to be in the context
            if not context.has_data(var_name):
                 raise MissingDataDependency(f"Task '{task.name}' requires input '{var_name}', but it is missing.")
            
            resolved[var_name] = context.resolve_value(f"{{{{{var_name}}}}}")
                
        return resolved

    async def execute_step(self, task, context: WorkflowContext) -> Any:
        """
        Orquesta la ejecución de un único paso del workflow.
        
        Pasos del proceso:
        1. Resolución de variables de entrada desde el contexto.
        2. Localización del ejecutor registrado para el tipo de paso.
        3. Invocación del ejecutor (sincrona o asíncrona).
        4. Persistencia del resultado en el contexto para pasos futuros.
        """
        # 1. Resolve inputs
        inputs = self.resolve_inputs(task, context)
        
        # 2. Find Executor
        step_type_key = task.type.value if hasattr(task.type, 'value') else str(task.type)
        executor = self._executors.get(step_type_key)
        
        if not executor:
             raise NotImplementedError(f"No executor registered for step type '{step_type_key}'")

        # 3. Execution (Inject inputs + context)
        # Some executors might need full context object, others just inputs.
        # Design decision: Pass 'inputs' as specific args if possible, or merged into context?
        # Current WorkflowEngine passes (task, context_dict).
        # We will adapt: We pass an augmented context dict containing resolved inputs.
        
        # Create a dict context for compatibility with existing executors
        # that expect context['input_key']
        step_ctx = {
            "execution_id": context.execution_id,
            **inputs # Inject resolved inputs directly
        }
        
        # If executor is async, await it
        import inspect
        if inspect.iscoroutinefunction(executor) or (hasattr(executor, 'func') and inspect.iscoroutinefunction(executor.func)): # Handle partials/mocks
            result = await executor(task, step_ctx)
        else:
            result = executor(task, step_ctx)
            
        # 4. Persistence
        # Store result keyed by step name (variable name)
        # If task has an ID or name that serves as variable source
        # Ideally TaskSpec should have 'output_var' or we use task.name
        # For Prompt 12, we assume task.name or explicit output mapping.
        # Let's use task.name as the default key for now.
        if task.name:
            context.set_output(task.name, result)
            
        return result

