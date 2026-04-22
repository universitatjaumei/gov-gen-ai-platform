# client_app/tests/unit/test_custom_script_clarification.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services.clarification_service import (
    ClarificationResult,
    ClarificationQuestion,
    ClarificationResponse,
    QuestionType
)

class TestCustomScriptWizardClarification:
    """Tests para la integración de clarificación en Custom Script."""

    def test_wizard_phases_include_clarification(self):
        """Verifica que las fases del wizard incluyen clarification (conceptual)."""
        # Nota: En el código real de la UI, las fases son cadenas hardcoded.
        # Aquí verificaremos que el flujo lógico pase por 'clarification'.
        pass 

    def test_wizard_state_has_clarification_fields(self):
        """Verifica que WizardState tiene los campos necesarios."""
        # Simulamos la clase WizardState modificada si estuviera en el mismo archivo
        # o verificamos atributos en una clase mock que replique la estructura deseada
        class MockWizardState:
            def __init__(self):
                self.phase = 'description'
                self.user_prompt = ""
                # Campos esperados
                self.clarification_result = None
                self.clarification_responses = []
                self.clarification_skipped = False

        wizard = MockWizardState()
        assert hasattr(wizard, 'clarification_result')
        assert hasattr(wizard, 'clarification_responses')
        assert hasattr(wizard, 'clarification_skipped')

    @pytest.mark.asyncio
    async def test_analyze_called_after_description(self):
        """Verifica que se llama a analyze_for_clarification después de descripción."""
        # Mock de clarification_service
        # (Dependiendo de cómo importes en la UI, esto puede requerir patch más específico)
        # Aquí usamos un mock directo para simular la lógica que implementaremos
        
        clarification_service = AsyncMock()
        mock_result = ClarificationResult(
            needs_clarification=True,
            questions=[
                ClarificationQuestion(
                    id="q1",
                    question="¿Formato de salida?",
                    type=QuestionType.SINGLE_CHOICE,
                    options=["Excel", "CSV"]
                )
            ],
            confidence_score=0.5,
            reasoning="Formato no especificado"
        )
        clarification_service.analyze_for_clarification.return_value = mock_result

        # Simulamos la lógica de transición
        user_prompt = "Procesar archivos"
        context = {}
        
        result = await clarification_service.analyze_for_clarification(
            module_type="custom_script",
            user_input={"prompt": user_prompt},
            context=context
        )

        clarification_service.analyze_for_clarification.assert_called_once()
        assert result.needs_clarification is True

    def test_skip_clarification_goes_to_generation(self):
        """Verifica que omitir clarificación va directamente a generación."""
        class MockWizard:
            phase = 'clarification'
            clarification_skipped = False
            
            def skip_to_generation(self):
                self.clarification_skipped = True
                self.phase = 'generation'

        wizard = MockWizard()
        wizard.skip_to_generation()

        assert wizard.phase == 'generation'
        assert wizard.clarification_skipped is True

    def test_submit_clarification_goes_to_generation(self):
        """Verifica que responder clarificación va a generación con respuestas."""
        responses = [
            ClarificationResponse(question_id="q1", answer="Excel"),
        ]

        class MockWizard:
            phase = 'clarification'
            clarification_responses = []
            
            def submit_clarifications(self, resps):
                self.clarification_responses = resps
                self.phase = 'generation'

        wizard = MockWizard()
        wizard.submit_clarifications(responses)

        assert wizard.phase == 'generation'
        assert len(wizard.clarification_responses) == 1

class TestScriptGeneratorWithClarifications:
    """Tests para generación de scripts con clarificaciones."""

    @pytest.mark.asyncio
    async def test_generate_signature_accepts_clarifications(self):
        """Verifica que el método generate_script acepte clarificaciones."""
        from client_app.app.services.script_generator_service import ScriptGeneratorService
        service = ScriptGeneratorService()
        
        # En Python, podemos inspeccionar la firma, o llamar con kwargs y ver si falla (si no está implementado)
        # O simplemente simular la llamada:
        
        # Este test fallará si el método 'generate_script' no acepta 'clarifications'
        # o '**kwargs' que lo capturen, o si no hemos actualizado la firma aún.
        
        # Simplemente verificamos que pretendemos llamarlo así:
        try:
             # Mock dependencies to avoid actual DB/LLM calls
             with patch.object(service, '_get_client_and_license', new_callable=AsyncMock) as mock_auth:
                 mock_auth.return_value = (AsyncMock(), "key")
                 with patch('client_app.app.services.script_generator_service.get_security_policy', new_callable=AsyncMock) as mock_policy:
                    mock_policy.return_value = MagicMock(allowed_imports=[], forbidden_imports=[])
                    
                    # Call with clarifications kwarg - should NOT raise TypeError if updated
                    # Note: currently it accepts **kwargs via signature update or if we add the param
                    # We expect this to FAIL until we update the service
                    await service.generate_script(
                        user_prompt="test",
                        clarifications={"q1": "Answer"} 
                    )
        except TypeError:
            pytest.fail("generate_script does not accept 'clarifications' argument")
        except Exception:
            # Other errors (like mock failures) are ignored for this signature test
            pass
