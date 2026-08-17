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

from server.app.core.llm_text import texto_de

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
)

MAX_ITERACIONES = 10
EXCERPT_MAX = 500

#: Por encima de esto, `read_document` no vuelca el documento en la conversación.
#:
#: Medido sobre el corpus del piloto: la normativa **propia** más larga son 51.032 tokens,
#: así que con este techo se sigue leyendo entera —que es lo que permite citar el artículo
#: exacto—. Las **externas** son otra cosa: las 22 del corpus de Gerencia suman 1.745.337
#: tokens y la Ley de Contratos sola son 279.425. Esas se consultan por fragmentos.
LIMITE_LECTURA_TOKENS = 60_000

#: Cuánto del principio se conserva cuando hay que truncar: lo justo para que el modelo vea
#: de qué norma se trata y cómo está organizada antes de ir a buscar dentro.
CABECERA_AL_TRUNCAR = 4_000

_AVISO_TRUNCADO = (
    "\n\n[...]\n\n[El documento son ~{tokens} tokens y no cabe entero en el contexto. "
    "Arriba está solo el principio. Para el contenido concreto usa "
    "`search_knowledge(query=...)`, que trae los fragmentos que respondan a la pregunta.]"
)


class FragmentSearcher(Protocol):
    """Búsqueda por fragmentos para el tool `search_knowledge`."""

    async def search(
        self, query: str, chatbot_id: str, language: str | None = None
    ) -> list[EvidenceItem]: ...


class DocumentReader(Protocol):
    """Acceso a documentos para los tools del modo selector."""

    async def list_index(
        self,
        chatbot_id: str,
        language: str | None,
        submateries: list[str] | None = None,
    ) -> str:
        """Índice legible por el LLM (fichas: título, id, rango, resumen)."""
        ...

    async def read(self, document_id: uuid.UUID) -> dict | None:
        """Documento completo: title, url, markdown_content."""
        ...


#: El contenido de una respuesta de modelo, como texto plano. Vive en `core/` desde VER.1:
#: el mismo problema mordió en redacción, así que dejó de ser de este módulo.
_texto = texto_de


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
        searcher: FragmentSearcher | None = None,
    ) -> None:
        self._reader = reader
        self._tools = tools
        self._max_iterations = max_iterations
        self._searcher = searcher

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
                return leidas, _texto(respuesta.content)

            # El mensaje entero, no un dict con solo el texto: el `ToolMessage` que va
            # detrás se casa por `tool_call_id` con los `tool_calls` de ESTE turno. Sin
            # ellos queda huérfano, el modelo no ve el resultado y vuelve a pedir la misma
            # tool hasta agotar las iteraciones, devolviendo una respuesta en blanco.
            mensajes.append(respuesta)
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
            return await self._reader.list_index(
                chatbot_id, language, args.get("submateries")
            )

        if nombre == "read_document":
            doc_id = str(args.get("document_id", ""))
            documento = await self._reader.read(uuid.UUID(doc_id)) if doc_id else None
            if documento is None:
                return f"Documento {doc_id} no encontrado."
            texto = documento["markdown_content"]
            tokens = int(documento.get("token_count") or 0)
            truncada = tokens > LIMITE_LECTURA_TOKENS
            leidas.append(
                EvidenceItem(
                    source_id=doc_id,
                    content=texto[:EXCERPT_MAX],
                    source_url=documento["url"],
                    title=documento["title"],
                    language=documento.get("language"),
                    score=1.0,
                    # VIS.2: qué escalón del índice sirvió este documento. Sin esto, el
                    # retroceso escalonado no se puede medir sobre respuestas reales, y
                    # una estrategia que no se mide no se ajusta.
                    metadata={
                        "index_fallback_level": getattr(
                            self._reader, "last_index_level", None
                        ),
                        "lectura_truncada": truncada,
                    },
                )
            )
            if truncada:
                return texto[:CABECERA_AL_TRUNCAR] + _AVISO_TRUNCADO.format(tokens=tokens)
            return texto

        if nombre == "search_knowledge":
            return await self._buscar(args.get("query", ""), chatbot_id, language, leidas)

        return f"Tool {nombre} no reconocida."

    async def _buscar(
        self,
        consulta: str,
        chatbot_id: str,
        language: str | None,
        leidas: list[EvidenceItem],
    ) -> str:
        """Fragmentos que respondan a la consulta, para lo que no cabe entero.

        Sin buscador —un chatbot sin embeddings— se lo dice al modelo en la salida del tool
        en vez de reventar el turno: el modelo puede seguir con `read_document`.
        """
        if self._searcher is None:
            return (
                "La búsqueda por fragmentos no está disponible en este asistente. "
                "Usa `list_documents` y `read_document`."
            )
        encontrados = await self._searcher.search(consulta, chatbot_id, language)
        if not encontrados:
            return f"Sin fragmentos para «{consulta}»."
        leidas.extend(encontrados)
        return "\n\n".join(
            f"[{item.title}]({item.source_url})\n{item.content}" for item in encontrados
        )
