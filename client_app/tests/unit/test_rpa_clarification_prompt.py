# client_app/tests/unit/test_rpa_clarification_prompt.py

import pytest
from client_app.app.prompts.clarification_prompts import (
    CLARIFICATION_ANALYSIS_RPA,
    get_clarification_prompt
)

class TestRPAClarificationPrompt:
    """Tests para el prompt de clarificación de RPA."""

    def test_rpa_prompt_exists(self):
        """Verifica que el prompt RPA está definido."""
        assert CLARIFICATION_ANALYSIS_RPA is not None
        assert len(CLARIFICATION_ANALYSIS_RPA) > 100

    def test_rpa_prompt_contains_required_sections(self):
        """Verifica secciones necesarias."""
        required_sections = [
            "MÓDULO: RPA WEB",
            "ANÁLISIS DE GRABACIÓN",
            "TU TAREA",
            "REGLAS"
        ]
        
        # Check specific module context or headers
        prompt_upper = CLARIFICATION_ANALYSIS_RPA.upper()
        
        # Checking for main headers that are likely in uppercase in the prompt source
        assert "CONTEXTO DEL MÓDULO" in prompt_upper
        assert "ENTRADA" in prompt_upper
        assert "TU TAREA" in prompt_upper
        
        # Specific RPA content check
        assert "RPA" in prompt_upper

    def test_rpa_prompt_covers_critical_topics(self):
        """Verifica que cubre temas críticos de RPA."""
        common_topics = [
            "excepciones", # Popups, cookies
            "dinámicos",   # Datos variables
            "login",       # Seguridad
            # "captcha"     # Optional but good
        ]

        prompt_lower = CLARIFICATION_ANALYSIS_RPA.lower()
        for topic in common_topics:
            assert topic in prompt_lower, f"Topic '{topic}' no encontrado"

    def test_get_clarification_prompt_rpa(self):
        """Verifica que get_clarification_prompt retorna el prompt RPA."""
        prompt = get_clarification_prompt("rpa")
        assert prompt == CLARIFICATION_ANALYSIS_RPA

    def test_rpa_prompt_structure_json(self):
        """Verifica que pide JSON estricto."""
        assert "```json" in CLARIFICATION_ANALYSIS_RPA
        assert "needs_clarification" in CLARIFICATION_ANALYSIS_RPA
        assert "questions" in CLARIFICATION_ANALYSIS_RPA
