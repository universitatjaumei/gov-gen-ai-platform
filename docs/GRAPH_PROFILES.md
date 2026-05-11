# Guía de perfiles y pipelines de grafos públicos

## Qué es CoreGraph

`CoreGraph` es el orquestador común a todos los chatbots públicos
(`server/app/modules/agents_hub/agent/public_graphs/core/core_graph.py`).
Ejecuta siempre el mismo flujo:

```
detect_language → retrieve → merge → quality_gate
                                         ↓ ok          ↓ bajo
                                  generate_answer    fallback
                                         ↓
                                        log → END
```

No contiene lógica de dominio ni conoce el `retrieval_mode`. Toda la
variación entre chatbots se inyecta a través de cuatro estrategias:

| Estrategia | Responsabilidad |
|---|---|
| `RetrievalStrategy` | Decide cómo y de dónde recuperar evidencias |
| `MergeStrategy` | Fusiona los buckets de evidencia en una lista plana |
| `TemplateStrategy` | Construye el contexto de prompt para el LLM |
| `LanguagePolicy` | Detecta el idioma, filtra y genera warnings de traducción |

## Qué es un GraphProfile

Un perfil es un bundle de las cuatro estrategias adaptado a un caso de uso
concreto. Cada perfil se registra en `GraphProfileRegistry` como una factoría
`(cfg, deps, llm) → CoreGraph`. Los perfiles disponibles se definen en
`PublicGraphProfile` (`types.py`):

| Perfil | Caso de uso | Módulo |
|---|---|---|
| `PUBLIC_KB_RICH` | Chatbot genérico con KB enriquecida (grupos, FAQs, oferta académica) | `profiles/public_kb_rich.py` |
| `PUBLIC_PORTAL_AGGREGATOR` | Portal que agrega dos fuentes (procedimientos + normativa) | `profiles/public_portal_aggregator.py` |
| `PUBLIC_PORTAL_ROUTER` | Portal que enruta entre chatbots hijos disjuntos | `profiles/public_portal_router.py` |

## Qué es retrieval_mode

`retrieval_mode` es el mecanismo de recuperación de documentos que usa el
pipeline subyacente. Se resuelve en la cascada de config
(plataforma → organización → chatbot). Los tres modos disponibles son:

| Modo | Pipeline | Cuándo usarlo |
|---|---|---|
| `RAG` | `RagVectorPipeline` | KBs medianas con buen índice vectorial |
| `MD_LONG_CONTEXT` | `MdLongContextPipeline` | Corpus pequeño que cabe en contexto |
| `MD_AGENT_SELECTOR` | `MdAgentSelectorPipeline` | Selección agéntica (stub; evoluciona en 9B.8+) |

El `retrieval_mode` es **independiente** del perfil: cualquier perfil puede
operar con cualquier modo. El `CoreGraph` no conoce el modo; lo conoce la
`RetrievalStrategy` (o el perfil que la instancia).

## Cómo añadir un perfil nuevo

Ejemplo: perfil `OFERTA_ACADEMICA` para estructuras de grados y másteres.

### 1. Registrar el valor en el enum

```python
# types.py
class PublicGraphProfile(str, Enum):
    PUBLIC_KB_RICH           = "PUBLIC_KB_RICH"
    PUBLIC_PORTAL_AGGREGATOR = "PUBLIC_PORTAL_AGGREGATOR"
    PUBLIC_PORTAL_ROUTER     = "PUBLIC_PORTAL_ROUTER"
    OFERTA_ACADEMICA         = "OFERTA_ACADEMICA"   # ← nuevo
```

### 2. Crear el módulo de perfil

