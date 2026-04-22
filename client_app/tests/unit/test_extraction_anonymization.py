# client_app/tests/unit/test_extraction_anonymization.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestExtractionAnonymization:
    """Tests de anonimización obligatoria en extracción."""

    @pytest.mark.asyncio
    async def test_extraction_always_anonymizes(self):
        """La extracción SIEMPRE anonimiza - no hay parámetro para desactivar."""
        from client_app.app.services.extraction_service import ExtractionService

        service = ExtractionService(logger=MagicMock())

        # Llamar a extracción - NO hay parámetro anonymize
        # Si existiera, este test fallaría porque el método no lo acepta
        import inspect
        sig = inspect.signature(service.extract_with_ai)
        param_names = list(sig.parameters.keys())

        assert "anonymize" not in param_names, "No debe existir parámetro 'anonymize'"

    @pytest.mark.asyncio
    async def test_text_is_anonymized_before_ai_call(self, test_client_db):
        """El texto se anonimiza ANTES de llamar a la IA."""
        from client_app.app.services.extraction_service import ExtractionService

        # Texto con datos sensibles (Email es determinista por Regex)
        original_text = "DNI: 12345678Z, Email: test@test.com"

        # Mock que captura lo que se envía a IA
        captured_text = None

        async def mock_ai_call(file_path=None, user_definition=None, target_fields=None, usar_tier_2=False, texto_fitz=None, texto_plumber=None, **kwargs):
            nonlocal captured_text
            captured_text = texto_fitz
            return {"email": "fake@fake.com", "dni": "Fake DNI"}

        mock_client = AsyncMock()
        mock_client.extract_data = mock_ai_call

        service = ExtractionService(logger=MagicMock())

        # Mock _get_brain_client to return our mock client
        with patch.object(service, '_get_brain_client', return_value=(mock_client, "test-key")):
            # Ejecutar extracción
            await service.extract_with_ai(
                texto_fitz=original_text,
                texto_plumber=original_text,
                campos=["email", "dni"],
                config={}
            )

        # Verificar que lo enviado a IA NO contiene datos originales
        assert captured_text is not None
        assert "12345678Z" not in captured_text, "DNI Real se filtró a la IA"
        assert "test@test.com" not in captured_text, "Email Real se filtró a la IA"

    @pytest.mark.asyncio
    async def test_result_is_rehydrated_after_ai_call(self, test_client_db):
        """El resultado se rehidrata con datos originales."""
        from client_app.app.services.extraction_service import ExtractionService

        original_text = "DNI: 12345678Z, Nombre: Juan Pérez"

        # This test verifies the deanonymization logic is called
        # We can verify it by patching AnonymizationContext
        pass  # Covered by test_anonymization_integrated_flow

    @pytest.mark.asyncio
    async def test_anonymization_integrated_flow(self, test_client_db):
        """Test flow using real Anonymizer context via side-effects or spies."""
        from client_app.app.services.extraction_service import ExtractionService

        service = ExtractionService(logger=MagicMock())

        # Mock client
        mock_client = AsyncMock()
        mock_client.extract_data.return_value = {"data": "FAKE"}

        # We patch AnonymizationContext to control fakes
        with patch("client_app.app.services.extraction_service.AnonymizationContext") as MockContext:
            ctx_instance = MockContext.return_value
            ctx_instance.anonymize.return_value = "Texto Anonimizado"
            ctx_instance.deanonymize.return_value = {"data": "REAL"}
            ctx_instance.fake_to_real = {"fake": "real"}  # for logging check
            ctx_instance.get_stats.return_value = {"entities": 1}

            with patch.object(service, '_get_brain_client', return_value=(mock_client, "test-key")):
                result, stats = await service.extract_with_ai(
                    texto_fitz="Original",
                    texto_plumber="Original",
                    campos=[],
                    config={}
                )

            # Check Anonymization called
            ctx_instance.anonymize.assert_called()
            # Check Brain called with Anon Text
            args = mock_client.extract_data.call_args
            assert args.kwargs['texto_fitz'] == "Texto Anonimizado"

            # Check Deanonymization called with Brain Result
            ctx_instance.deanonymize.assert_called_with({"data": "FAKE"})

            # Check Result is what Deanonymize returned
            assert result == {"data": "REAL"}

    @pytest.mark.asyncio
    async def test_entity_count_logged(self, test_client_db, caplog):
        """Se registra en logs cuántas entidades se anonimizaron."""
        import logging
        from client_app.app.services.extraction_service import ExtractionService

        test_logger = logging.getLogger("TestLogger")
        service = ExtractionService(logger=test_logger)

        mock_client = AsyncMock()
        mock_client.extract_data.return_value = {}

        # Patch AnonymizationContext to have some entities
        with patch("client_app.app.services.extraction_service.AnonymizationContext") as MockContext:
            ctx = MockContext.return_value
            ctx.fake_to_real = {"a": "b", "c": "d"}  # 2 entities
            ctx.anonymize.return_value = "..."
            ctx.deanonymize.return_value = {}
            ctx.get_stats.return_value = {"entities": 2}

            with patch.object(service, '_get_brain_client', return_value=(mock_client, "test-key")):
                with caplog.at_level(logging.INFO):
                    await service.extract_with_ai("", "", [], {})

            # Log should mention "Anonimizadas"
            assert any("Anonimizadas" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_anonymization_map_cleared_after_request(self, test_client_db):
        """El mapa de anonimización se limpia después de cada request."""
        from client_app.app.services.extraction_service import ExtractionService

        service = ExtractionService(logger=MagicMock())

        mock_client = AsyncMock()
        mock_client.extract_data.return_value = {}

        with patch("client_app.app.services.extraction_service.AnonymizationContext") as MockContext:
            ctx = MockContext.return_value
            ctx.fake_to_real = {}
            ctx.anonymize.return_value = ""
            ctx.deanonymize.return_value = {}
            ctx.get_stats.return_value = {}

            with patch.object(service, '_get_brain_client', return_value=(mock_client, "test-key")):
                await service.extract_with_ai("", "", [], {})

        assert service._anonymizer is None
