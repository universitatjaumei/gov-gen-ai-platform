# client_app/tests/unit/test_extraction_clarification_prompt.py

import pytest
from client_app.app.prompts.clarification_prompts import (
    CLARIFICATION_ANALYSIS_EXTRACTION,
    get_clarification_prompt
)

class TestExtractionClarificationPrompt:
    """Tests para el prompt de clarificación de Extracción."""

    def test_extraction_prompt_exists(self):
        """Verifica que el prompt Extracción está definido."""
        assert CLARIFICATION_ANALYSIS_EXTRACTION is not None
        assert len(CLARIFICATION_ANALYSIS_EXTRACTION) > 100

    def test_extraction_prompt_contains_required_sections(self):
        """Verifica secciones necesarias."""
        # Use simple string checks as the exact header case/format might vary slightly
        # based on previous prompts, but we expect standard headers.
        prompt = CLARIFICATION_ANALYSIS_EXTRACTION
        assert "CONTEXTO" in prompt
        assert "TAREA" in prompt or "TU TAREA" in prompt
        assert "REGLAS" in prompt
        assert "EXTRACCIÓN INTELIGENTE" in prompt.upper() or "EXTRACCIÓN" in prompt.upper()

    def test_extraction_prompt_covers_ambiguities(self):
        """Verifica que cubre ambigüedades comunes de extracción."""
        common_topics = [
            "ambigüedad",  # Ambiguity
            "formato",     # Formats
            "tablas",      # Tables selection
            # "selección"
        ]

        prompt_lower = CLARIFICATION_ANALYSIS_EXTRACTION.lower()
        for topic in common_topics:
            assert topic in prompt_lower, f"Topic '{topic}' no encontrado"

    def test_get_clarification_prompt_extraction(self):
        """Verifica que get_clarification_prompt retorna el prompt de extracción."""
        prompt = get_clarification_prompt("extraction")
        assert prompt == CLARIFICATION_ANALYSIS_EXTRACTION
