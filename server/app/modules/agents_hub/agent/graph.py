"""Grafo de LangGraph para el agente.

Soporta tres modos de recuperacion:
- vector: HybridRetriever + agrupacion por documento
- long_context: corpus completo en el contexto (prompt caching Anthropic)
- agentic: LLM decide que documentos leer con list_documents / read_document

Deploy: edge
"""

import uuid

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END, StateGraph

from server.app.modules.agents_hub.agent.citation_validator import enforce_citation_contract
from server.app.modules.agents_hub.agent.language_detector import detect_language
from server.app.modules.agents_hub.agent.prompts import build_system_prompt, format_sources_block
from server.app.modules.agents_hub.agent.state import AgentState
from server.app.modules.agents_hub.services.retrieval.types import Source


def create_agent_graph(
    retrieval_strategy,
    llm,
    base_system_prompt: str,
    user_id: str | None = None,
):
    """Crea el grafo del agente.

    Args:
        retrieval_strategy: RetrievalStrategy (vector / long_context / agentic)
        llm: BaseChatModel inyectado
        base_system_prompt: system_prompt del HubChatbot
        user_id: ID del usuario (None para modo publico)
    """

    async def detect_language_node(state: AgentState) -> dict:
        messages = state.get("messages", [])
        if messages:
            last = messages[-1]
            if isinstance(last, HumanMessage):
                return {"language": detect_language(last.content)}
        return {"language": state.get("language", "es")}

    async def search_or_skip_node(state: AgentState) -> dict:
        if retrieval_strategy.mode == "agentic":
            return {"retrieved_sources": [], "retrieval_mode": "agentic", "total_tokens": 0}
        messages = state.get("messages", [])
        query = ""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                query = m.content
                break
        ctx = await retrieval_strategy.get_context(
            query=query,
            chatbot_id=uuid.UUID(state["chatbot_id"]),
            language=state.get("language"),
        )
        return {
            "retrieved_sources": ctx.sources,
            "retrieval_mode": ctx.mode,
            "total_tokens": ctx.total_tokens,
        }

    async def generate_response_node(state: AgentState) -> dict:
        sources = list(state.get("retrieved_sources", []))
        mode = state.get("retrieval_mode", "vector")
        sources_block = format_sources_block(sources)
        system = build_system_prompt(
            base_system_prompt,
            state.get("language", "es"),
            sources_block,
            mode,
        )
        history = [
            {
                "role": "user" if isinstance(m, HumanMessage) else "assistant",
                "content": m.content,
            }
            for m in state.get("messages", [])
        ]

        if mode == "agentic":
            llm_with_tools = llm.bind_tools(retrieval_strategy.get_agent_tools())
            sources, text = await _run_agentic_loop(
                llm_with_tools, system, history, retrieval_strategy, state
            )
        else:
            response = await llm.ainvoke([{"role": "system", "content": system}, *history])
            text = response.content

        validated = enforce_citation_contract(text, sources, mode)
        return {"messages": [AIMessage(content=validated)], "sources": sources}

    graph = StateGraph(AgentState)
    graph.add_node("detect_language", detect_language_node)
    graph.add_node("search_or_skip", search_or_skip_node)
    graph.add_node("generate_response", generate_response_node)

    graph.set_entry_point("detect_language")
    graph.add_edge("detect_language", "search_or_skip")
    graph.add_edge("search_or_skip", "generate_response")
    graph.add_edge("generate_response", END)

    return graph


async def _run_agentic_loop(
    llm_with_tools,
    system: str,
    history: list[dict],
    retrieval_strategy,
    state: dict,
    max_iterations: int = 10,
) -> tuple[list[Source], str]:
    """Ejecuta el loop tool-calling para el modo agentic.

    Devuelve (sources_used, final_text).
    """
    messages = [{"role": "system", "content": system}, *history]
    sources_used: list[Source] = []
    chatbot_id = state.get("chatbot_id", "")
    language = state.get("language")

    for _ in range(max_iterations):
        response = await llm_with_tools.ainvoke(messages)
        if not getattr(response, "tool_calls", None):
            return sources_used, response.content

        messages.append({"role": "assistant", "content": response.content or ""})
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            if tool_name == "list_documents":
                from server.app.modules.agents_hub.agent.tools.list_documents import list_documents
                tool_output = await list_documents(chatbot_id, retrieval_strategy, language)
            elif tool_name == "read_document":
                doc_id = tool_args.get("document_id", "")
                doc = await retrieval_strategy.read(uuid.UUID(doc_id))
                if doc:
                    sources_used.append(Source(
                        document_id=uuid.UUID(doc_id),
                        title=doc["title"],
                        url=doc["url"],
                        excerpt=doc["markdown_content"][:500],
                        score=1.0,
                    ))
                from server.app.modules.agents_hub.agent.tools.read_document import read_document
                tool_output = await read_document(doc_id, retrieval_strategy)
            else:
                tool_output = f"Tool {tool_name} no reconocida."
            messages.append(ToolMessage(content=tool_output, tool_call_id=tc["id"]))

    return sources_used, ""
