"""VER.2 — proponer una plantilla con el modelo, en vez de devolver 503.

`LLMSpecService` estaba escrito y probado desde 9R; lo que devolvía 503 era la dependencia
que lo construye (`get_llm_spec_service`, un stub con «connect to model_factory»). Es la
puerta de entrada natural al módulo: describir el informe que quieres y que la plantilla se
proponga sola, en vez de montarla campo a campo en el constructor.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from server.app.modules.redaccion.services.llm_spec_service import LLMSpecService


class TestLaDependencia:

    @pytest.mark.asyncio
    async def test_should_build_the_service_from_the_model_cascade(self):
        """Deja de ser un stub: resuelve el modelo por `model_factory`, como todo lo demás."""
        import server.app.routers.redaccion.llm_drafts_router as router_modulo

        modelo = MagicMock()
        modelo.model_name = "gemini-2.5-flash"

        async def _modelo_falso(_tier, _provider):
            return modelo

        original = router_modulo.get_model_for_tier
        router_modulo.get_model_for_tier = _modelo_falso
        try:
            servicio = await router_modulo.get_llm_spec_service(session=MagicMock())
        finally:
            router_modulo.get_model_for_tier = original

        assert isinstance(servicio, LLMSpecService)

    @pytest.mark.asyncio
    async def test_should_still_say_503_and_why_when_there_is_no_model(self):
        """Sin modelo configurado el 503 tiene que seguir, y decir qué falta: es la
        diferencia entre «esto no está montado» y «esto está roto»."""
        from fastapi import HTTPException

        import server.app.routers.redaccion.llm_drafts_router as router_modulo

        async def _revienta(_tier, _provider):
            raise ValueError("No hay configuracion LLM por defecto para tier 1")

        original = router_modulo.get_model_for_tier
        router_modulo.get_model_for_tier = _revienta
        try:
            with pytest.raises(HTTPException) as fallo:
                await router_modulo.get_llm_spec_service(session=MagicMock())
        finally:
            router_modulo.get_model_for_tier = original

        assert fallo.value.status_code == 503
        assert "tier 1" in str(fallo.value.detail)


class TestElCaminoDeLaPropuesta:

    @pytest.mark.asyncio
    async def test_should_propose_a_template_from_a_description(self):
        """El servicio pide JSON al modelo y lo valida contra el contrato de plantilla."""
        modelo = MagicMock()
        modelo.ainvoke = AsyncMock(return_value=MagicMock(content="""```json
{
  "proposed_profile": "GENERIC_REPORT",
  "proposed_sections": [{"id": "s1", "title": "Introduccion", "order": 1, "block_ids": []}],
  "proposed_blocks": [
    {"id": "b1", "kind": "STATIC_TEXT", "title": "Encabezado", "order": 1,
     "text": "Informe de ejecucion presupuestaria"}
  ],
  "proposed_inputs": {"required_slots": [], "optional_slots": []},
  "rationale": "Un informe sencillo"
}
```"""))

        borrador = await LLMSpecService(modelo, "gemini-2.5-flash").propose_template(
            prompt_nl="Un informe de ejecución presupuestaria trimestral",
            owner_kind="admin",
        )

        assert borrador.proposed_profile == "GENERIC_REPORT"
        assert [s.title for s in borrador.proposed_sections] == ["Introduccion"]
        assert borrador.model_used == "gemini-2.5-flash"
