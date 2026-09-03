## FASE 9B: Grafo Público Extensible (CoreGraph + GraphProfiles + RetrievalPipelineFactory)

**Objetivo de la Fase**: Diseñar e implementar una arquitectura de grafo público extensible para una plataforma multi-organización, manteniendo un enfoque determinista-first, TDD (RED/GREEN) y reutilización máxima de componentes.

El objetivo NO es implementar un único chatbot, sino una **plataforma** capaz de soportar **múltiples chatbots públicos** con **hipótesis de uso distintas**, **estrategias de retrieval distintas**, y **configuración en cascada**, sin acoplar la topología del grafo a un único dominio.

**Dependencias**: Fase 4 (grafo LangGraph operativo), Fase 5B (LocalEmbeddingService BGE-M3)

**Decisiones de diseño**:

- **No grafo monolítico**: no se implementa un único grafo "gigante" con condicionales por dominio. En su lugar: un `CoreGraph` reutilizable, un contrato de `GraphProfiles` seleccionables por chatbot, y un contrato de `RetrievalPipeline` enchufables.
- **CoreGraph**: define el flujo común (idioma, retrieval, merge, rerank, generate, quality_gate, fallback, log). No contiene lógica específica de ningún dominio ni modo de retrieval.
- **GraphProfiles**: definen la topología lógica y el UX por tipo de chatbot (agregación, routing, plantilla de respuesta). Ejemplos: `PUBLIC_KB_RICH` (genérico) y `PUBLIC_PORTAL_AGGREGATOR` (UJI: normativa + procedimientos).
- **RetrievalPipelineFactory**: selecciona pipeline según `retrieval_mode` (`RAG` / `MD_LONG_CONTEXT` / `MD_AGENT_SELECTOR`). Garantiza un contrato común de salida (`RetrievalResult`) para todas las estrategias. El CoreGraph es agnóstico a cómo se obtuvo la evidencia.
- **Configuración en cascada**: Plataforma → Organización → Chatbot. La organización aporta defaults; el chatbot puede sobrescribir cualquier parámetro. No existe lista de "perfiles permitidos" por organización.
- **Caso piloto UJI** (`PUBLIC_PORTAL_AGGREGATOR`): dos dominios relacionados (normativa + procedimientos), comportamiento de agregación, preferencia de idioma (prefer, no strict), aviso de traducción si el idioma de la evidencia difiere del idioma del usuario.

**Arquitectura objetivo**:
```
CoreGraph (flujo común)
  detect_language → retrieve (delegado a RetrievalStrategy + Pipeline) → merge (por perfil)
  → rerank (opcional) → generate_answer (plantilla por perfil)
  → quality_gate (faithfulness + relevance) → fallback honesto / log_interaction

GraphProfiles
  PUBLIC_KB_RICH            ← genérico: grupos, oferta académica, FAQs municipales
  PUBLIC_PORTAL_AGGREGATOR  ← UJI: normativa + procedimientos, merge dual

RetrievalPipelineFactory
  RAG              ← retrieval vectorial clásico
  MD_LONG_CONTEXT  ← document packs Markdown
  MD_AGENT_SELECTOR ← agente selecciona documentos/secciones
```

---

### Prompt 9B.1 (RED) — Estructura de librería de grafos públicos + registry

```markdown
# PROMPT 9B.1 (RED) — Crear estructura de librería de grafos públicos + registry

Objetivo: crear una librería extensible para grafos públicos:
- CoreGraph (nodos comunes)
- Perfiles (Graph Profiles)
- Estrategias enchufables
- Registry (catálogo de perfiles)

Tareas:
1) Crear carpetas:
   server/app/modules/agents_hub/agent/public_graphs/
     core/
     profiles/
     strategies/
     registry.py
     types.py

2) Definir en types.py:
   - Enum PublicGraphProfile con valores iniciales:
     PUBLIC_KB_RICH
     PUBLIC_PORTAL_ROUTER (opcional, preparado)
     PUBLIC_PORTAL_AGGREGATOR (UJI)

3) Implementar registry.py:
   - register_profile(profile_name, profile_factory)
   - get_profile(profile_name) -> profile_factory o error
   - list_profiles() -> list[str]

Tests (RED) en tests/public_graphs/test_registry.py:
- test_registry_lists_profiles
- test_registry_raises_on_unknown_profile
- test_registry_can_register_and_get_profile

Criterio de aceptación:
- La estructura existe y los tests del registry pasan.
```

---

### Prompt 9B.2 (RED) — Modelo de datos: `public_graph_profile` + `retrieval_mode` + defaults de organización

