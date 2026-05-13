"""TracingService — capa de observabilidad para el DraftingCoreGraph (9R.6.5).

Reutiliza la infraestructura de Langfuse del módulo agents_hub cuando está disponible.
Si LANGFUSE_SECRET_KEY no está configurada, todos los métodos son no-ops.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Protocolo de handles de span
# ---------------------------------------------------------------------------

@runtime_checkable
class SpanHandle(Protocol):
    def set_attribute(self, key: str, value: Any) -> None: ...
    def add_event(self, name: str, **attrs: Any) -> None: ...
    def end(self) -> None: ...


# ---------------------------------------------------------------------------
# Protocolo de servicio de tracing
# ---------------------------------------------------------------------------

@runtime_checkable
class TracingService(Protocol):
    def open_trace(
        self,
        trace_name: str,
        workspace_id: str,
        template_version_id: str,
    ) -> SpanHandle: ...

    def node_span(self, node_name: str, **attrs: Any) -> SpanHandle: ...


# ---------------------------------------------------------------------------
# Implementación no-op (default cuando Langfuse no está configurado)
# ---------------------------------------------------------------------------

class NoOpSpanHandle:
    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def add_event(self, name: str, **attrs: Any) -> None:
        pass

    def end(self) -> None:
        pass


class NoOpTracingService:
    def open_trace(
        self,
        trace_name: str,
        workspace_id: str,
        template_version_id: str,
    ) -> NoOpSpanHandle:
        return NoOpSpanHandle()

    def node_span(self, node_name: str, **attrs: Any) -> NoOpSpanHandle:
        return NoOpSpanHandle()


# ---------------------------------------------------------------------------
# Helper: envuelve un nodo con tracing
# ---------------------------------------------------------------------------

def traced_node(node_fn, tracing: Any, node_name: str):
    """Devuelve un callable async que abre un node_span alrededor del nodo original.

    - Extrae atributos IA (model_used, prompt_version) del patch resultante.
    - En caso de excepción: emite span.add_event("error", ...) antes de relanzar.
    """
    async def wrapper(state):
        span = tracing.node_span(node_name)
        try:
            result = await node_fn(state) or {}
            # Adjuntar atributos IA si el nodo actualizó bloques con content de IA
            for bstate in result.get("blocks", {}).values():
                content = getattr(bstate, "content", None)
                if isinstance(content, dict) and "model_used" in content:
                    span.set_attribute("model_used", content["model_used"])
                    span.set_attribute("prompt_version", content.get("prompt_version"))
            return result
        except Exception as exc:
            span.add_event("error", type=type(exc).__name__, message=str(exc))
            raise
        finally:
            span.end()

    return wrapper
