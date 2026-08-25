"""RAG.15 — `top_k` es `top_k`, y el mínimo es un mínimo.

**El defecto, medido el 2026-08-24 sobre el chatbot de normativa**: la estrategia de recuperación
se construía con `top_k=cfg.min_retrieval_results`. Dos consecuencias, y la primera es la que
importa:

1. **El asistente respondía con UN fragmento.** `min_retrieval_results` valía 1, así que el `top_k`
   efectivo era 1: sobre un corpus de 23.306 fragmentos, la respuesta se componía leyendo uno. En
   el lote ujirag, 25 de 25 respuestas con exactamente una fuente.
2. **`retrieval_top_k` era configuración muerta y editable.** Está en el modelo, en el alta y en la
   edición del router, y por tanto en el panel: un administrador podía cambiar un número que no
   hacía nada y creer que había ajustado la recuperación.

**La causa está un nivel más abajo de lo que decía el diagnóstico**, y por eso ningún pipeline lo
leía: `retrieval_top_k` **no existe en `PublicGraphConfig`**. No es que se olvidaran de usarlo, es
que nunca llegó a la configuración resuelta — así que no había nada que usar.

Y un efecto de segundo orden que confundió el diagnóstico del umbral: como `top_k` era el mínimo,
la comprobación `len(items) >= min_retrieval_results` del quality gate sólo se cumplía cuando se
recuperaban **exactamente** todos los que cabían, y si faltaba uno el score se multiplicaba por
0,5. Subir el mínimo no endurecía un mínimo: ampliaba la recuperación **y a la vez** hacía más
probable el castigo. Con los dos números separados, cada uno vuelve a significar lo que dice.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


class TestElConfigResueltoLlevaElTopK:

    def test_should_carry_retrieval_top_k_in_the_resolved_config(self):
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            PublicGraphConfig,
        )

        assert "retrieval_top_k" in PublicGraphConfig.__dataclass_fields__, (
            "`retrieval_top_k` no llega a la configuración resuelta, así que ningún pipeline "
            "puede leerlo por mucho que el panel lo deje editar"
        )

    def test_should_default_to_a_width_that_is_not_the_minimum(self):
        """El valor por omisión del config resuelto no puede ser el mínimo de resultados: son
        dos decisiones distintas y confundirlas es justo el defecto que este prompt cierra."""
        from server.app.modules.agents_hub.agent.public_graphs.core import config_resolver

        por_defecto = config_resolver._PLATFORM_DEFAULTS
        assert por_defecto.retrieval_top_k > por_defecto.min_retrieval_results


class TestLaEstrategiaRecibeElTopK:

    @pytest.mark.asyncio
    async def test_should_pass_retrieval_top_k_to_the_strategy(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline import (
            RagVectorPipeline,
        )

        cfg = SimpleNamespace(
            retrieval_top_k=8,
            min_retrieval_results=2,
            min_retrieval_score=0.0,
            reranker_enabled=False,
        )
        deps = SimpleNamespace(session=object(), embedder=object())

        estrategia = await RagVectorPipeline()._construir_estrategia(deps, cfg)

        assert estrategia._top_k == 8

    @pytest.mark.asyncio
    async def test_should_not_use_min_retrieval_results_as_top_k(self):
        """El caso real del piloto: mínimo 1 y anchura 8. Si `top_k` acaba valiendo 1, el
        asistente compone la respuesta leyendo un solo fragmento."""
        from server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline import (
            RagVectorPipeline,
        )

        cfg = SimpleNamespace(
            retrieval_top_k=8,
            min_retrieval_results=1,
            min_retrieval_score=0.0,
            reranker_enabled=False,
        )
        deps = SimpleNamespace(session=object(), embedder=object())

        estrategia = await RagVectorPipeline()._construir_estrategia(deps, cfg)

        assert estrategia._top_k != 1, (
            "la estrategia se construye con el mínimo como anchura: es el defecto que hacía "
            "que 25 de 25 respuestas del lote citaran una sola fuente"
        )
        assert estrategia._top_k == 8

    def test_should_not_read_the_minimum_as_width_anywhere(self):
        """Guardarraíl: el mismo error estaba en dos sitios, y arreglar uno solo deja el otro
        decidiendo la anchura de las respuestas de otro perfil de grafo."""
        from pathlib import Path

        culpables = []
        for ruta in Path("app/modules/agents_hub/agent/public_graphs").rglob("*.py"):
            texto = ruta.read_text(encoding="utf-8")
            for numero, linea in enumerate(texto.splitlines(), 1):
                if "top_k=" not in linea or "min_retrieval_results" not in linea:
                    continue
                # La reserva `retrieval_top_k or min_retrieval_results` es legítima y
                # deliberada: mantiene en pie a los dobles de test que sólo declaran el mínimo,
                # que son unos cuantos. Lo que se persigue es leer el mínimo **en lugar** de la
                # anchura, no leerlo *después* de ella.
                if "retrieval_top_k" in linea:
                    continue
                culpables.append(f"{ruta.as_posix()}:{numero}")

        assert culpables == [], (
            "estos sitios usan el mínimo de resultados como anchura de recuperación: "
            f"{culpables}"
        )


class TestElMinimoSigueSiendoUnMinimo:

    def test_should_penalise_only_when_fewer_items_than_the_minimum(self):
        """El gate, desacoplado del `top_k`.

        Antes los dos números eran el mismo, así que «he recuperado menos de los que caben» y
        «he recuperado menos de los que necesito» eran la misma condición. Separados, recuperar
        8 con un mínimo de 2 tiene que pasar el gate sin penalización.
        """
        from pathlib import Path

        fuente = Path(
            "app/modules/agents_hub/agent/public_graphs/core/core_graph.py"
        ).read_text(encoding="utf-8")

        assert "len(items) >= self.cfg.min_retrieval_results" in fuente, (
            "el gate de calidad tiene que seguir comparando contra el MÍNIMO, no contra la "
            "anchura: es lo único que hace que `min_retrieval_results` signifique algo"
        )
