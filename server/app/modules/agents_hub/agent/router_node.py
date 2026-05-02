"""Nodo router multi-materia: clasifica la consulta y delega a un sub-chatbot."""

from __future__ import annotations

import uuid
from typing import Any, Protocol

import numpy as np


class ChatbotChildrenProvider(Protocol):
    """Proveedor de hijos de un chatbot router."""

    async def get_children(self, parent_id: uuid.UUID) -> list[Any]: ...


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Calcula similitud coseno segura."""
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def build_route_to_subagent_node(
    embedding_service: Any,
    chatbot_provider: ChatbotChildrenProvider,
    llm_fallback: Any | None = None,
    confidence_threshold: float = 0.65,
):
    """Construye el nodo async de routing a subagentes."""

    async def node(state: dict[str, Any]) -> dict[str, Any]:
        router_id = uuid.UUID(str(state["chatbot_id"]))
        children = await chatbot_provider.get_children(router_id)

        if not children:
            raise ValueError(f"Chatbot router {router_id} sin hijos atómicos.")

        if len(children) == 1:
            return {
                "selected_child_id": str(children[0].id),
                "routing_confidence": 1.0,
            }

        query = state["messages"][-1].content
        query_embedding = np.array(await embedding_service.embed(query), dtype=float)

        scored_children: list[tuple[Any, float]] = []
        for child in children:
            prompt_embedding = np.array(
                await embedding_service.embed(child.system_prompt), dtype=float
            )
            score = _cosine(query_embedding, prompt_embedding)
            scored_children.append((child, score))

        scored_children.sort(key=lambda item: item[1], reverse=True)
        best_child, best_confidence = scored_children[0]

        if llm_fallback is not None and best_confidence < confidence_threshold:
            options = "\n".join(
                f"- {child.id}: {child.name} ({child.system_prompt[:120]})"
                for child, _ in scored_children
            )
            response = await llm_fallback.ainvoke(
                [
                    {
                        "role": "system",
                        "content": (
                            "Devuelve SOLO el UUID del sub-chatbot que mejor responda. "
                            "Sin explicaciones."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Consulta: {query}\n\nOpciones:\n{options}",
                    },
                ]
            )
            picked_id = str(response.content).strip()
            picked_child = next(
                (child for child, _ in scored_children if str(child.id) == picked_id),
                best_child,
            )
            return {
                "selected_child_id": str(picked_child.id),
                "routing_confidence": float(best_confidence),
            }

        return {
            "selected_child_id": str(best_child.id),
            "routing_confidence": float(best_confidence),
        }

    return node