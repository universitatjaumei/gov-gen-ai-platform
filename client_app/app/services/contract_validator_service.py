"""
Servicio de validación de contratos de datos entre átomos.

Valida que el output_contract de un átomo sea compatible
con el input_contract del siguiente átomo en un flujo.

Data Contracts Fase 1, Prompt 3.
"""
from typing import Dict, List, Any, Optional


class ContractValidator:
    """Validador de compatibilidad entre contratos de datos."""

    @staticmethod
    def are_types_compatible(output_type: Optional[str], input_type: Optional[str]) -> bool:
        """
        Verificar si dos tipos son compatibles.

        Args:
            output_type: Tipo del campo de salida
            input_type: Tipo del campo de entrada

        Returns:
            True si son compatibles
        """
        # Si alguno es None, no son compatibles
        if output_type is None or input_type is None:
            return False

        # Tipo 'any' acepta cualquier cosa
        if input_type == "any":
            return True

        # Tipos idénticos son compatibles
        if output_type == input_type:
            return True

        # Número puede aceptar integer
        if input_type == "number" and output_type == "integer":
            return True

        return False

    @staticmethod
    def validate_contract_compatibility(
        output_contract: Dict[str, Any],
        input_contract: Dict[str, Any]
    ) -> bool:
        """
        Validar que output_contract sea compatible con input_contract.

        Args:
            output_contract: JSON Schema del output del átomo anterior
            input_contract: JSON Schema del input del átomo siguiente

        Returns:
            True si son compatibles
        """
        output_props = output_contract.get("properties", {})
        input_props = input_contract.get("properties", {})
        required_fields = input_contract.get("required", [])

        # Si no hay campos requeridos, siempre es compatible
        if not required_fields:
            return True

        # Verificar que todos los campos requeridos existan y sean compatibles
        for field in required_fields:
            if field not in output_props:
                return False

            output_field = output_props[field]
            input_field = input_props.get(field, {})

            output_type = output_field.get("type")
            input_type = input_field.get("type")

            # Verificar compatibilidad de tipos
            if not ContractValidator.are_types_compatible(output_type, input_type):
                return False

            # Si son arrays, verificar items
            if output_type == "array" and input_type == "array":
                output_items = output_field.get("items", {})
                input_items = input_field.get("items", {})

                output_item_type = output_items.get("type")
                input_item_type = input_items.get("type")

                if not ContractValidator.are_types_compatible(output_item_type, input_item_type):
                    return False

            # Si son objetos, validar recursivamente
            if output_type == "object" and input_type == "object":
                if not ContractValidator.validate_contract_compatibility(
                    output_field,
                    input_field
                ):
                    return False

        return True

    @staticmethod
    def get_missing_fields(
        output_contract: Dict[str, Any],
        input_contract: Dict[str, Any]
    ) -> List[str]:
        """
        Obtener lista de campos requeridos que faltan o son incompatibles.

        Args:
            output_contract: JSON Schema del output
            input_contract: JSON Schema del input

        Returns:
            Lista de nombres de campos faltantes o con problemas
        """
        output_props = output_contract.get("properties", {})
        input_props = input_contract.get("properties", {})
        required_fields = input_contract.get("required", [])

        missing = []
        for field in required_fields:
            if field not in output_props:
                missing.append(field)
            else:
                # Verificar compatibilidad de tipos
                output_type = output_props[field].get("type")
                input_type = input_props.get(field, {}).get("type")

                if not ContractValidator.are_types_compatible(output_type, input_type):
                    missing.append(f"{field} (tipo incompatible: {output_type} -> {input_type})")

        return missing

    @staticmethod
    def get_compatibility_report(
        output_contract: Dict[str, Any],
        input_contract: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generar reporte detallado de compatibilidad.

        Args:
            output_contract: JSON Schema del output
            input_contract: JSON Schema del input

        Returns:
            Dict con is_compatible, missing_fields, y detalles
        """
        is_compatible = ContractValidator.validate_contract_compatibility(
            output_contract, input_contract
        )
        missing = ContractValidator.get_missing_fields(output_contract, input_contract)

        output_props = output_contract.get("properties", {})
        input_props = input_contract.get("properties", {})
        required_fields = input_contract.get("required", [])

        # Campos que sí coinciden
        matched_fields = [
            f for f in required_fields
            if f in output_props and f not in [m.split(" ")[0] for m in missing]
        ]

        # Campos extra en output (no requeridos por input)
        extra_fields = [f for f in output_props if f not in input_props]

        return {
            "is_compatible": is_compatible,
            "missing_fields": missing,
            "matched_fields": matched_fields,
            "extra_fields": extra_fields,
            "required_count": len(required_fields),
            "matched_count": len(matched_fields)
        }


# Funciones de conveniencia para uso directo
def validate_contract_compatibility(output: Dict[str, Any], input_contract: Dict[str, Any]) -> bool:
    """Wrapper para validación rápida de compatibilidad."""
    return ContractValidator.validate_contract_compatibility(output, input_contract)


def get_missing_fields(output: Dict[str, Any], input_contract: Dict[str, Any]) -> List[str]:
    """Wrapper para obtener campos faltantes."""
    return ContractValidator.get_missing_fields(output, input_contract)


def get_compatibility_report(output: Dict[str, Any], input_contract: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper para obtener reporte completo de compatibilidad."""
    return ContractValidator.get_compatibility_report(output, input_contract)
