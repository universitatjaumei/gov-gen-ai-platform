"""Tests de las plantillas de system prompt -- TDD."""
import uuid

from server.app.modules.agents_hub.services.retrieval.types import Source


def _make_source(title: str, url: str) -> Source:
    return Source(
        document_id=uuid.uuid4(),
        title=title,
        url=url,
        excerpt="Contenido de ejemplo del documento.",
        score=1.0,
    )


class TestBuildSystemPrompt:

    def test_build_system_prompt_includes_citation_rules(self):
        from server.app.modules.agents_hub.agent.prompts import build_system_prompt
        result = build_system_prompt(
            base_prompt="Eres un asistente.",
            language="es",
            sources_block="",
            mode="vector",
        )
        assert "REGLAS DE CITA" in result

    def test_build_system_prompt_includes_language_directive(self):
        from server.app.modules.agents_hub.agent.prompts import build_system_prompt
        result = build_system_prompt(
            base_prompt="Eres un asistente.",
            language="ca",
            sources_block="",
            mode="vector",
        )
        assert "ca" in result

    def test_build_system_prompt_for_agentic_mentions_tools(self):
        from server.app.modules.agents_hub.agent.prompts import build_system_prompt
        result = build_system_prompt(
            base_prompt="Eres un asistente.",
            language="es",
            sources_block="",
            mode="agentic",
        )
        assert "list_documents" in result
        assert "read_document" in result

    def test_build_system_prompt_for_long_context_includes_sources_block(self):
        from server.app.modules.agents_hub.agent.prompts import build_system_prompt
        result = build_system_prompt(
            base_prompt="Eres un asistente.",
            language="es",
            sources_block="## Norma A\n_URL: https://ej.com_\n\nTexto.",
            mode="long_context",
        )
        assert "DOCUMENTOS DISPONIBLES" in result
        assert "Norma A" in result

    def test_build_system_prompt_does_not_include_docs_for_empty_sources_block(self):
        from server.app.modules.agents_hub.agent.prompts import build_system_prompt
        result = build_system_prompt(
            base_prompt="Eres un asistente.",
            language="es",
            sources_block="",
            mode="vector",
        )
        assert "DOCUMENTOS DISPONIBLES" not in result


class TestFormatSourcesBlock:

    def test_format_sources_block_renders_each_source_with_title_and_url(self):
        from server.app.modules.agents_hub.agent.prompts import format_sources_block
        sources = [
            _make_source("Norma A", "https://ej.com/a.pdf"),
            _make_source("Norma B", "https://ej.com/b.pdf"),
        ]
        result = format_sources_block(sources)
        assert "Norma A" in result
        assert "https://ej.com/a.pdf" in result
        assert "Norma B" in result

    def test_format_sources_block_returns_empty_for_no_sources(self):
        from server.app.modules.agents_hub.agent.prompts import format_sources_block
        assert format_sources_block([]) == ""
