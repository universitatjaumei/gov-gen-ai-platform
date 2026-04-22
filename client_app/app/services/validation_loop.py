from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
import json

from client_app.app.database.models import ValidationHistory

class ValidationLoopManager:
    """
    Gestiona el ciclo de validación interactiva de tareas.
    Permite el registro de feedback del usuario, el seguimiento de reintentos
    y la escalación automática a soporte técnico si se superan los límites.
    """
    def __init__(self, session: AsyncSession, max_retries: int = 3):
        """
        Inicializa el gestor del ciclo de validación.

        Args:
            session: Sesión de base de datos asíncrona.
            max_retries: Número máximo de reintentos permitidos antes de escalar.
        """
        self.session = session
        self.max_retries = max_retries

    async def handle_feedback(
        self,
        task_id: str,
        action: str,  # approve, reject, retry, escalate
        feedback: Optional[str] = None,
        who: Optional[str] = None,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Procesa el feedback del usuario asignado a una tarea y determina el siguiente estado del flujo.

        Args:
            task_id: Identificador de la tarea o ejecución.
            action: Acción tomada por el usuario (approve, reject, retry, escalate).
            feedback: Comentarios aclaratorios del usuario.
            who: Identificador del usuario que realiza la acción.
            fields: Lista de campos afectados por el feedback.

        Returns:
            Diccionario con el nuevo estado de la tarea y el conteo de reintentos.
        """
        # Contar reintentos previos (solo si la acción es retry)
        # We need to count how many 'retry' actions have happened for this task
        current_retries = (await self.session.exec(
            select(func.count(ValidationHistory.id)).where(
                ValidationHistory.task_id == task_id,
                ValidationHistory.user_action == "retry"
            )
        )).one()

        # Determine next retries count
        next_retries = current_retries + 1 if action == "retry" else current_retries

        # Persistir en historial
        record = ValidationHistory(
            task_id=task_id,
            user_action=action,
            feedback=feedback,
            who=who,
            retries=next_retries,
            fields_affected=json.dumps(fields) if fields else None,
            timestamp=datetime.utcnow(),
        )
        self.session.add(record)
        await self.session.commit()

        # Determinar nuevo estado
        if action == "approve":
            return {"status": "approved", "retries": current_retries}

        elif action == "reject":
            return {"status": "rejected", "retries": current_retries}
            
        elif action == "escalate":
             await self._trigger_escalation(task_id)
             return {
                 "status": "escalated",
                 "retries": current_retries,
                 "fields_affected": fields
             }

        elif action == "retry":
            if next_retries > self.max_retries:
                # Escalar automáticamente
                await self._trigger_escalation(task_id)
                return {
                    "status": "escalated",
                    "retries": next_retries,
                    "fields_affected": fields,
                }

            return {
                "status": "regenerating",
                "retries": next_retries,
                "fields_affected": fields,
            }

    async def _trigger_escalation(self, task_id: str):
        """Invoca SupportPackager para crear ticket."""
        # Se implementará en P18B - Por ahora es un placeholder
        pass

    async def get_feedback_summary(self, task_id: str) -> Dict[str, Any]:
        """
        Obtiene un resumen histórico del feedback para proporcionar pistas (hints)
        al motor de IA en el próximo intento de regeneración.

        Args:
            task_id: Identificador de la tarea.

        Returns:
            Resumen con intentos totales, campos con problemas y últimos comentarios.
        """
        history = (await self.session.exec(
            select(ValidationHistory)
            .where(ValidationHistory.task_id == task_id)
            .order_by(ValidationHistory.timestamp.desc())
        )).all()

        all_fields = set()
        feedbacks = []

        for h in history:
            if h.feedback:
                feedbacks.append(h.feedback)
            if h.fields_affected:
                try:
                    fields = json.loads(h.fields_affected)
                    if isinstance(fields, list):
                        all_fields.update(fields)
                except json.JSONDecodeError:
                    pass

        return {
            "total_attempts": len(history),
            "fields_with_issues": list(all_fields),
            "recent_feedbacks": feedbacks[:3],  # últimos 3
        }
