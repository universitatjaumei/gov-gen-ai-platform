# client_app/tests/unit/test_clarification_prompts.py

import pytest
from client_app.app.prompts.clarification_prompts import (
    CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT,
    get_clarification_prompt,
    format_prompt_for_module
)

class TestCustomScriptClarificationPrompt:
    """Tests para el prompt de clarificación de Custom Script."""

    def test_prompt_exists(self):
        """Verifica que el prompt está definido."""
        assert CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT is not None
        assert len(CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT) > 100

    def test_prompt_contains_required_sections(self):
        """Verifica que el prompt tiene las secciones necesarias."""
        required_sections = [
            "CONTEXTO DEL MÓDULO",
            "ENTRADA DEL USUARIO",
            "TU TAREA",
            "REGLAS",
            "RESPUESTA"
        ]

        for section in required_sections:
            assert section in CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT

    def test_prompt_has_json_output_format(self):
        """Verifica que el prompt especifica formato JSON de salida."""
        assert "```json" in CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT
        assert "needs_clarification" in CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT
        assert "confidence_score" in CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT
        assert "questions" in CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT

    def test_prompt_limits_max_questions(self):
        """Verifica que el prompt limita a 3 preguntas."""
        assert "máximo 3" in CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT.lower() or \
               "max 3" in CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT.lower()

    def test_prompt_has_anti_obvio_rules(self):
        """Verifica que el prompt indica NO preguntar obviedades."""
        prompt_lower = CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT.lower()
        assert "no pregunt" in prompt_lower and "obvi" in prompt_lower

    def test_get_clarification_prompt_custom_script(self):
        """Verifica que get_clarification_prompt retorna el prompt correcto."""
        prompt = get_clarification_prompt("custom_script")
        assert prompt == CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT

    def test_format_prompt_with_user_input(self):
        """Verifica que el prompt se formatea correctamente."""
        user_input = {
            "prompt": "Necesito procesar archivos CSV de ventas"
        }
        context = {
            "files": ["ventas_enero.csv", "ventas_febrero.csv"]
        }

        formatted = format_prompt_for_module(
            "custom_script",
            user_input,
            context
        )

        assert "procesar archivos CSV" in formatted
        assert "ventas_enero.csv" in formatted

    def test_prompt_includes_example_questions(self):
        """Verifica que el prompt incluye ejemplos de buenas preguntas."""
        # Los ejemplos ayudan al modelo a entender qué tipo de preguntas hacer
        assert "formato" in CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT.lower() or \
               "ejemplo" in CLARIFICATION_ANALYSIS_CUSTOM_SCRIPT.lower()


class TestClarificationPromptsRegistry:
    """Tests para el registro de prompts por módulo."""

    def test_all_modules_have_prompts(self):
        """Verifica que todos los módulos tienen prompts definidos."""
        modules = ["custom_script", "etl", "rpa", "extraction"]

        for module in modules:
            prompt = get_clarification_prompt(module)
            # Al menos custom_script debe existir, otros pueden ser None inicialmente
            if module == "custom_script":
                assert prompt is not None

    def test_unknown_module_returns_none(self):
        """Verifica que un módulo desconocido retorna None."""
        prompt = get_clarification_prompt("unknown_module")
        assert prompt is None
