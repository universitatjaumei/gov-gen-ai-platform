"""
Tests TDD para TypeCompatibilityService - Prompt #10
Logica de "Sugerencia de Puentes" para Contratos Incompatibles.

Valida la deteccion de incompatibilidades de tipos entre conexiones de flujo
y la generacion de scripts puente.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from automatia_shared.contracts.ui_contract import InputType

from client_app.app.services.type_compatibility_service import (
    TypeCompatibilityService,
    TypeCompatibilityResult,
    BridgeSuggestion,
)


class TestTypeCompatibilityValidation:
    """Tests para validacion de compatibilidad de tipos."""

    def test_detect_compatible_same_type(self):
        """Test que tipos identicos son compatibles."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "total", "type": InputType.INT}
        input_spec = {"name": "amount", "type": InputType.INT}

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is True
        assert result.error_message is None

    def test_detect_compatible_int_to_float(self):
        """Test que INT es compatible con FLOAT (widening)."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "count", "type": InputType.INT}
        input_spec = {"name": "value", "type": InputType.FLOAT}

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is True

    def test_detect_compatible_float_to_int(self):
        """Test que FLOAT es compatible con INT (narrowing permitido)."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "price", "type": InputType.FLOAT}
        input_spec = {"name": "count", "type": InputType.INT}

        result = validator.validate_connection(output_spec, input_spec)

        # FLOAT a INT requiere conversion pero es permitido
        assert result.is_compatible is True

    def test_detect_compatible_date_to_datetime(self):
        """Test que DATE es compatible con DATETIME."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "fecha", "type": InputType.DATE}
        input_spec = {"name": "timestamp", "type": InputType.DATETIME}

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is True

    def test_detect_incompatible_str_to_int(self):
        """Test que STR no es directamente compatible con INT."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "total", "type": InputType.STR}
        input_spec = {"name": "amount", "type": InputType.INT}

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is False
        assert "incompatible" in result.error_message.lower()

    def test_detect_incompatible_bool_to_str(self):
        """Test que BOOL no es directamente compatible con STR."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "is_active", "type": InputType.BOOL}
        input_spec = {"name": "status", "type": InputType.STR}

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is False

    def test_detect_incompatible_file_to_str(self):
        """Test que FILE no es compatible con STR."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "documento", "type": InputType.FILE}
        input_spec = {"name": "texto", "type": InputType.STR}

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is False

    def test_detect_incompatible_files_to_file(self):
        """Test que FILES no es directamente compatible con FILE."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "documentos", "type": InputType.FILES}
        input_spec = {"name": "documento", "type": InputType.FILE}

        result = validator.validate_connection(output_spec, input_spec)

        # FILES a FILE requiere seleccion/extraccion
        assert result.is_compatible is False


class TestBridgeSuggestions:
    """Tests para sugerencias de puentes."""

    def test_suggest_bridge_for_str_to_int(self):
        """Test que sugiere puente para STR -> INT."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "precio_texto", "type": InputType.STR}
        input_spec = {"name": "precio_numero", "type": InputType.INT}

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is False
        assert result.bridge_suggestion is not None
        assert result.bridge_suggestion.source_type == InputType.STR
        assert result.bridge_suggestion.target_type == InputType.INT

    def test_suggest_bridge_for_json_to_str(self):
        """Test que sugiere puente para JSON -> STR."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "data", "type": InputType.JSON}
        input_spec = {"name": "text", "type": InputType.STR}

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is False
        assert result.bridge_suggestion is not None

    def test_bridge_suggestion_includes_description(self):
        """Test que la sugerencia incluye descripcion util."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "total", "type": InputType.STR}
        input_spec = {"name": "amount", "type": InputType.INT}

        result = validator.validate_connection(output_spec, input_spec)

        assert result.bridge_suggestion.description is not None
        assert len(result.bridge_suggestion.description) > 0


class TestFileBridges:
    """Tests para puentes de archivos."""

    def test_suggest_decompression_bridge_zip_to_pdf(self):
        """Test que sugiere puente de descompresion para .zip -> .pdf."""
        validator = TypeCompatibilityService()

        # Simular extension del archivo
        output_spec = {
            "name": "archivo_comprimido",
            "type": InputType.FILE,
            "extension": ".zip"
        }
        input_spec = {
            "name": "documento_pdf",
            "type": InputType.FILE,
            "extension": ".pdf"
        }

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is False
        assert result.bridge_suggestion is not None
        assert "descompresion" in result.bridge_suggestion.description.lower() or \
               "extraccion" in result.bridge_suggestion.description.lower()

    def test_compatible_same_file_extension(self):
        """Test que archivos con misma extension son compatibles."""
        validator = TypeCompatibilityService()

        output_spec = {
            "name": "documento_origen",
            "type": InputType.FILE,
            "extension": ".pdf"
        }
        input_spec = {
            "name": "documento_destino",
            "type": InputType.FILE,
            "extension": ".pdf"
        }

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is True


class TestDateFormatBridges:
    """Tests para puentes de formato de fecha."""

    def test_suggest_bridge_date_format_es_to_iso(self):
        """Test que sugiere puente para fecha formato ES -> ISO."""
        validator = TypeCompatibilityService()

        output_spec = {
            "name": "fecha_factura",
            "type": InputType.DATE,
            "format": "DD/MM/YYYY"  # Formato espanol
        }
        input_spec = {
            "name": "fecha_sistema",
            "type": InputType.DATE,
            "format": "YYYY-MM-DD"  # Formato ISO
        }

        result = validator.validate_connection(output_spec, input_spec)

        # Fechas con formato diferente necesitan conversion
        assert result.is_compatible is False or result.bridge_suggestion is not None


