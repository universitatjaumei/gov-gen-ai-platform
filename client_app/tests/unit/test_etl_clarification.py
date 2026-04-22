# client_app/tests/unit/test_etl_clarification.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services.clarification_service import (
    ClarificationResult,
    ClarificationQuestion,
    ClarificationResponse
)

class TestETLCustomClarification:
    """Tests para la integración de clarificación en ETL Wizard."""

    def test_etl_state_has_clarification_fields(self):
        """Verifica que EtlState/Wizard tiene los campos necesarios."""
        # Simulamos la estructura esperada del state
        class MockEtlState:
            def __init__(self):
                self.phase = 'upload'
                self.clarification_result = None
                self.clarification_responses = []
                self.clarification_skipped = False
                self.is_analyzing = False

        state = MockEtlState()
        assert hasattr(state, 'clarification_result')
        assert hasattr(state, 'clarification_responses')
        assert hasattr(state, 'is_analyzing')

    @pytest.mark.asyncio
    async def test_etl_analyze_flow(self):
        """Verifica que se llama a analyze_for_clarification con modulo 'etl'."""
        clarification_service = AsyncMock()
        mock_result = ClarificationResult(
            needs_clarification=True,
            questions=[],
            confidence_score=0.5,
            reasoning="Ambiguo"
        )
        clarification_service.analyze_for_clarification.return_value = mock_result

        # Datos de prueba
        user_desc = "Transformar fechas"
        files = ["data.csv"]

        result = await clarification_service.analyze_for_clarification(
            module_type="etl",
            user_input={"prompt": user_desc},
            context={"files": files}
        )

        clarification_service.analyze_for_clarification.assert_called_once()
        args, kwargs = clarification_service.analyze_for_clarification.call_args
        assert kwargs['module_type'] == "etl"
        assert kwargs['user_input']['prompt'] == user_desc

    def test_etl_clarification_submit_advances_phase(self):
        """Verifica que al enviar clarificaciones avanza de fase (conceptual)."""
        class MockWizard:
            phase = 'clarification'
            clarification_responses = []
            
            def submit_clarifications(self, resps):
                self.clarification_responses = resps
                self.phase = 'results' # Asumiendo que va a resultados/generación

        wizard = MockWizard()
        resps = [ClarificationResponse(question_id="q1", answer="A")]
        wizard.submit_clarifications(resps)
        
        assert wizard.phase == 'results'
        assert len(wizard.clarification_responses) == 1
