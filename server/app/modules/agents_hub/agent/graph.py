"""Grafo de LangGraph para el agente.

Soporta dos modos de operación:
- Modo Público (Chatbot): user_id=None, solo herramientas RAG públicas.
- Modo Agente (Identificado): user_id válido, desbloquea MCP y docs de usuario.
"""

import os

from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from server.app.modules.agents_hub.agent.language_detector import detect_language
from server.app.modules.agents_hub.agent.state import AgentState
from server.app.modules.agents_hub.agent.tools.search_knowledge import search_knowledge


def create_agent_graph(retriever, embedding_service, user_id: str | None = None):
    """Crea el grafo del agente.

    Args:
        retriever: Servicio de recuperación
        embedding_service: Servicio de embeddings
        user_id: ID del usuario (None para modo público)

    Returns:
        StateGraph configurado
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
    )

    async def route_by_capability_node(state: AgentState) -> dict:
        """Determina las capacidades disponibles según el rol del usuario."""
        available_tools = ["search_knowledge"]
        if user_id:
            available_tools.extend(["query_oracle_mcp", "search_user_docs"])
        return {"user_id": user_id, "available_tools": available_tools}

    async def detect_language_node(state: AgentState) -> dict:
        """Detecta el idioma del último mensaje."""
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, HumanMessage):
                language = detect_language(last_message.content)
                return {"language": language}
        return {"language": state.get("language", "es")}

    async def search_knowledge_node(state: AgentState) -> dict:
        """Busca información relevante."""
        messages = state.get("messages", [])
        if not messages:
            return {"retrieved_context": []}

        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage):
            return {"retrieved_context": []}

        result = await search_knowledge(
            query=last_message.content,
            chatbot_id=state["chatbot_id"],
            retriever=retriever,
            embedding_service=embedding_service,
            language=state.get("language"),
        )
        return {"retrieved_context": [result]}

    async def generate_response_node(state: AgentState) -> dict:
        """Genera la respuesta final."""
        messages = state.get("messages", [])
        context = state.get("retrieved_context", [])

        context_str = "\n".join(context) if context else "Sin información adicional."

        system_prompt = f"""Eres un asistente útil. Responde en {state.get("language", "es")}.

Información relevante:
{context_str}

Responde de forma concisa y útil."""

        response = await llm.ainvoke(
            [
                {"role": "system", "content": system_prompt},
                *[
                    {
                        "role": "user" if isinstance(m, HumanMessage) else "assistant",
                        "content": m.content,
                    }
                    for m in messages
                ],
            ]
        )

        return {"messages": [AIMessage(content=response.content)]}

    graph = StateGraph(AgentState)

    graph.add_node("route_by_capability", route_by_capability_node)
    graph.add_node("detect_language", detect_language_node)
    graph.add_node("search_knowledge", search_knowledge_node)
    graph.add_node("generate_response", generate_response_node)

    graph.set_entry_point("route_by_capability")
    graph.add_edge("route_by_capability", "detect_language")
    graph.add_edge("detect_language", "search_knowledge")
    graph.add_edge("search_knowledge", "generate_response")
    graph.add_edge("generate_response", END)

    return graph