```python
# profiles/oferta_academica.py
"""Perfil OFERTA_ACADEMICA — grados, másteres y programas estructurados.

Deploy: edge
"""
from server.app.modules.agents_hub.agent.public_graphs.profiles.public_kb_rich import (
    DefaultLanguagePolicy,
    PassthroughMergeStrategy,
    SingleSourceRetrievalStrategy,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import EvidenceItem


class AcademicAnswerTemplateStrategy:
    """Plantilla estructurada: sección de Grado + sección de Acceso + sección de Plan."""

    def build_prompt_context(self, items: list[EvidenceItem], language: str | None, query: str) -> str:
        lang_hint = f"Responde en idioma: {language}." if language else ""
        sections = "\n\n".join(
            f"## {item.title or item.source_id}\n{item.content}" for item in items
        )
        return f"{lang_hint}\n\nUsa sólo la siguiente información académica:\n\n{sections}".strip()
```

### 3. Registrar la factoría en `graph_factory.py`

```python
# core/graph_factory.py (al final del archivo)

def _make_oferta_academica(cfg, deps, llm=None):
    from server.app.modules.agents_hub.agent.public_graphs.profiles.oferta_academica import (
        AcademicAnswerTemplateStrategy,
    )
    from server.app.modules.agents_hub.agent.public_graphs.profiles.public_kb_rich import (
        DefaultLanguagePolicy,
        PassthroughMergeStrategy,
        SingleSourceRetrievalStrategy,
    )
    return CoreGraph(
        retrieval_strategy=SingleSourceRetrievalStrategy(),
        merge_strategy=PassthroughMergeStrategy(),
        template_strategy=AcademicAnswerTemplateStrategy(),
        language_policy=DefaultLanguagePolicy(),
        cfg=cfg,
        deps=deps,
        llm=llm,
    )

register_profile(PublicGraphProfile.OFERTA_ACADEMICA, _make_oferta_academica)
```

### 4. Escribir los tests de contrato del perfil nuevo

Los tests en `tests/public_graphs/test_profile_contract.py` se ejecutan
automáticamente para todo perfil en `_default_registry`. Basta con que el
nuevo perfil esté registrado al importar `graph_factory`.

## Cómo añadir un pipeline nuevo

Si apareciese un modo `HYBRID_RERANK` que combina RAG y reranker externo:

### 1. Crear el módulo de pipeline

```python
# strategies/hybrid_rerank_pipeline.py
"""HybridRerankPipeline — RAG + reranker externo.

Deploy: edge
"""
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem, RetrievalResult,
)


class HybridRerankPipeline:
    async def run(self, query, chatbot_id, cfg, deps) -> RetrievalResult:
        # ... implementación ...
        return RetrievalResult(items=[], debug={"pipeline_mode": "HYBRID_RERANK"})
```

### 2. Registrar el modo en `retrieval_pipeline_factory.py`

```python
_VALID_MODES = ("RAG", "MD_LONG_CONTEXT", "MD_AGENT_SELECTOR", "HYBRID_RERANK")

def get_pipeline(mode: str):
    ...
    if mode == "HYBRID_RERANK":
        from ...strategies.hybrid_rerank_pipeline import HybridRerankPipeline
        return HybridRerankPipeline()
    raise ValueError(...)
```

### 3. Añadir el mock en `test_pipeline_contract_suite.py`

El test parametrizado sobre `_VALID_MODES` ya cubrirá el nuevo modo,
pero hay que añadir la rama de mocking en `_patch_for_mode`:

```python
elif mode == "HYBRID_RERANK":
    return [patch(
        "...hybrid_rerank_pipeline.HybridRerankPipeline.run",
        AsyncMock(return_value=RetrievalResult(items=[], debug={"pipeline_mode": "HYBRID_RERANK"})),
    )]
```

## Reglas de extensión

- Un perfil nuevo **no modifica** `CoreGraph` ni los protocolos existentes.
- Un modo nuevo **no modifica** los perfiles existentes.
- El contrato `RetrievalResult` con `items: list[EvidenceItem]` es inmutable:
  todo pipeline nuevo debe respetarlo.
- Los tests de contrato (`test_profile_contract.py`,
  `test_pipeline_contract_suite.py`) se ejecutan automáticamente sobre el
  nuevo perfil/pipeline sin modificar los archivos de test.
