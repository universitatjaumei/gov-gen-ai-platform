"""VER.1 — el adaptador entre el modelo y el nodo de redacción del grafo.

`AIAssistDraftNode` llama a `llm.generate(prompt=<ai_prompt_template_id>, context=...)`. Ese
`prompt` **no es un prompt**: es el identificador de una plantilla de prompt, y en el módulo
de redacción no había nada que lo resolviera —`hub_prompt_templates` cuelga de un chatbot y
es otra cosa—. Mandarlo tal cual al modelo significa pedirle que redacte un informe con la
instrucción «generic_report_v1», que es lo mismo que no cablear nada.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from server.app.modules.redaccion.services.redactor_de_bloques import (
    CATALOGO_DE_PROMPTS,
    RedactorDeBloques,
    instruccion_para,
)


class TestLaInstruccion:

    def test_should_resolve_a_known_prompt_id_to_a_real_instruction(self):
        instruccion = instruccion_para("generic_report_v1")

        assert instruccion == CATALOGO_DE_PROMPTS["generic_report_v1"]
        assert len(instruccion) > 80, "una instruccion de una linea no redacta un informe"

    def test_should_never_send_the_bare_identifier_as_the_instruction(self):
        """Es lo que hacía antes de existir este adaptador."""
        instruccion = instruccion_para("un_id_que_no_existe")

        assert instruccion.strip() != "un_id_que_no_existe"

    def test_should_keep_the_unknown_identifier_visible_in_the_instruction(self):
        """Sin catálogo no hay instrucción específica, pero el id tiene que viajar: es lo
        único que permite saber después qué plantilla pidió esa redacción."""
        instruccion = instruccion_para("informe_de_gerencia_v3")

        assert "informe_de_gerencia_v3" in instruccion


class TestElAdaptador:

    @pytest.mark.asyncio
    async def test_should_return_the_text_the_model_wrote(self):
        modelo = MagicMock()
        modelo.ainvoke = AsyncMock(return_value=MagicMock(content="Texto redactado."))

        salida = await RedactorDeBloques(modelo, "gemini-de-prueba").generate(
            prompt="generic_report_v1", context="[b_datos]\ntotal: 100",
        )

        assert salida == "Texto redactado."

    @pytest.mark.asyncio
    async def test_should_survive_a_model_that_answers_in_blocks(self):
        """Gemini devuelve `content` como lista de bloques en cuanto hay más de una parte.
        Guardar la lista tal cual mete un `[{'type': 'text'...}]` en el informe."""
        modelo = MagicMock()
        modelo.ainvoke = AsyncMock(return_value=MagicMock(content=[
            {"type": "text", "text": "Primera parte. "},
            {"type": "text", "text": "Segunda parte."},
        ]))

        salida = await RedactorDeBloques(modelo, "gemini-de-prueba").generate(
            prompt="generic_report_v1", context="",
        )

        assert salida == "Primera parte. Segunda parte."

    @pytest.mark.asyncio
    async def test_should_send_the_context_to_the_model(self):
        """El contexto son los bloques ya extraídos y validados. Si no llega, el modelo
        redacta de memoria, que es exactamente lo que el módulo viene a evitar."""
        modelo = MagicMock()
        modelo.ainvoke = AsyncMock(return_value=MagicMock(content="ok"))

        await RedactorDeBloques(modelo, "m").generate(
            prompt="generic_report_v1", context="[b_datos]\nimporte: 30 euros",
        )

        enviado = str(modelo.ainvoke.call_args)
        assert "importe: 30 euros" in enviado

    def test_should_expose_the_model_name_the_node_records(self):
        """`AIAssistDraftNode` guarda `model_used` en el bloque: es lo que permite saber
        con qué modelo se redactó un informe meses después."""
        redactor = RedactorDeBloques(MagicMock(), "gemini-2.5-flash")

        assert redactor.model_name == "gemini-2.5-flash"
