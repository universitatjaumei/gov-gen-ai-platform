import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import fnmatch
import time
from datetime import datetime
import os

from shared.automatia_shared.dtos import FileWatcherPayload, TriggerPayloadMeta
from client_app.app.services.event_bus_service import event_bus_service
import uuid

class FolderWatcher:
    """
    Monitor de carpetas integrado con EventBus.
    
    Features:
    - Detección en tiempo real con watchdog
    - Filtrado por patrones de archivo (*.pdf, *.xlsx)
    - Espera de estabilización (evita procesar archivos en escritura)
    - Emisión a EventBus (Trigger)
    - Soporte para subdirectorios (opcional)
    """
    
    def __init__(
        self,
        watch_directory: Path,
        trigger_id: int,
        file_patterns: Optional[List[str]] = None,
        stabilization_time: float = 2.0,
        recursive: bool = False
    ):
        """
        Args:
            watch_directory: Carpeta a vigilar
            trigger_id: ID del TriggerConfig
            file_patterns: Patrones de archivo (ej: ["*.pdf", "*.xlsx"])
            stabilization_time: Segundos a esperar antes de procesar
            recursive: Vigilar subdirectorios
        """
        self.watch_directory = Path(watch_directory)
        self.trigger_id = trigger_id
        self.file_patterns = file_patterns or ["*"]
        self.stabilization_time = stabilization_time
        self.recursive = recursive
        
        self.observer: Optional[Observer] = None
        self._running = False
        self._pending_files: Dict[Path, float] = {}  # {path: timestamp}
        
        # Asegurar que existe el directorio
        self.watch_directory.mkdir(parents=True, exist_ok=True)
    
    def _matches_pattern(self, file_path: Path) -> bool:
        """Verifica si el archivo coincide con algún pattern"""
        filename = file_path.name
        
        for pattern in self.file_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        
        return False
    
    async def _wait_for_stability(self, file_path: Path):
        """
        Espera a que el archivo termine de escribirse.
        
        Monitorea el tamaño del archivo cada 0.5s durante
        `stabilization_time` segundos. Si no cambia, asume que terminó.
        """
        last_size = -1
        stable_count = 0
        required_stable = int(self.stabilization_time / 0.5)
        
        while stable_count < required_stable:
            try:
                current_size = file_path.stat().st_size
                
                if current_size == last_size:
                    stable_count += 1
                else:
                    stable_count = 0
                
                last_size = current_size
                await asyncio.sleep(0.5)
            
            except FileNotFoundError:
                # Archivo borrado mientras esperábamos
                return False
        
        return True
    
    async def _process_file(self, file_path: Path):
        """
        Procesa un archivo: espera estabilización y emite evento.
        
        Args:
            file_path: Ruta al archivo detectado
        """
        print(f"[FolderWatcher] Detected file: {file_path}")
        
        # Esperar estabilización
        is_stable = await self._wait_for_stability(file_path)
        
        if not is_stable:
            print(f"[FolderWatcher] File deleted before processing: {file_path}")
            return
        
        print(f"[FolderWatcher] File stable, emitting event: {file_path}")
        
        try:
            # Construct Payload
            stat = file_path.stat()
            rel_path = str(file_path.relative_to(self.watch_directory))
            
            meta = TriggerPayloadMeta(
                trigger_id=self.trigger_id,
                trigger_type="file_watcher",
                timestamp=datetime.utcnow(),
                execution_id=uuid.uuid4().hex
            )
            
            payload = FileWatcherPayload(
                meta=meta,
                data={
                    "file_path": str(file_path.absolute()),
                    "file_name": file_path.name,
                    "extension": file_path.suffix,
                    "size_bytes": stat.st_size,
                    "relative_path": rel_path
                }
            )
            
            # Emit Event
            await event_bus_service.emit_trigger_event(
                trigger_id=self.trigger_id,
                payload=payload.model_dump() # Convert to dict for compatibility
            )
            
            print(f"[FolderWatcher] Event emitted for {file_path}")

        except Exception as e:
            # Clean log for Windows
            try:
                encoded_e = str(e).encode('ascii', 'ignore').decode()
            except:
                encoded_e = "Unknown error"
            print(f"[FolderWatcher] ERROR emitting event: {encoded_e}")

    async def _monitor_pending_files(self):
        """
        Tarea en background que procesa archivos pendientes.
        
        Revisa continuamente la cola de archivos detectados
        y los procesa cuando están estables.
        """
        while self._running:
            try:
                # Procesar archivos pendientes
                for file_path in list(self._pending_files.keys()):
                    # Verificar si es hora de procesar
                    detection_time = self._pending_files[file_path]
                    elapsed = time.time() - detection_time
                    
                    if elapsed >= self.stabilization_time:
                        # Remover de pendientes y procesar
                        del self._pending_files[file_path]
                        await self._process_file(file_path)
                
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[FolderWatcher] Error in monitoring loop: {e}")
                await asyncio.sleep(1.0) # Wait a bit on error
    
    class _EventHandler(FileSystemEventHandler):
        """Handler interno de watchdog"""
        
        def __init__(self, watcher):
            self.watcher = watcher
        
        def on_created(self, event):
            """Callback cuando se crea un archivo"""
            if event.is_directory:
                return
            
            file_path = Path(event.src_path)
            print(f"DEBUG: on_created {file_path}")
            
            # Verificar patrón
            if not self.watcher._matches_pattern(file_path):
                print(f"DEBUG: pattern mismatch {file_path}")
                return
            
            # Añadir a cola de pendientes
            print(f"DEBUG: added to pending {file_path}")
            self.watcher._pending_files[file_path] = time.time()
            
        def on_modified(self, event):
            """Callback cuando se modifica un archivo (fallback para Windows)"""
            self.on_created(event)
    
    async def start_monitoring(self):
        """
        Inicia el monitoreo de la carpeta.
        
        Ejecuta en loop infinito hasta que se llame a stop().
        """
        print(f"[FolderWatcher] Starting monitoring: {self.watch_directory}")
        print(f"[FolderWatcher] Patterns: {self.file_patterns}")
        print(f"[FolderWatcher] Workflow: {self.flow_id}")
        
        self._running = True
        
        # Configurar watchdog observer
        self.observer = Observer()
        event_handler = self._EventHandler(self)
        
        self.observer.schedule(
            event_handler,
            str(self.watch_directory),
            recursive=self.recursive
        )
        
        self.observer.start()
        
        # Iniciar procesador de cola
        await self._monitor_pending_files()
    
    def stop(self):
        """Detiene el monitoreo"""
        print("[FolderWatcher] Stopping monitoring")
        self._running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
