"""
Tests para servicio de validación de contratos.
TDD: Valida compatibilidad entre output_contract e input_contract.
Data Contracts Fase 1, Prompt 3.
"""
import pytest
from client_app.app.services.contract_validator_service import (
    ContractValidator,
    validate_contract_compatibility,
    get_missing_fields
)


class TestContractValidation:
    """Tests para validación básica de compatibilidad."""

    def test_compatible_simple_types(self):
        """
        Contratos con tipos simples compatibles deben validar.
        """
        output = {
            "type": "object",
            "properties": {
                "file": {"type": "string"}
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "file": {"type": "string"}
            },
            "required": ["file"]
        }

        assert validate_contract_compatibility(output, input_contract) == True

    def test_incompatible_missing_field(self):
        """
        Si falta un campo requerido, debe fallar.
        """
        output = {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "file": {"type": "string"}
            },
            "required": ["file"]
        }

        assert validate_contract_compatibility(output, input_contract) == False

    def test_compatible_with_extra_fields(self):
        """
        Output con campos extra debe ser compatible.
        """
        output = {
            "type": "object",
            "properties": {
                "file": {"type": "string"},
                "metadata": {"type": "object"}  # Extra
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "file": {"type": "string"}
            },
            "required": ["file"]
        }

        assert validate_contract_compatibility(output, input_contract) == True

    def test_incompatible_type_mismatch(self):
        """
        Tipos incompatibles deben fallar.
        """
        output = {
            "type": "object",
            "properties": {
                "count": {"type": "string"}
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"}
            },
            "required": ["count"]
        }

        assert validate_contract_compatibility(output, input_contract) == False

    def test_get_missing_fields(self):
        """
        Debe retornar lista de campos faltantes.
        """
        output = {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "language": {"type": "string"}
            },
            "required": ["text", "language"]
        }

        missing = get_missing_fields(output, input_contract)
        assert "language" in missing
        assert "text" not in missing

    def test_get_missing_fields_type_mismatch(self):
        """
        Campos con tipos incompatibles también deben reportarse.
        """
        output = {
            "type": "object",
            "properties": {
                "count": {"type": "string"}
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"}
            },
            "required": ["count"]
        }

        missing = get_missing_fields(output, input_contract)
        # Debe indicar que count tiene tipo incompatible
        assert any("count" in field for field in missing)


class TestContractValidationAdvanced:
    """Tests para casos avanzados."""

    def test_array_type_compatibility(self):
        """
        Arrays de tipos compatibles deben validar.
        """
        output = {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["files"]
        }

        assert validate_contract_compatibility(output, input_contract) == True

    def test_array_type_incompatibility(self):
        """
        Arrays con tipos de items diferentes deben fallar.
        """
        output = {
            "type": "object",
            "properties": {
                "values": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "values": {
                    "type": "array",
                    "items": {"type": "integer"}
                }
            },
            "required": ["values"]
        }

        assert validate_contract_compatibility(output, input_contract) == False

    def test_nested_object_compatibility(self):
        """
        Objetos anidados deben validar correctamente.
        """
        output = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"}
                    }
                }
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    },
                    "required": ["name"]
                }
            },
            "required": ["user"]
        }

        assert validate_contract_compatibility(output, input_contract) == True

    def test_nested_object_missing_required(self):
        """
        Objetos anidados con campos requeridos faltantes deben fallar.
        """
        output = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"}
                    }
                }
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    },
                    "required": ["name"]
                }
            },
            "required": ["user"]
        }

        assert validate_contract_compatibility(output, input_contract) == False

    def test_any_type_accepts_all(self):
        """
        Tipo 'any' debe aceptar cualquier tipo.
        """
        output = {
            "type": "object",
            "properties": {
                "data": {"type": "string"}
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "data": {"type": "any"}
            },
            "required": ["data"]
        }

        assert validate_contract_compatibility(output, input_contract) == True

    def test_integer_to_number_coercion(self):
        """
        Integer debe ser compatible con number.
        """
        output = {
            "type": "object",
            "properties": {
                "value": {"type": "integer"}
            }
        }
        input_contract = {
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            },
            "required": ["value"]
        }

        assert validate_contract_compatibility(output, input_contract) == True

    def test_no_required_fields(self):
        """
        Si no hay campos requeridos, siempre es compatible.
        """
        output = {
            "type": "object",
            "properties": {}
        }
        input_contract = {
            "type": "object",
            "properties": {
                "optional_field": {"type": "string"}
            }
            # No "required" key
        }

        assert validate_contract_compatibility(output, input_contract) == True

    def test_empty_contracts(self):
        """
        Contratos vacíos deben ser compatibles.
        """
        output = {"type": "object", "properties": {}}
        input_contract = {"type": "object", "properties": {}}

        assert validate_contract_compatibility(output, input_contract) == True


class TestContractValidatorClass:
    """Tests para la clase ContractValidator directamente."""

    def test_are_types_compatible_same_type(self):
        """Tipos idénticos son compatibles."""
        assert ContractValidator.are_types_compatible("string", "string") == True
        assert ContractValidator.are_types_compatible("integer", "integer") == True
        assert ContractValidator.are_types_compatible("boolean", "boolean") == True

    def test_are_types_compatible_any(self):
        """Tipo 'any' acepta todo."""
        assert ContractValidator.are_types_compatible("string", "any") == True
        assert ContractValidator.are_types_compatible("integer", "any") == True
        assert ContractValidator.are_types_compatible("object", "any") == True

    def test_are_types_compatible_integer_to_number(self):
        """Integer es compatible con number."""
        assert ContractValidator.are_types_compatible("integer", "number") == True

    def test_are_types_incompatible(self):
        """Tipos incompatibles retornan False."""
        assert ContractValidator.are_types_compatible("string", "integer") == False
        assert ContractValidator.are_types_compatible("boolean", "string") == False
        assert ContractValidator.are_types_compatible("array", "object") == False
