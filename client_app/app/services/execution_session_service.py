"""
Execution Session Service

Almacena metadata de ejecuciones en sandbox para uso posterior en promoción.
Permite vincular contratos generados con ejecuciones validadas.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

class ExecutionSessionService:
    """
    Servicio para almacenar y recuperar metadata de ejecuciones.
    Usa almacenamiento en archivo JSON por simplicidad.
    """
    
    def __init__(self, storage_dir: str = "app/data/execution_sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._load_sessions()
    
    def _load_sessions(self):
        """Carga sesiones desde disco."""
        session_file = self.storage_dir / "sessions.json"
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    self._sessions = json.load(f)
                # Limpiar sesiones antiguas (> 7 días)
                self._cleanup_old_sessions()
            except Exception as e:
                print(f"Error loading execution sessions: {e}")
                self._sessions = {}
    
    def _save_sessions(self):
        """Guarda sesiones a disco."""
        session_file = self.storage_dir / "sessions.json"
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(self._sessions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving execution sessions: {e}")
    
    def _cleanup_old_sessions(self):
        """Elimina sesiones más antiguas de 7 días."""
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        to_remove = []
        for session_id, session in self._sessions.items():
            if session.get('created_at', '') < cutoff:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self._sessions[session_id]
        
        if to_remove:
            self._save_sessions()
    
    async def save_execution_session(
        self,
        script_id: int,
        execution_id: str,
        input_metadata: Dict[str, Any],
        output_metadata: Dict[str, Any],
        validated: bool = False
    ) -> str:
        """
        Guarda metadata de una ejecución.
        
        Args:
            script_id: ID del script ejecutado
            execution_id: ID único de la ejecución
            input_metadata: Metadata de entrada (variables, campos detectados)
            output_metadata: Metadata de salida (estructura del resultado)
            validated: Si fue validado por HITL
            
        Returns:
            Session ID
        """
        session_id = f"{script_id}_{execution_id}"
        
        self._sessions[session_id] = {
            "script_id": script_id,
            "execution_id": execution_id,
            "input_metadata": input_metadata,
            "output_metadata": output_metadata,
            "validated": validated,
            "created_at": datetime.utcnow().isoformat()
        }
        
        self._save_sessions()
        return session_id
    
    async def get_execution_session(
        self,
        script_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera la última sesión validada para un script.
        
        Args:
            script_id: ID del script
            
        Returns:
            Session dict o None si no existe
        """
        # Buscar la sesión más reciente validada para este script
        matching_sessions = [
            session for session_id, session in self._sessions.items()
            if session.get('script_id') == script_id and session.get('validated')
        ]
        
        if not matching_sessions:
            return None
        
        # Ordenar por fecha de creación (más reciente primero)
        matching_sessions.sort(
            key=lambda s: s.get('created_at', ''),
            reverse=True
        )
        
        return matching_sessions[0]
    
    async def mark_session_validated(
        self,
        execution_id: str
    ) -> bool:
        """
        Marca una sesión como validada (HITL aprobado).
        
        Args:
            execution_id: ID de la ejecución
            
        Returns:
            True si se encontró y actualizó
        """
        for session_id, session in self._sessions.items():
            if session.get('execution_id') == execution_id:
                session['validated'] = True
                session['validated_at'] = datetime.utcnow().isoformat()
                self._save_sessions()
                return True
        
        return False
    
    async def clear_script_sessions(
        self,
        script_id: int
    ):
        """
        Elimina todas las sesiones de un script.
        
        Args:
            script_id: ID del script
        """
        to_remove = [
            session_id for session_id, session in self._sessions.items()
            if session.get('script_id') == script_id
        ]
        
        for session_id in to_remove:
            del self._sessions[session_id]
        
        if to_remove:
            self._save_sessions()

# Singleton instance
execution_session_service = ExecutionSessionService()
