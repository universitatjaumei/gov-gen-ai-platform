"""
Validador de mapeo de variables para pasos de informe.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class MappingValidationResult:
    """Resultado de validación de mapeo."""
    is_valid: bool
    missing_fields: List[str] = field(default_factory=list)
    type_mismatches: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def validate_mapping(
    mapping: Dict[str, str],
    input_schema: Dict[str, Any],
    available_variables: Optional[Dict[str, Any]] = None
) -> MappingValidationResult:
    """
    Validar que el mapeo cubra todos los campos requeridos del esquema.

    Args:
        mapping: Diccionario de campo -> expresión de variable
        input_schema: JSON Schema del input esperado
        available_variables: Variables disponibles del flujo (opcional)

    Returns:
        Resultado de la validación
    """
    result = MappingValidationResult(is_valid=True)

    # Obtener campos requeridos
    required_fields = input_schema.get("required", [])
    properties = input_schema.get("properties", {})

    # Verificar campos requeridos
    for field_name in required_fields:
        if field_name not in mapping or not mapping[field_name]:
            result.is_valid = False
            result.missing_fields.append(field_name)

    # Verificar tipos si hay variables disponibles
    if available_variables:
        for field_name, var_expr in mapping.items():
            if field_name in properties:
                expected_type = properties[field_name].get("type")
                actual_type = _infer_variable_type(var_expr, available_variables)

                if actual_type and expected_type and not _types_compatible(actual_type, expected_type):
                    result.type_mismatches.append({
                        "field": field_name,
                        "expected": expected_type,
                        "actual": actual_type
                    })

    # Advertencias para campos opcionales no mapeados
    for field_name in properties:
        if field_name not in mapping and field_name not in required_fields:
            result.warnings.append(f"Campo opcional '{field_name}' no mapeado")

    return result


def _infer_variable_type(var_expr: str, available_variables: Dict[str, Any]) -> Optional[str]:
    """Inferir tipo de una expresión de variable."""
    # Si es literal string
    if var_expr.startswith("'") and var_expr.endswith("'"):
        return "string"

    # Si es número
    try:
        float(var_expr)
        return "number"
    except ValueError:
        pass

    # Buscar en variables disponibles
    parts = var_expr.split(".")
    current = available_variables
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    if isinstance(current, str):
        return "string"
    elif isinstance(current, (int, float)):
        return "number"
    elif isinstance(current, list):
        return "array"
    elif isinstance(current, dict):
        return "object"

    return None


def _types_compatible(actual: str, expected: str) -> bool:
    """Verificar compatibilidad de tipos."""
    if actual == expected:
        return True

    # Compatibilidades especiales
    compatible = {
        ("integer", "number"): True,
        ("number", "string"): True,  # Coerción permitida
    }

    return compatible.get((actual, expected), False)