```markdown
# PROMPT 9B.2 (RED) — Modelo de datos para selección de perfil + retrieval_mode + cascada de defaults

Objetivo: permitir múltiples perfiles y múltiples estrategias de retrieval por chatbot/portal (por uso),
sin restricciones por organización. La organización aporta defaults; el chatbot puede sobrescribir.

Tareas:
1) Añadir campos a HubChatbot:
   - public_graph_profile: str (default "PUBLIC_KB_RICH")
   - retrieval_mode: str (default "RAG")  # RAG | MD_LONG_CONTEXT | MD_AGENT_SELECTOR
   - language_mode: str (default "prefer")  # strict | prefer | none
   - quality_threshold: float (default 0.6)
   - min_retrieval_results: int (default 2)
   - min_retrieval_score: float (default 0.25)
   - reranker_enabled: bool (default true)
   - answer_template: str (default "generic")

2) Añadir defaults a la entidad Organización:
   - default_public_graph_profile: str (default "PUBLIC_KB_RICH")
   - default_retrieval_mode: str (default "RAG")
   - default_language_mode: str (default "prefer")
   - default_quality_threshold, default_min_retrieval_results, default_min_retrieval_score
   - default_reranker_enabled, default_answer_template

3) Migraciones Alembic para ambas tablas.

Tests (RED):
- test_chatbot_has_retrieval_mode_default
- test_org_has_default_retrieval_mode
- test_migration_applies_defaults_without_breaking_existing_rows

Criterio de aceptación:
- Dos chatbots de la misma organización pueden tener retrieval_mode distinto.
- No existe campo de "allowed profiles/modes" por organización (sin restricciones).
```

---

### Prompt 9B.3 (RED/GREEN) — ConfigResolver efectivo (cascada) incluye `retrieval_mode`

```markdown
# PROMPT 9B.3 (RED/GREEN) — ConfigResolver: Platform → Organization → Chatbot (incluye retrieval_mode)

Objetivo: resolver configuración efectiva del grafo público por chatbot.

Tareas:
1) Crear core/config_resolver.py:
   - PublicGraphConfig (dataclass/pydantic) con:
     profile, retrieval_mode, language_mode, thresholds, reranker_enabled, answer_template, etc.
   - async get_effective_public_graph_config(chatbot_id, session) -> PublicGraphConfig

2) PlatformDefaults: valores hardcoded o ConfigProvider global.

Tests (RED):
- test_effective_config_uses_platform_defaults
- test_effective_config_org_overrides_platform
- test_effective_config_chatbot_overrides_org
- test_effective_config_includes_retrieval_mode

GREEN:
- Implementación mínima para pasar tests.
```

---

### Prompt 9B.4 (RED) — Contrato de evidencias + contrato de pipelines (tests de contrato)

```markdown
# PROMPT 9B.4 (RED) — Contrato de Evidencia + Protocolos de RetrievalPipeline (con tests de contrato)

Objetivo: definir un contrato uniforme de salida del retrieval, independiente de la estrategia usada.
Es lo que evita necesitar "un grafo por retriever".

Tareas:
1) Crear strategies/retrieval_contract.py:
   - EvidenceItem:
       source_id: str
       source_url: str | None
       title: str | None
       content: str
       language: str | None
       score: float | None
       metadata: dict
   - RetrievalResult:
       items: list[EvidenceItem]
       context_source_language: str | None
       debug: dict

2) Crear strategies/retrieval_pipeline_protocol.py:
   - class RetrievalPipeline(Protocol):
       async def run(query: str, chatbot_id: str, cfg: PublicGraphConfig, deps: GraphDeps) -> RetrievalResult

3) Tests de contrato (RED) en tests/public_graphs/test_retrieval_contract.py:
   - test_pipeline_result_has_items_and_debug
   - test_evidence_item_has_required_fields
   - test_context_source_language_is_set_when_items_present
   - test_contract_is_serializable_or_repr_safe

Criterio de aceptación:
- Existe un contrato estable de retrieval que todos los pipelines deben cumplir.
```

---

### Prompt 9B.5 (RED/GREEN) — RetrievalPipelineFactory + pipelines stub + tests de contrato por modo

