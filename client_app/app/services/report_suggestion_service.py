"""
Servicio de sugerencias para informes con Zero-Knowledge.
La IA SOLO recibe esquemas de datos, NUNCA datos reales.
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from client_app.app.core.state import state


@dataclass
class VisualizationSuggestion:
    """Sugerencia de visualización."""
    type: str  # chart | table | text
    chart_type: Optional[str] = None  # bar | line | pie | scatter
    title: str = ""
    description: str = ""
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    config: Dict[str, Any] = None


class ReportSuggestionService:
    """
    Servicio de sugerencias Zero-Knowledge para diseño de informes.
    CRÍTICO: Este servicio NUNCA recibe datos reales, solo esquemas.
    """

    def __init__(self):
        self.brain = state.brain

    async def suggest_visualizations(
        self,
        schema: Dict[str, Any],
        context: Optional[str] = None,
        real_data: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Sugerir visualizaciones basándose SOLO en el esquema.

        Args:
            schema: JSON Schema de los datos esperados
            context: Contexto textual opcional (ej: "informe de ventas")
            real_data: NUNCA USAR. Solo para detectar violaciones de privacidad.

        Returns:
            Lista de sugerencias de bloques

        Raises:
            TypeError: Si se intenta pasar datos reales
        """
        # Guardar privacidad: si real_data no es None, ERROR.
        if real_data is not None:
             raise TypeError("ReportSuggestionService must NOT receive real data, only schema.")

        # Extraer campos y tipos del esquema
        fields = self._extract_fields(schema)

        # Construir prompt para IA (Zero-Knowledge)
        prompt = self._build_suggestion_prompt(fields, context)

        # Llamar a IA
        response = await self.brain.generate(
            prompt=prompt,
            system_prompt=self._get_system_prompt(),
            response_format="json"
        )

        return self._parse_suggestions(response)

    def _extract_fields(self, schema: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extraer campos y sus tipos del JSON Schema."""
        fields = []

        properties = schema.get("properties", {})
        for name, spec in properties.items():
            field_type = spec.get("type", "string")
            field_format = spec.get("format", "")

            # Para arrays, extraer estructura interna
            if field_type == "array" and "items" in spec:
                items = spec["items"]
                if items.get("type") == "object":
                    nested = items.get("properties", {})
                    for nested_name, nested_spec in nested.items():
                        fields.append({
                            "name": f"{name}.{nested_name}",
                            "type": nested_spec.get("type", "string"),
                            "format": nested_spec.get("format", ""),
                            "parent": name
                        })

            fields.append({
                "name": name,
                "type": field_type,
                "format": field_format
            })

        return fields

    def _build_suggestion_prompt(
        self,
        fields: List[Dict[str, str]],
        context: Optional[str]
    ) -> str:
        """Construir prompt para sugerencias."""
        fields_desc = "\n".join([
            f"- {f['name']}: {f['type']}" + (f" (formato: {f['format']})" if f.get('format') else "")
            for f in fields
        ])

        return f"""
Analiza el siguiente esquema de datos y sugiere visualizaciones apropiadas.

CAMPOS DISPONIBLES:
{fields_desc}

CONTEXTO: {context or 'Informe general'}

Sugiere entre 2-4 visualizaciones (gráficos o tablas) que aprovechen estos campos.
Para cada sugerencia indica:
- type: "chart" o "table"
- chart_type: (si es chart) "bar", "line", "pie", "scatter", "area"
- title: título descriptivo
- description: explicación de por qué esta visualización es útil
- x_field: campo para eje X (si aplica)
- y_field: campo para eje Y (si aplica)

Responde en JSON con formato: {{"suggestions": [...]}}
"""

    def _get_system_prompt(self) -> str:
        """System prompt para sugerencias."""
        return """
Eres un experto en visualización de datos y diseño de informes.
Tu trabajo es analizar ESQUEMAS de datos (nunca datos reales) y sugerir
las mejores visualizaciones para presentar esa información.

Reglas:
1. Sugiere gráficos de línea para series temporales (campos date/datetime)
2. Sugiere gráficos de barras para comparaciones categóricas
3. Sugiere gráficos de pie para proporciones (máximo 5-7 categorías)
4. Sugiere tablas para datos detallados o cuando hay muchos campos
5. Prioriza la claridad sobre la complejidad
"""

    def _parse_suggestions(self, response: str) -> List[Dict[str, Any]]:
        """Parsear respuesta de IA."""
        try:
            # Handle possible string/dict return depending on brain implementation
            if isinstance(response, dict):
                 data = response
            else:
                 data = json.loads(response)
            
            return data.get("suggestions", [])
        except (json.JSONDecodeError, AttributeError):
            return []


async def suggest_visualizations(
    schema: Dict[str, Any],
    context: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Función de conveniencia para sugerencias."""
    service = ReportSuggestionService()
    return await service.suggest_visualizations(schema, context)


async def generate_mock_data(
    schema: Dict[str, Any],
    num_rows: int = 5
) -> Dict[str, Any]:
    """
    Generar datos mock que sigan el esquema.
    Útil para vista previa sin datos reales.
    """
    import random
    from datetime import datetime, timedelta

    mock = {}
    properties = schema.get("properties", {})

    for name, spec in properties.items():
        field_type = spec.get("type", "string")
        field_format = spec.get("format", "")

        if field_type == "string":
            if field_format == "date":
                mock[name] = (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
            else:
                mock[name] = f"Ejemplo {name}"

        elif field_type == "number":
            mock[name] = round(random.uniform(100, 10000), 2)

        elif field_type == "integer":
            mock[name] = random.randint(1, 100)

        elif field_type == "boolean":
            mock[name] = random.choice([True, False])

        elif field_type == "array":
            items_spec = spec.get("items", {})
            if items_spec.get("type") == "object":
                mock[name] = [
                    await generate_mock_data(items_spec, num_rows=1) # recursive single row inside array
                    for _ in range(num_rows)
                ]
            else:
                mock[name] = [f"Item {i}" for i in range(num_rows)]

    return mock
