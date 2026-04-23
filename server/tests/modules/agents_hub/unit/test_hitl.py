"""Tests para el bucle Human-in-the-Loop (Prompt 4.11)."""
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestHumanInTheLoop:

    @pytest.mark.asyncio
    async def test_draft_revision_loop(self) -> None:
        """Tras el feedback del usuario, el agente genera una segunda versión."""
        from server.app.modules.agents_hub.agent.hitl import HumanInTheLoopNode

        hitl = HumanInTheLoopNode()

        initial_draft = "## Borrador inicial\n\nContenido de prueba."
        user_feedback = "Necesito que incluyas el apartado de conclusiones."

        with patch.object(hitl, '_revise_draft', new_callable=AsyncMock) as mock_revise:
            mock_revise.return_value = (
                "## Borrador revisado\n\nContenido de prueba.\n\n## Conclusiones\n\nConclusión."
            )
            revised = await hitl.process_feedback(
                draft=initial_draft,
                feedback=user_feedback,
            )

        mock_revise.assert_called_once_with(draft=initial_draft, feedback=user_feedback)
        assert revised != initial_draft

    @pytest.mark.asyncio
    async def test_finalize_signal_triggers_export(self) -> None:
        """La señal 'FINALIZAR' cierra el bucle y activa el proceso de exportación."""
        from server.app.modules.agents_hub.agent.hitl import HumanInTheLoopNode, FINALIZE_SIGNAL

        hitl = HumanInTheLoopNode()

        is_final = hitl.is_finalize_signal(FINALIZE_SIGNAL)
        is_not_final = hitl.is_finalize_signal("Dame más detalles.")

        assert is_final is True
        assert is_not_final is False
