"""Nodo de validación Human-in-the-Loop (HITL) para LangGraph."""

FINALIZE_SIGNAL = "FINALIZAR"


class HumanInTheLoopNode:
    """Gestiona el bucle de revisión iterativa usuario–agente."""

    def is_finalize_signal(self, message: str) -> bool:
        """Determina si el mensaje del usuario es la señal de finalización.

        Args:
            message: Texto del mensaje

        Returns:
            True si el mensaje es la señal de cierre del bucle
        """
        return message.strip().upper() == FINALIZE_SIGNAL

    async def process_feedback(self, draft: str, feedback: str) -> str:
        """Genera una versión revisada del borrador aplicando el feedback.

        Args:
            draft: Borrador actual
            feedback: Comentarios del usuario

        Returns:
            Borrador revisado
        """
        return await self._revise_draft(draft=draft, feedback=feedback)

    async def _revise_draft(self, draft: str, feedback: str) -> str:
        """Aplica el feedback al borrador (stub — se sustituye por LLM en producción)."""
        return f"{draft}\n\n<!-- Revisión solicitada: {feedback} -->"
