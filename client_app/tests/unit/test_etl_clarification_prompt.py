# client_app/tests/unit/test_etl_clarification_prompt.py

import pytest
from client_app.app.prompts.clarification_prompts import (
    CLARIFICATION_ANALYSIS_ETL,
    get_clarification_prompt,
    format_prompt_for_module
)

class TestETLClarificationPrompt:
    """Tests para el prompt de clarificación de ETL."""

    def test_etl_prompt_exists(self):
        """Verifica que el prompt ETL está definido."""
        assert CLARIFICATION_ANALYSIS_ETL is not None
        assert len(CLARIFICATION_ANALYSIS_ETL) > 100

    def test_etl_prompt_contains_required_sections(self):
        """Verifica secciones necesarias."""
        required_sections = [
            "CONTEXTO",
            "ENTRADA",
            "TAREA",
            "REGLAS"
        ]

        # Use case-insensitive check or partial match logic as needed, 
        # usually prompts have headings like '## CONTEXTO'
        for section in required_sections:
            assert section in CLARIFICATION_ANALYSIS_ETL

    def test_etl_prompt_covers_common_ambiguities(self):
        """Verifica que cubre ambigüedades comunes de ETL."""
        common_topics = [
            "formato",     # Formatos de fecha, números
            "nulos",       # Manejo de valores nulos
            "duplicados",  # Qué hacer con duplicados
            # "columnas" might be context specific, checked via examples usually
        ]

        prompt_lower = CLARIFICATION_ANALYSIS_ETL.lower()
        for topic in common_topics:
            assert topic in prompt_lower, f"Topic '{topic}' no encontrado"

    def test_get_clarification_prompt_etl(self):
        """Verifica que get_clarification_prompt retorna el prompt ETL."""
        prompt = get_clarification_prompt("etl")
        assert prompt == CLARIFICATION_ANALYSIS_ETL

    def test_etl_prompt_examples_include_data_scenarios(self):
        """Verifica ejemplos específicos de ETL."""
        etl_scenarios = [
            "fecha",
            "excel",  # Usually mentions Excel sheets
            # "csv" might be implicit
        ]

        prompt_lower = CLARIFICATION_ANALYSIS_ETL.lower()
        matches = sum(1 for s in etl_scenarios if s in prompt_lower)
        assert matches >= 1, "Debe incluir escenarios de ETL"
