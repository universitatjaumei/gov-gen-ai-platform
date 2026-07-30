"""AgenticLoop — loop tool-calling del modo MD_AGENT_SELECTOR.

Portado en RAG.2 desde `agent/graph.py:_run_agentic_loop`, que desapareció con el grafo
antiguo. Aquí es un componente independiente del grafo: el CoreGraph lo usa en
`generate_answer` cuando `cfg.retrieval_mode == "MD_AGENT_SELECTOR"`, y se puede probar
sin compilar ningún grafo.

Dos cambios respecto al original, ambos consecuencia de la unificación de contratos:

- acumula **EvidenceItem**, no `Source` — es el único contrato de evidencia del proyecto;
- lee los documentos a través de un `DocumentReader` inyectado en vez de importar los
  tools dentro del bucle, para que el modo sea testeable sin BD.

Deploy: edge
"""
from __future__ import annotations

import uuid
from typing import Any, Protocol

from langchain_core.messages import ToolMessage

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
)

MAX_ITERACIONES = 10
EXCERPT_MAX = 500


class DocumentReader(Protocol):
    """Acceso a documentos para los tools del modo selector."""

    async def list_index(self, chatbot_id: str, language: str | None) -> str:
        """Índice legible por el LLM (títulos + ids)."""
        ...

    async def read(self, document_id: uuid.UUID) -> dict | None:
        """Documento completo: title, url, markdown_content."""
        ...


class AgenticLoop:
    """Ejecuta el ciclo LLM ↔ tools hasta que el modelo responde sin pedir tools.

    Devuelve `(evidencias_leídas, texto_final)`. Solo entran como evidencia los
    documentos que el modelo **leyó de verdad**, no el índice que se le ofreció: es lo que
    hace que las citas del modo selector sean verificables.
    """

    def __init__(
        self,
        reader: DocumentReader,
        tools: list[Any],
        max_iterations: int = MAX_ITERACIONES,
    ) -> None:
        self._reader = reader
        self._tools = tools
        self._max_iterations = max_iterations

    async def run(
        self,
        llm: Any,
        system: str,
        query: str,
        chatbot_id: str = "",
        language: str | None = None,
        history: list[dict] | None = None,
    ) -> tuple[list[EvidenceItem], str]:
        llm_con_tools = llm.bind_tools(self._tools)
        mensajes: list[Any] = [{"role": "system", "content": system}]
        mensajes.extend(history or [])
        mensajes.append({"role": "user", "content": query})

        leidas: list[EvidenceItem] = []

        for _ in range(self._max_iterations):
            respuesta = await llm_con_tools.ainvoke(mensajes)
            tool_calls = getattr(respuesta, "tool_calls", None)
            if not tool_calls:
                return leidas, respuesta.content

            mensajes.append({"role": "assistant", "content": respuesta.content or ""})
            for llamada in tool_calls:
                salida = await self._ejecutar(llamada, chatbot_id, language, leidas)
                mensajes.append(ToolMessage(content=salida, tool_call_id=llamada["id"]))

        return leidas, ""

    async def _ejecutar(
        self,
        llamada: dict,
        chatbot_id: str,
        language: str | None,
        leidas: list[EvidenceItem],
    ) -> str:
        nombre = llamada["name"]
        args = llamada.get("args", {})

        if nombre == "list_documents":
            return await self._reader.list_index(chatbot_id, language)

        if nombre == "read_document":
            doc_id = str(args.get("document_id", ""))
            documento = await self._reader.read(uuid.UUID(doc_id)) if doc_id else None
            if documento is None:
                return f"Documento {doc_id} no encontrado."
            leidas.append(
                EvidenceItem(
                    source_id=doc_id,
                    content=documento["markdown_content"][:EXCERPT_MAX],
                    source_url=documento["url"],
                    title=documento["title"],
                    language=documento.get("language"),
                    score=1.0,
                )
            )
            return documento["markdown_content"]

        return f"Tool {nombre} no reconocida."