```markdown
# PROMPT 9B.5 (RED/GREEN) — RetrievalPipelineFactory + 3 pipelines (RAG / MD_LONG_CONTEXT / MD_AGENT_SELECTOR)

Objetivo: implementar una fábrica que devuelva un pipeline según retrieval_mode, y verificar por tests
que cada pipeline cumple el contrato.

Tareas:
1) Crear strategies/retrieval_pipeline_factory.py:
   - def get_pipeline(mode: str) -> RetrievalPipeline
   - lanzar ValueError si mode desconocido

2) Implementar pipelines mínimos:
   - RagVectorPipeline: llama al retriever vectorial existente y devuelve EvidenceItem por chunk
   - MdLongContextPipeline: selecciona un subconjunto de docs MD y construye un "pack" en items
   - MdAgentSelectorPipeline: (mínimo) simula selección de docs sin LLM y devuelve items

3) Tests (RED) en tests/public_graphs/test_retrieval_pipeline_factory.py:
   - test_factory_returns_pipeline_for_each_mode
   - test_factory_raises_for_unknown_mode

4) Tests de contrato por pipeline (RED) en tests/public_graphs/test_retrieval_pipelines_contract.py:
   - test_rag_pipeline_conforms_to_contract
   - test_md_long_context_pipeline_conforms_to_contract
   - test_md_agent_selector_pipeline_conforms_to_contract

GREEN:
- Implementación mínima para pasar tests.
```

---

### Prompt 9B.6 (RED) — Protocolos/Interfaces de estrategias actualizados para usar pipelines

```markdown
# PROMPT 9B.6 (RED) — Protocolos de estrategias (actualizados para RetrievalPipeline)

Objetivo: los perfiles siguen definiendo RetrievalStrategy/Merge/Template/LanguagePolicy,
pero RetrievalStrategy debe usar el pipeline devuelto por RetrievalPipelineFactory según cfg.retrieval_mode.

Tareas:
1) En strategies/protocols.py:
   - RetrievalStrategy.retrieve(...) devuelve RetrievalOutput
   - RetrievalOutput puede contener uno o varios RetrievalResult (p.ej. buckets)
   - RetrievalStrategy invoca internamente get_pipeline(cfg.retrieval_mode).run(...)

2) Tests (RED):
   - test_retrieval_strategy_uses_pipeline_factory
   - test_retrieval_output_can_hold_multiple_buckets

Criterio:
- retrieval_mode se aplica sin cambiar CoreGraph.
```

---

### Prompt 9B.7 (RED/GREEN) — CoreGraph (orquestación común)

```markdown
# PROMPT 9B.7 (RED/GREEN) — CoreGraph: orquestación común usando RetrievalStrategy

Objetivo: CoreGraph ejecuta el flujo común sin lógica específica de dominio ni retrieval_mode:
detect_language → retrieve → merge → (optional) rerank → generate_answer → quality_gate → (log | fallback)

Tareas:
- Implementar/ajustar core/core_graph.py para trabajar con RetrievalOutput/RetrievalResult.
- No introducir lógica específica de UJI ni de ningún modo de retrieval.

Tests (RED):
- test_core_graph_compiles_with_mock_strategies
- test_core_graph_branches_to_fallback_when_quality_low
- test_core_graph_runs_with_each_retrieval_mode_using_generic_profile

GREEN:
- Implementación mínima.
```

---

### Prompt 9B.8 (RED/GREEN) — Perfil genérico PUBLIC_KB_RICH (compatible con los 3 retrieval_mode)

```markdown
# PROMPT 9B.8 (RED/GREEN) — PUBLIC_KB_RICH compatible con 3 retrieval_mode

Objetivo: perfil "default" para futuros chatbots (grupos, oferta académica, FAQs municipales).
Debe funcionar con cualquiera de los 3 modos de retrieval.

Tareas:
1) profiles/public_kb_rich.py:
   - SingleSourceRetrievalStrategy: usa pipeline(cfg.retrieval_mode)
   - PassthroughMergeStrategy
   - GenericAnswerTemplateStrategy
   - DefaultLanguagePolicy

2) Tests (RED):
   - test_public_kb_rich_runs_in_rag_mode
   - test_public_kb_rich_runs_in_md_long_context_mode
   - test_public_kb_rich_runs_in_md_agent_selector_mode

GREEN:
- Implementación.

Criterio:
- Un chatbot público genérico funciona con los 3 modos sin cambiar de grafo.
```

---

### Prompt 9B.9 (RED/GREEN) — Perfil PUBLIC_PORTAL_ROUTER (opcional, compatible con retrieval_mode)

```markdown
# PROMPT 9B.9 (RED/GREEN) — PUBLIC_PORTAL_ROUTER (opcional) compatible con retrieval_mode

Objetivo: portal que enruta entre chatbots hijos si los dominios son disjuntos.
El retrieval dentro del hijo respeta su cfg.retrieval_mode.

Tareas:
- Implementar profiles/public_portal_router.py:
   - decide chatbot hijo
   - carga effective config del hijo
   - ejecuta CoreGraph con el perfil del hijo (o fuerza PUBLIC_KB_RICH si procede)

Tests (RED):
- test_portal_router_selects_child_chatbot_and_uses_child_retrieval_mode

GREEN:
- Implementación.
```

