"""
Flow Diagram Generator - Genera diagramas Mermaid para visualizar flujos.

Soporta validación visual con clases de estilo para errores y warnings.
Refactorizado como parte de la Fase 4 del Plan de Taxonomía.
"""
from typing import Dict, List, Optional, Any
from automatia_shared.dtos import FlowSpec


class FlowDiagramGenerator:
    """Generador de diagramas Mermaid para flujos de trabajo."""

    def generate(
        self,
        flow: FlowSpec,
        validation_errors: Optional[Dict[int, List[Any]]] = None,
        highlight_step: Optional[int] = None
    ) -> str:
        """
        Genera código Mermaid para el flujo.

        Args:
            flow: FlowSpec con los pasos del flujo
            validation_errors: Dict con índice de paso -> lista de errores
            highlight_step: Índice del paso a resaltar (paso actual en edición)

        Returns:
            Código Mermaid del diagrama
        """
        if not flow.steps:
            return """graph LR
    Start([Inicio]) --> End([Fin])
    style Start fill:#e0f2fe,stroke:#0284c7
    style End fill:#dcfce7,stroke:#16a34a"""

        lines = ["graph LR"]

        # Definir clases de estilo
        lines.append("    %% Estilos de validación")
        lines.append("    classDef errorNode fill:#fee2e2,stroke:#ef4444,stroke-width:3px")
        lines.append("    classDef warningNode fill:#fff7ed,stroke:#f97316,stroke-width:2px")
        lines.append("    classDef activeNode fill:#dbeafe,stroke:#2563eb,stroke-width:3px")
        lines.append("    classDef defaultNode fill:#f8fafc,stroke:#94a3b8,stroke-width:1px")
        lines.append("")

        # Nodo de inicio
        lines.append("    Start([Inicio])")
        lines.append("    style Start fill:#e0f2fe,stroke:#0284c7")

        # Generar nodos de pasos
        error_nodes = []
        warning_nodes = []
        active_nodes = []

        for idx, step in enumerate(flow.steps):
            step_id = f"S{idx + 1}"
            step_type = (step.type.value if hasattr(step.type, 'value') else str(step.type)).upper()

            # Escapar comillas dobles y caracteres especiales
            safe_name = step.name.replace('"', "'").replace('<', '&lt;').replace('>', '&gt;')
            label = f"{safe_name}<br/><small>{step_type}</small>"

            lines.append(f'    {step_id}["{label}"]')

            # Clasificar nodo según errores
            if validation_errors and idx in validation_errors:
                errors = validation_errors[idx]
                has_error = any(
                    getattr(e, 'severity', 'error') == 'error'
                    for e in errors
                )
                has_warning = any(
                    getattr(e, 'severity', 'warning') == 'warning'
                    for e in errors
                )

                if has_error:
                    error_nodes.append(step_id)
                elif has_warning:
                    warning_nodes.append(step_id)

            # Paso activo (en edición)
            if highlight_step is not None and idx == highlight_step:
                active_nodes.append(step_id)

        # Conexiones
        lines.append("")
        lines.append("    %% Conexiones")
        lines.append("    Start --> S1")
        for idx in range(len(flow.steps) - 1):
            lines.append(f"    S{idx + 1} --> S{idx + 2}")

        # Nodo final
        lines.append(f"    S{len(flow.steps)} --> End([Fin])")
        lines.append("    style End fill:#dcfce7,stroke:#16a34a")

        # Aplicar clases de estilo
        if error_nodes:
            lines.append("")
            lines.append("    %% Nodos con errores")
            lines.append(f"    class {','.join(error_nodes)} errorNode")

        if warning_nodes:
            lines.append("")
            lines.append("    %% Nodos con advertencias")
            lines.append(f"    class {','.join(warning_nodes)} warningNode")

        if active_nodes:
            lines.append("")
            lines.append("    %% Nodo activo")
            lines.append(f"    class {','.join(active_nodes)} activeNode")

        return "\n".join(lines)

    def generate_simple(self, flow: FlowSpec) -> str:
        """
        Genera un diagrama simple sin validación (para vistas rápidas).

        Args:
            flow: FlowSpec con los pasos del flujo

        Returns:
            Código Mermaid básico
        """
        return self.generate(flow, validation_errors=None, highlight_step=None)


# Singleton
flow_diagram_generator = FlowDiagramGenerator()
