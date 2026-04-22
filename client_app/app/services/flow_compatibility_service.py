"""
Servicio de validación de compatibilidad entre átomos en flujos.

Analiza si los datos de salida de un átomo son compatibles con
las entradas esperadas por otro, y sugiere transformaciones si es necesario.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from automatia_shared.contracts.ui_contract import (
    InputType, InputDefinition, Constraints,
    OutputSchema, OutputField, UIContract
)


class CompatibilityStatus(str, Enum):
    """Estado de compatibilidad entre campos/átomos."""
    COMPATIBLE = "compatible"      # Conexión directa sin problemas
    COERCIBLE = "coercible"        # Requiere conversión automática simple
    WARNING = "warning"            # Compatible pero con advertencias
    RISKY = "risky"                # Puede fallar en runtime
    INCOMPATIBLE = "incompatible"  # No se puede conectar


@dataclass
class FieldCompatibilityResult:
    """Resultado de compatibilidad para un campo específico."""
    source_field: str
    target_field: str
    status: CompatibilityStatus
    message: str = ""
    coercion_needed: bool = False
    coercion_code: Optional[str] = None
    requires_bridge: bool = False


@dataclass
class LinkCompatibilityResult:
    """Resultado de compatibilidad para una conexión completa."""
    status: CompatibilityStatus
    message: str = ""
    field_results: List[FieldCompatibilityResult] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    bridge_prompt: Optional[str] = None  # Prompt para generar bridge con IA


# Matriz de coerción automática entre tipos
COERCION_MATRIX: Dict[tuple, tuple] = {
    # (source_type, target_type): (is_safe, coercion_code)
    (InputType.INT, InputType.STR): (True, "str({value})"),
    (InputType.FLOAT, InputType.STR): (True, "str({value})"),
    (InputType.BOOL, InputType.STR): (True, "str({value})"),
    (InputType.INT, InputType.FLOAT): (True, "float({value})"),
    (InputType.STR, InputType.INT): (False, "int({value})"),  # Risky
    (InputType.STR, InputType.FLOAT): (False, "float({value})"),  # Risky
    (InputType.STR, InputType.BOOL): (True, "{value}.lower() in ('true', '1', 'yes')"),
}


class FlowCompatibilityService:
    """
    Servicio para validar compatibilidad de conexiones en el editor de flujos.

    Uso:
        service = FlowCompatibilityService()
        result = service.validate_atom_link(source_output, target_input)

        if result.status == CompatibilityStatus.INCOMPATIBLE:
            # Mostrar error y sugerir bridge
            print(result.bridge_prompt)
    """

    def check_field_compatibility(
        self,
        source: OutputField,
        target: InputDefinition
    ) -> FieldCompatibilityResult:
        """
        Valida compatibilidad entre un campo de salida y uno de entrada.
        """
        result = FieldCompatibilityResult(
            source_field=source.name,
            target_field=target.name,
            status=CompatibilityStatus.COMPATIBLE
        )

        # 1. Verificar tipos
        if source.type != target.type:
            coercion = COERCION_MATRIX.get((source.type, target.type))

            if coercion:
                is_safe, code = coercion
                result.coercion_needed = True
                result.coercion_code = code
                result.status = CompatibilityStatus.COERCIBLE if is_safe else CompatibilityStatus.RISKY
                result.message = f"Conversión de {source.type.value} a {target.type.value}"
            else:
                result.status = CompatibilityStatus.INCOMPATIBLE
                result.requires_bridge = True
                result.message = f"Tipos incompatibles: {source.type.value} → {target.type.value}"
                return result

        # 2. Verificar constraints
        if target.constraints:
            constraint_issues = self._check_constraints(source, target)
            if constraint_issues:
                if result.status == CompatibilityStatus.COMPATIBLE:
                    result.status = CompatibilityStatus.WARNING
                result.message += f" | Constraints: {constraint_issues}"

        return result

    def _check_constraints(self, source: OutputField, target: InputDefinition) -> str:
        """Verifica si los constraints del destino pueden cumplirse."""
        issues = []
        tc = target.constraints
        sc = source.constraints

        if tc.min is not None:
            if not sc or sc.min is None or sc.min < tc.min:
                issues.append(f"Origen puede producir valores < {tc.min}")

        if tc.max is not None:
            if not sc or sc.max is None or sc.max > tc.max:
                issues.append(f"Origen puede producir valores > {tc.max}")

        if tc.regex and (not sc or not sc.regex):
            issues.append(f"Destino requiere formato regex no garantizado")

        return "; ".join(issues) if issues else ""

    def validate_atom_link(
        self,
        source_schema: OutputSchema,
        target_contract: UIContract
    ) -> LinkCompatibilityResult:
        """
        Valida la conexión completa entre dos átomos.

        Args:
            source_schema: Schema de salida del átomo origen
            target_contract: Contrato de entrada del átomo destino

        Returns:
            LinkCompatibilityResult con estado general y detalles por campo
        """
        result = LinkCompatibilityResult(status=CompatibilityStatus.COMPATIBLE)
        source_fields = {f.name: f for f in source_schema.fields}

        for target_input in target_contract.inputs:
            source_field = source_fields.get(target_input.name)

            if not source_field:
                if target_input.required:
                    result.missing_fields.append(target_input.name)
                    result.status = CompatibilityStatus.INCOMPATIBLE
                continue

            field_result = self.check_field_compatibility(source_field, target_input)
            result.field_results.append(field_result)

            # Propagar el peor estado
            # Enum comparison works by name usually, but here we want severity.
            # We need a way to compare severity.
            # Let's map to int.
            severity = {
               CompatibilityStatus.COMPATIBLE: 0,
               CompatibilityStatus.COERCIBLE: 1,
               CompatibilityStatus.WARNING: 2,
               CompatibilityStatus.RISKY: 3,
               CompatibilityStatus.INCOMPATIBLE: 4
            }
            
            if severity[field_result.status] > severity[result.status]:
                result.status = field_result.status

        # Generar mensaje y prompt de bridge si es necesario
        if result.missing_fields:
            if result.message: result.message += ". "
            result.message += f"Campos requeridos faltantes: {', '.join(result.missing_fields)}"

        if result.status == CompatibilityStatus.INCOMPATIBLE:
            result.bridge_prompt = self._generate_bridge_prompt(
                source_schema, target_contract, result
            )

        return result

    def _generate_bridge_prompt(
        self,
        source: OutputSchema,
        target: UIContract,
        result: LinkCompatibilityResult
    ) -> str:
        """Genera prompt para que la IA cree un script bridge."""
        source_desc = ", ".join(f"{f.name}:{f.type.value}" for f in source.fields)
        target_desc = ", ".join(f"{i.name}:{i.type.value}" for i in target.inputs)

        issues = []
        if result.missing_fields:
            issues.append(f"Campos faltantes: {result.missing_fields}")
        for fr in result.field_results:
            if fr.status == CompatibilityStatus.INCOMPATIBLE:
                issues.append(f"{fr.source_field} → {fr.target_field}: {fr.message}")

        return f"""
Genera un script Python que transforme los datos de salida del átomo origen
para que sean compatibles con las entradas del átomo destino.

ORIGEN: {source_desc}
DESTINO: {target_desc}

PROBLEMAS DETECTADOS:
{chr(10).join(issues)}

El script debe:
1. Recibir un dict con los campos del origen
2. Retornar un dict con los campos esperados por el destino
3. Manejar errores de conversión gracefully
"""
