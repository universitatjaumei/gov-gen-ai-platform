
import pytest
from dataclasses import asdict
from client_app.app.services.clarification_service import (
    ClarificationService,
    ClarificationQuestion,
    ClarificationResponse,
    ClarificationResult,
    QuestionType
)

class TestClarificationModels:
    """Tests para los modelos de datos de clarificación."""

    def test_question_type_enum_values(self):
        """Verifica que QuestionType tiene todos los tipos necesarios."""
        assert QuestionType.SINGLE_CHOICE.value == "single_choice"
        assert QuestionType.MULTIPLE_CHOICE.value == "multiple_choice"
        assert QuestionType.FREE_TEXT.value == "free_text"
        assert QuestionType.YES_NO.value == "yes_no"
        assert QuestionType.FILE_UPLOAD.value == "file_upload"

    def test_clarification_question_creation(self):
        """Verifica la creación de ClarificationQuestion."""
        question = ClarificationQuestion(
            id="q1",
            question="¿En qué formato necesitas el resultado?",
            type=QuestionType.SINGLE_CHOICE,
            options=["Excel", "CSV", "JSON"],
            hint="Excel permite tablas dinámicas",
            required=True,
            default="Excel"
        )

        assert question.id == "q1"
        assert question.type == QuestionType.SINGLE_CHOICE
        assert len(question.options) == 3
        assert question.required is True

    def test_clarification_question_minimal(self):
        """Verifica creación con campos mínimos."""
        question = ClarificationQuestion(
            id="q2",
            question="¿Deseas sobrescribir los archivos originales?",
            type=QuestionType.YES_NO
        )

        assert question.options is None
        assert question.hint is None
        assert question.required is True  # Default
        assert question.default is None

    def test_clarification_response_single(self):
        """Verifica respuesta de tipo single."""
        response = ClarificationResponse(
            question_id="q1",
            answer="Excel"
        )

        assert response.question_id == "q1"
        assert response.answer == "Excel"

    def test_clarification_response_multiple(self):
        """Verifica respuesta de tipo multiple."""
        response = ClarificationResponse(
            question_id="q2",
            answer=["Total ventas", "Top productos"]
        )

        assert isinstance(response.answer, list)
        assert len(response.answer) == 2

    def test_clarification_result_needs_clarification(self):
        """Verifica ClarificationResult cuando necesita preguntas."""
        result = ClarificationResult(
            needs_clarification=True,
            questions=[
                ClarificationQuestion(
                    id="q1",
                    question="Pregunta 1",
                    type=QuestionType.SINGLE_CHOICE,
                    options=["A", "B"]
                )
            ],
            confidence_score=0.4,
            reasoning="La petición es ambigua en varios aspectos."
        )

        assert result.needs_clarification is True
        assert len(result.questions) == 1
        assert result.confidence_score == 0.4

    def test_clarification_result_no_clarification(self):
        """Verifica ClarificationResult cuando NO necesita preguntas."""
        result = ClarificationResult(
            needs_clarification=False,
            questions=[],
            confidence_score=0.9,
            reasoning="La información es suficientemente clara."
        )

        assert result.needs_clarification is False
        assert len(result.questions) == 0
        assert result.confidence_score > 0.8


class TestClarificationService:
    """Tests para el servicio de clarificación."""

    @pytest.fixture
    def service(self):
        return ClarificationService()

    def test_service_instantiation(self, service):
        """Verifica que el servicio se puede instanciar."""
        assert service is not None

    def test_supported_modules(self, service):
        """Verifica que los módulos soportados están definidos."""
        supported = service.get_supported_modules()

        assert "custom_script" in supported
        assert "etl" in supported
        assert "rpa" in supported
        assert "extraction" in supported

    def test_module_tier_mapping(self, service):
        """Verifica el mapeo de módulo a tier de modelo."""
        assert service.get_module_tier("custom_script") == 3  # supervision
        assert service.get_module_tier("etl") == 2  # logico_navegacion
        assert service.get_module_tier("rpa") == 2
        assert service.get_module_tier("extraction") == 2

    @pytest.mark.asyncio
    async def test_analyze_requires_valid_module(self, service):
        """Verifica que analyze_for_clarification valida el módulo."""
        with pytest.raises(ValueError, match="Módulo no soportado"):
            await service.analyze_for_clarification(
                module_type="invalid_module",
                user_input={"prompt": "test"},
                context={}
            )

    @pytest.mark.asyncio
    async def test_analyze_returns_result_structure(self, service):
        """Verifica que analyze devuelve ClarificationResult."""
        # Mock del cliente de IA
        from unittest.mock import AsyncMock, patch

        mock_response = {
            "needs_clarification": True,
            "confidence_score": 0.5,
            "reasoning": "Test reasoning",
            "questions": [
                {
                    "id": "q1",
                    "question": "Test question",
                    "type": "single_choice",
                    "options": ["A", "B"],
                    "required": True
                }
            ]
        }

        # Mock _call_ai_for_analysis directly to avoid external dependencies
        with patch.object(service, '_call_ai_for_analysis', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await service.analyze_for_clarification(
                module_type="custom_script",
                user_input={"prompt": "Procesar archivos CSV"},
                context={}
            )

            assert isinstance(result, ClarificationResult)
            assert result.needs_clarification is True
            assert len(result.questions) == 1

    def test_confidence_threshold(self, service):
        """Verifica el umbral de confianza para omitir clarificación."""
        # Si confidence >= 0.8, no debería necesitar clarificación
        assert service.CONFIDENCE_THRESHOLD == 0.8

    def test_max_questions(self, service):
        """Verifica el límite máximo de preguntas."""
        assert service.MAX_QUESTIONS == 3
