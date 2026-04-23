"""Tests para el detector de idioma."""
import pytest


class TestLanguageDetector:

    def test_detects_spanish(self) -> None:
        from server.app.modules.agents_hub.agent.language_detector import detect_language

        text = "Hola, ¿cómo estás? Necesito ayuda con un problema."
        result = detect_language(text)
        assert result == "es"

    def test_detects_english(self) -> None:
        from server.app.modules.agents_hub.agent.language_detector import detect_language

        text = "Hello, how are you? I need help with a problem."
        result = detect_language(text)
        assert result == "en"

    def test_defaults_to_spanish_on_short_text(self) -> None:
        from server.app.modules.agents_hub.agent.language_detector import detect_language

        text = "Hola"
        result = detect_language(text)
        assert result == "es"  # Default
