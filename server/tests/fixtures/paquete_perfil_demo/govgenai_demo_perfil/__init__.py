"""Paquete de ejemplo: un perfil y un pipeline aportados desde fuera de la plataforma.

Esto es lo que escribiría un tercero. Fíjate en lo que **no** hay: ni un import del registro, ni
una llamada para darse de alta, ni nada específico de la plataforma más allá de los dos
protocolos. El paquete sólo expone dos objetos y los declara en su `pyproject.toml`; de
encontrarlos y registrarlos se encarga el cargador al arrancar.
"""

from __future__ import annotations

from typing import Any


def construir_perfil_demo(cfg: Any, deps: Any, llm: Any = None) -> Any:
    """Factoría de perfil: `(cfg, deps, llm) -> CoreGraph`.

    Envuelve las estrategias del perfil operativo del núcleo con otro nombre, que es el caso
    realista: quien aporta un perfil casi nunca reimplementa los cuatro ejes, sino que cambia uno
    y reutiliza el resto.

    El import va **dentro** de la función a propósito. Un import de nivel superior obligaría a
    tener la plataforma instalada para poder siquiera importar este módulo, y el cargador importa
    cada *entry point* para comprobarlo: un fallo ahí abortaría el arranque de la plataforma por
    un paquete que en realidad sólo quería declararse.
    """
    from server.app.modules.agents_hub.agent.public_graphs.core.graph_factory import (
        _make_public_kb_rich,
    )

    return _make_public_kb_rich(cfg, deps, llm)


class PipelineDemo:
    """Pipeline de recuperación mínimo que cumple `RetrievalPipeline`.

    Devuelve un resultado fijo. Sirve para comprobar el camino entero —descubrimiento, registro,
    construcción— sin depender de una base de datos ni de un servicio de *embeddings*.
    """

    async def run(self, query: str, chatbot_id: str, cfg: Any, deps: Any) -> Any:
        from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
            EvidenceItem,
            RetrievalResult,
        )

        return RetrievalResult(
            items=[
                EvidenceItem(
                    source_id="demo-1",
                    content=f"Resultado de ejemplo para: {query}",
                    score=1.0,
                )
            ],
            debug={"pipeline_mode": "DEMO_PIPELINE"},
        )