---

### Prompt 9B.10 (RED) — Tests del perfil UJI agregador (independiente de retrieval_mode)

```markdown
# PROMPT 9B.10 (RED) — Tests UJI Aggregator: combina procedimientos + normativa en cualquier retrieval_mode

El perfil UJI agrega dos fuentes (procedimientos + normativa). El mismo perfil debe operar con
retrieval_mode=RAG (lo normal) y, en el futuro, con MD_LONG_CONTEXT o MD_AGENT_SELECTOR sin duplicar el grafo.

Tests:
- test_uji_aggregator_rag_mode_combines_procedure_and_normativa
- test_uji_aggregator_md_long_context_mode_combines_procedure_and_normativa
- test_uji_aggregator_md_agent_selector_mode_combines_procedure_and_normativa
- test_uji_normativa_only_when_no_procedure_candidate
- test_uji_answer_template_sections_present
- test_uji_translation_warning_only_when_context_language_differs
```

---

### Prompt 9B.11 (GREEN) — Implementación del perfil UJI agregador usando pipelines por bucket

```markdown
# PROMPT 9B.11 (GREEN) — Implementar PUBLIC_PORTAL_AGGREGATOR (UJI) usando pipelines según cfg.retrieval_mode

Objetivo: RetrievalStrategy dual:
- bucket procedimientos: pipeline(cfg.retrieval_mode).run(...) sobre fuente procedimientos
- bucket normativa: pipeline(cfg.retrieval_mode).run(...) sobre fuente normativa

Merge:
- si hay procedimiento candidato:
    - incluir procedimiento top
    - recuperar normativa enlazada por URL/canonical_id si existe
    - añadir normativa general como respaldo
- si no:
    - solo normativa

Notas:
- Deduplicación no puede basarse solo en URL si el contenido varía por idioma;
  usar doc_id o (canonical_url, language).

Criterio:
- Pasa los tests del Prompt 9B.10 sin cambiar CoreGraph.
```

---

### Prompt 9B.12 (RED/GREEN) — LanguagePolicy (prefer/strict/none) + warning por idioma real del contexto

```markdown
# PROMPT 9B.12 (RED/GREEN) — LanguagePolicy y warning de traducción

Objetivo:
- prefer: prioriza idioma del usuario si existe evidencia; evita doble búsqueda innecesaria.
- strict: permite comportamiento de filtro estricto si se necesita.
- none: neutral.

Warning de traducción:
- Se muestra si context_source_language != query_language.
- No se dispara por "fallback_triggered" de calidad (son señales distintas).

Tests:
- test_language_policy_prefer_avoids_double_search
- test_language_policy_strict_can_trigger_fallback
- test_warning_only_when_context_language_differs
```

---

### Prompt 9B.13 (RED/GREEN) — GraphFactory runtime: selección de perfil + pipeline por chatbot

```markdown
# PROMPT 9B.13 (RED/GREEN) — GraphFactory runtime: perfil + retrieval_mode por chatbot

Objetivo: punto de integración final. El endpoint público debe:
- resolver config efectiva (incluye public_graph_profile y retrieval_mode)
- seleccionar perfil en registry
- crear CoreGraph con el bundle de estrategias del perfil
- ejecutar

Tests:
- test_graph_factory_uses_chatbot_override_profile_and_retrieval_mode
- test_graph_factory_uses_org_defaults_when_chatbot_missing
- test_graph_factory_uses_platform_defaults_when_org_missing
```

---

### Prompt 9B.14 — Kit de ampliación (docs + tests de contrato por perfil y pipeline)

```markdown
# PROMPT 9B.14 — Kit para añadir perfiles y pipelines (docs + tests de contrato)

Objetivo: dejar la plataforma lista para crecer sin reabrir arquitectura.

Tareas:
1) docs/GRAPH_PROFILES.md:
   - qué es CoreGraph
   - qué es un GraphProfile
   - qué es retrieval_mode
   - cómo añadir un perfil nuevo (ej. oferta académica estructurada)
   - cómo añadir un pipeline nuevo (si apareciera un modo futuro)

2) tests/public_graphs/test_profile_contract.py:
   - todo perfil registrado debe:
     - compilar grafo
     - tener strategies no nulas
     - poder ejecutarse con cada retrieval_mode (smoke)

3) tests/public_graphs/test_pipeline_contract_suite.py:
   - todo pipeline en factory debe pasar el contrato común (EvidenceItem, RetrievalResult)
```

---


---
