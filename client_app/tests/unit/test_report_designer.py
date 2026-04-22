"""
Tests para el Report Designer.
TDD: Estos tests DEBEN FALLAR inicialmente.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

# We need to mock ReportSuggestionService import if it doesn't exist yet, 
# but for TDD we usually assume the interface. 
# However, if I run this before the file exists, it will ImportError.
# So I will create empty files or stubs first?
# The prompt says "Fase TDD: Red (Tests Primero)". 
# Typically in Python you expect the module to exist even if empty.

# I will define the test to import from the future location.
# If I run pytest and it errors with ImportError, that counts as "Red" (Test fails).

class TestReportSuggestionService:
    """Tests para sugerencias IA Zero-Knowledge."""

    @pytest.mark.asyncio
    async def test_suggest_visualizations_from_schema(self):
        """
        RED: IA debe sugerir visualizaciones basándose solo en el esquema.
        """
        from client_app.app.services.report_suggestion_service import ReportSuggestionService
        from client_app.app.core.state import state
        
        # Mocking the brain response
        mock_response = '''{
            "suggestions": [
                {"type": "chart", "chart_type": "line", "x_field": "date", "y_field": "sales", "title": "Sales Trend"},
                {"type": "chart", "chart_type": "bar", "x_field": "region", "y_field": "sales", "title": "Sales by Region"},
                {"type": "table", "title": "Detailed Data"}
            ]
        }'''
        
        # We need to mock state.brain BEFORE creating the service
        state.brain = MagicMock()
        state.brain.generate = AsyncMock(return_value=mock_response)
        
        input_schema = {
            "type": "object",
            "properties": {
                "date": {"type": "string", "format": "date"},
                "sales": {"type": "number"},
                "region": {"type": "string"},
                "product": {"type": "string"}
            }
        }

        service = ReportSuggestionService()
        suggestions = await service.suggest_visualizations(input_schema)

        # Debe sugerir gráfico de líneas para date + sales
        assert any(s["chart_type"] == "line" for s in suggestions)
        # Debe sugerir gráfico de barras para region + sales
        assert any(s["chart_type"] == "bar" for s in suggestions)
        # Debe sugerir tabla para datos detallados
        assert any(s["type"] == "table" for s in suggestions)

    @pytest.mark.asyncio
    async def test_generate_mock_data_from_schema(self):
        """
        RED: Debe generar datos mock que sigan el esquema.
        """
        from client_app.app.services.report_suggestion_service import generate_mock_data
        
        input_schema = {
            "type": "object",
            "properties": {
                "sales_data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "month": {"type": "string"},
                            "total": {"type": "number"}
                        }
                    }
                },
                "report_title": {"type": "string"}
            }
        }

        mock_data = await generate_mock_data(input_schema, num_rows=5)

        assert "sales_data" in mock_data
        assert len(mock_data["sales_data"]) == 5
        assert "report_title" in mock_data
        assert isinstance(mock_data["sales_data"][0]["total"], (int, float))

    @pytest.mark.asyncio
    async def test_zero_knowledge_no_real_data(self):
        """
        RED: El servicio NUNCA debe recibir datos reales.
        """
        from client_app.app.services.report_suggestion_service import ReportSuggestionService
        service = ReportSuggestionService()

        # Verificar que el método solo acepta schemas, no datos
        with pytest.raises(TypeError):
            await service.suggest_visualizations(
                schema={"type": "object"},
                real_data={"secret": "value"}  # Esto debe fallar si la firma lo impide o si validamos
            )


class TestReportBlockEditor:
    """Tests para el editor de bloques."""

    def test_block_reorder(self):
        """
        RED: Los bloques deben poder reordenarse.
        """
        from client_app.app.ui.components.report_block_editor import ReportBlockEditor

        blocks = [
            {"id": "b1", "type": "text"},
            {"id": "b2", "type": "chart"},
            {"id": "b3", "type": "table"}
        ]

        editor = ReportBlockEditor(blocks)
        editor.move_block("b3", 0)  # Mover tabla al inicio (index based on id?) 
        # The prompt implementation of move_block uses (block_id, new_index).
        
        # Need to re-fetch blocks or check the list
        assert editor.blocks[0]["id"] == "b3"
        assert editor.blocks[1]["id"] == "b1"

    def test_chart_block_column_mapping(self):
        """
        RED: Bloques de gráfico deben permitir mapear columnas del esquema.
        """
        from client_app.app.ui.components.report_block_editor import ChartBlockConfig

        available_columns = ["date", "sales", "region", "product"]

        config = ChartBlockConfig(
            chart_type="bar",
            x_field="region",
            y_field="sales",
            available_columns=available_columns
        )

        assert config.x_field in available_columns
        assert config.y_field in available_columns
        assert config.validate() is True
