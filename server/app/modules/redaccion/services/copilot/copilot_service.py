"""Servicio Copilot: dos modos.

1. `answer(question, module)`: RAG sobre la documentación interna + síntesis LLM con citas.
2. `translate_nl_to_config(instruction, target_kind)`: traduce instrucción NL a configuración
   estructurada para los wizards (chart, ETL, script proposal).
"""

from __future__ import annotations

from typing import Any

from .docs_retriever import DocsRetriever
from .models import (
    CopilotAnswer,
    CopilotModule,
    CopilotTargetKind,
    CopilotTranslateResponse,
)


_ANSWER_SYSTEM_PROMPT = """Eres un asistente experto en la plataforma Gov Gen AI. \
Respondes preguntas del usuario apoyándote ÚNICAMENTE en los fragmentos de documentación \
que se te pasan como contexto. Si la respuesta no está en el contexto, di explícitamente \
"No tengo esa información en la documentación disponible." y no inventes.

Cita las secciones relevantes mencionando el título del documento entre corchetes."""


class CopilotService:
    def __init__(
        self,
        llm: Any,
        retriever: DocsRetriever,
        chart_factory: Any | None = None,
        etl_factory: Any | None = None,
        script_proposal: Any | None = None,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._chart_factory = chart_factory
        self._etl_factory = etl_factory
        self._script_proposal = script_proposal

    async def answer(
        self,
        question: str,
        module: CopilotModule | None = None,
        top_k: int = 4,
    ) -> CopilotAnswer:
        chunks = await self._retriever.retrieve(question, module=module, top_k=top_k)
        if not chunks:
            return CopilotAnswer(
                answer="No tengo esa información en la documentación disponible.",
                source_refs=[],
            )
        context_block = "\n\n---\n\n".join(
            f"[{chunk.source_path}]\n{chunk.text}" for chunk in chunks
        )
        messages = [
            {"role": "system", "content": _ANSWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"CONTEXTO:\n{context_block}\n\n"
                    f"PREGUNTA: {question}\n\n"
                    "Responde en el idioma de la pregunta."
                ),
            },
        ]
        response = await self._llm.ainvoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)
        return CopilotAnswer(
            answer=raw,
            source_refs=[c.to_source_ref() for c in chunks],
        )

    async def translate_nl_to_config(
        self,
        instruction: str,
        target_kind: CopilotTargetKind,
        sample_schema: dict[str, Any] | None = None,
    ) -> CopilotTranslateResponse:
        schema = sample_schema or {}
        if target_kind == "chart_config":
            if self._chart_factory is None:
                raise ValueError("ChartFactory no configurada en este CopilotService")
            result = await self._chart_factory.generate_script(
                nl_prompt=instruction, schema=schema
            )
            return CopilotTranslateResponse(
                kind="chart_config", payload=self._to_dict(result)
            )
        if target_kind == "etl_ops":
            if self._etl_factory is None:
                raise ValueError("ETLFactory no configurada en este CopilotService")
            result = await self._etl_factory.generate_operations_from_nl(
                nl_prompt=instruction, schema=schema
            )
            return CopilotTranslateResponse(
                kind="etl_ops", payload=self._to_dict(result)
            )
        if target_kind == "script_proposal":
            if self._script_proposal is None:
                raise ValueError("ScriptProposalService no configurado en este CopilotService")
            result = await self._script_proposal.propose(
                prompt_nl=instruction, sample_schema=schema or None
            )
            return CopilotTranslateResponse(
                kind="script_proposal", payload=self._to_dict(result)
            )
        raise ValueError(f"target_kind desconocido: {target_kind}")

    @staticmethod
    def _to_dict(obj: Any) -> dict[str, Any]:
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if isinstance(obj, dict):
            return obj
        return {"value": obj}