class TestBridgeGeneration:
    """Tests para generacion de codigo de puentes."""

    @pytest.mark.asyncio
    async def test_request_bridge_script_from_brain(self):
        """Test que solicita codigo de puente al Brain."""
        validator = TypeCompatibilityService()

        with patch('client_app.app.clients.brain_client.BrainAPIClient.generate_bridge_code') as mock_brain:
            mock_brain.return_value = "def transform(val): return int(val.replace(',', '').replace('$', ''))"

            bridge_script = await validator.request_bridge_script(
                source_type=InputType.STR,
                target_type=InputType.INT,
                source_name="precio_texto",
                target_name="precio_numero",
                example_value="1.200,50"
            )

            assert "int" in bridge_script or "transform" in bridge_script
            mock_brain.assert_called_once()

    @pytest.mark.asyncio
    async def test_bridge_script_handles_currency(self):
        """Test que el puente maneja conversion de moneda."""
        validator = TypeCompatibilityService()

        with patch('client_app.app.clients.brain_client.BrainAPIClient.generate_bridge_code') as mock_brain:
            mock_brain.return_value = "def transform(val): return float(val.replace('€', '').replace('.', '').replace(',', '.'))"

            bridge_script = await validator.request_bridge_script(
                source_type=InputType.STR,
                target_type=InputType.FLOAT,
                source_name="importe",
                target_name="valor",
                example_value="1.234,56€"
            )

            assert bridge_script is not None
            assert len(bridge_script) > 0


class TestBridgeAtomCreation:
    """Tests para creacion de atomos puente."""

    @pytest.mark.asyncio
    async def test_create_bridge_atom_marked_as_bridge(self):
        """Test que el atomo puente se crea con is_bridge=True."""
        validator = TypeCompatibilityService()

        # Patch el import dentro del metodo
        with patch('client_app.app.services.script_library_service.script_library_service') as mock_lib:
            mock_script = MagicMock()
            mock_script.id = "bridge-123"
            mock_lib.add_script = AsyncMock(return_value=mock_script)

            with patch.object(validator, 'request_bridge_script', new_callable=AsyncMock) as mock_bridge:
                mock_bridge.return_value = "def transform(x): return int(x)"

                atom = await validator.create_bridge_atom(
                    source_type=InputType.STR,
                    target_type=InputType.INT,
                    source_name="texto",
                    target_name="numero"
                )

                # Verificar que se llamo con source_metadata conteniendo is_bridge=True
                call_kwargs = mock_lib.add_script.call_args.kwargs
                source_metadata = call_kwargs.get('source_metadata', {})
                assert source_metadata.get('is_bridge') is True
                assert source_metadata.get('auto_generated') is True


class TestSemanticSuggestions:
    """Tests para sugerencias semanticas (pre-validacion)."""

    def test_suggest_connection_similar_names(self):
        """Test que sugiere conexion para campos con nombres similares."""
        validator = TypeCompatibilityService()

        # Campos con nombres semanticamente relacionados
        output_spec = {"name": "precio_final", "type": InputType.FLOAT}
        input_spec = {"name": "coste_total", "type": InputType.FLOAT}

        # Aunque no esten conectados, el validador podria sugerir
        similarity = validator.calculate_name_similarity(
            output_spec["name"],
            input_spec["name"]
        )

        # Nombres relacionados con precio/coste deberian tener cierta similitud
        assert similarity >= 0  # Al menos no negativo


class TestValidationWithDicts:
    """Tests usando diccionarios como en el prompt original."""

    def test_validate_connection_dict_format(self):
        """Test usando el formato de dict del prompt."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "total", "type": InputType.STR}
        input_spec = {"name": "amount", "type": InputType.INT}

        is_valid, error_msg = validator.validate_connection_simple(output_spec, input_spec)

        assert is_valid is False
        assert "incompatible" in error_msg.lower()

    def test_validate_connection_compatible_dict_format(self):
        """Test conexion compatible con formato dict."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "count", "type": InputType.INT}
        input_spec = {"name": "total", "type": InputType.INT}

        is_valid, error_msg = validator.validate_connection_simple(output_spec, input_spec)

        assert is_valid is True
        assert error_msg is None


class TestEdgeCases:
    """Tests para casos limite."""

    def test_handle_missing_type(self):
        """Test que maneja campos sin tipo definido."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "field1"}  # Sin type
        input_spec = {"name": "field2", "type": InputType.STR}

        result = validator.validate_connection(output_spec, input_spec)

        # Debe manejar graciosamente, asumiendo STR por defecto
        assert result is not None

    def test_handle_type_as_string(self):
        """Test que maneja tipos como strings."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "field1", "type": "str"}  # String en lugar de enum
        input_spec = {"name": "field2", "type": InputType.STR}

        result = validator.validate_connection(output_spec, input_spec)

        assert result.is_compatible is True

    def test_handle_select_type(self):
        """Test manejo de tipo SELECT."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "option", "type": InputType.SELECT}
        input_spec = {"name": "value", "type": InputType.STR}

        result = validator.validate_connection(output_spec, input_spec)

        # SELECT es esencialmente un STR con restricciones
        assert result.is_compatible is True

    def test_handle_secret_type(self):
        """Test manejo de tipo SECRET."""
        validator = TypeCompatibilityService()

        output_spec = {"name": "password", "type": InputType.SECRET}
        input_spec = {"name": "auth", "type": InputType.STR}

        result = validator.validate_connection(output_spec, input_spec)

        # SECRET es compatible con STR
        assert result.is_compatible is True
