## Bloque RAG — Refuerzo del retrieval y calidad RAG (Subfase 1.B → 1.C, PENDIENTE)

> **Contexto**: planificado 2026-07-15 a partir de `docs/COMPARATIVA_RAG_LAMB.md` (comparativa arquitectónica del RAG con LAMB + recomendaciones propias + análisis "RAG vs agentes"). Principio rector: invertir en los **cimientos del retrieval** (índice híbrido real, reranker, representación del corpus, evaluación) porque son la herramienta que cualquier evolución agéntica consumirá; no invertir en sofisticación de pipeline que un bucle agéntico haría gratis.
>
> **Posición en el orden de ejecución** (acordada 2026-07-15, **actualizada 2026-07-28**): tras `ING.0` + carga del corpus v1, **antes** del resto del Bloque SEC. El corpus cargado es insumo del dataset dorado (RAG.1). El bloque se **parte**: `RAG.1` (baseline) y `RAG.2` (consolidación de grafos) van delante del **Bloque VIS**; `RAG.3→RAG.14`, detrás. Ver la tabla de enmiendas más abajo.
>
> **Estado**: ✅ relación de prompts aprobada y ✅ **detalle verbatim completado** (2ª pasada, 2026-07-15). Bloque listo para ejecutar cuando llegue su turno en el orden.
>
> **Lente de mantenibilidad (añadida 2026-07-24)**: `docs/RAG_SUSTITUCION_DEPENDENCIAS.md` reencuadra este bloque + el Bloque ING como "código propio → dependencia madura", derivado de `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md` §6 (RAG/ingesta se queda en el perímetro; el alivio de mantenimiento viene de apoyar las **primitivas** en librerías, no de mover nada a OWUI). Clasificación: **✅ ya apoyado, no tocar** (chunker→`langchain-text-splitters`, embeddings→`sentence-transformers`, PDF→`docling`); **♻️ reinventado, sustituir** (`keyword_search` ILIKE→FTS `tsvector` = **RAG.4**); **➕ hueco, añadir** (HNSW=**RAG.3**, reranker `bge-reranker-v2-m3` vía `sentence-transformers` ya instalada=**RAG.6**, parent-child=**RAG.8**, multi-formato en Docling=Bloque ING); **🔒 diferencial, no sustituir nunca** (`superseded`/P9, aislamiento `owner_id`, contrato de citas `sources`/P6, `hasher`, `quality/*`). **Anti-patrón**: no adoptar LlamaIndex/Haystack como orquestador (rompería la gobernanza tejida en el SQL). **80 % del valor**: RAG.4 + RAG.6.

### Propósito del bloque

1. **Consolidar los dos grafos** en uno: llevar `public_graphs/CoreGraph` (quality gate, cascada de config, LanguagePolicy — hoy solo en tests) a producción y retirar `agent/graph.py`.
2. **Medir antes de mejorar**: dataset dorado + métricas de recuperación en CI; toda mejora posterior se valida contra baseline.
3. **Elevar la calidad del retrieval**: índice HNSW, pata léxica real (tsvector), umbral + presupuesto de tokens, reranker cross-encoder, contextual retrieval, parent-child chunking.
4. **Robustecer los embeddings**: metadato de modelo/dimensión por chunk, validación inmutable al crear, ruta de re-embedding (patrón LAMB "por colección").
5. **Cerrar el bucle de calidad**: query rewriting conversacional, modo bypass de depuración, progreso granular de ingesta, test scenarios por chatbot y detección de huecos de corpus desde el feedback.

### Decisiones de diseño

- **Medir primero**: RAG.1 establece la baseline; ningún cambio del retriever (RAG.3–RAG.8, RAG.10) se cierra sin comparar recall@k/MRR contra ella en CI.
- **Consolidación temprana** (RAG.2): a partir de ahí existe **un solo grafo**; `agent/graph.py` se retira por **Caso B** (borrado directo, no es legacy NiceGUI) con el checklist completo de migración de CLAUDE.md. `Source` y `EvidenceItem` se unifican en el contrato de `public_graphs`.
- **Sin flags muertos**: `reranker_enabled` y `min_retrieval_score` (en `HubChatbot` desde 9B) o se activan (RAG.5, RAG.6) o se retiran del contrato. No queda config expuesta en la API admin sin consumidor.
- **Patrones importados de LAMB** (ver `docs/COMPARATIVA_RAG_LAMB.md` §7): query rewriting (`context_aware_rag`), config de embeddings inmutable y validada, parent-child chunking, connector `bypass`, `progress_callback` de ingesta, test scenarios. Lo que NO se copia: ChromaDB/SQLite, disco local, I/O síncrona, token estático.
- **Cambios de representación exigen re-embedding**: RAG.7 y RAG.8 alteran el texto embebido → migración de corpus documentada (comando de re-chunk/re-embed de RAG.9 como prerrequisito operativo si el corpus ya está cargado).
- **Deploy: edge** en todo el bloque (retrieval y datos del cliente); solo la UI admin de test scenarios (RAG.13) toca superficie cloud.

### Mapa de ejecución

| # | Prompt | Título | Depende de | Modelo sugerido |
|---|--------|--------|------------|-----------------|
| 1 | RAG.1 | Dataset dorado + métricas recall@k/MRR + CI de regresión | corpus de prueba (ING.0) | Sonnet |
| 2 | RAG.2 | Consolidación de grafos: CoreGraph a producción, retirada de `agent/graph.py` | 9B ✅, RAG.1 | **Opus** |
| 3 | RAG.3 | Índice HNSW en pgvector (migración Alembic) | — | Sonnet |
| 4 | RAG.4 | Pata léxica real: tsvector + GIN sustituye ILIKE en `HybridRetriever` | RAG.1 | Sonnet |
| 5 | RAG.5 | Activar `min_retrieval_score` + presupuesto de tokens del contexto | RAG.2 | Sonnet |
| 6 | RAG.6 | Reranker cross-encoder (BGE-reranker-v2-m3) + activar `reranker_enabled` | RAG.1, RAG.4 | **Opus** |
| 7 | RAG.7 | Contextual retrieval: headers + título en el texto embebido | RAG.1 | Sonnet |
| 8 | RAG.8 | Parent-child chunking (small-to-big) + chunking configurable por chatbot | RAG.7 | Sonnet |
| 9 | RAG.9 | Metadato de embeddings por chunk + validación inmutable + re-embedding | — | Sonnet |
| 10 | RAG.10 | Query rewriting conversacional (LLM pequeño + fallback) | RAG.2 | Sonnet |
| 11 | RAG.11 | Modo bypass/debug: prompt final sin llamar al LLM | RAG.2 | Sonnet |
| 12 | RAG.12 | Progreso granular de `HubIngestionJob` (callback + stats) | — | Sonnet |
| 13 | RAG.13 | Test scenarios por chatbot (backend + UI admin mínima) | RAG.11 | Sonnet |
| 14 | RAG.14 | Feedback → huecos de corpus (clustering + `HubContentFinding`, integra 9Q) | — | Sonnet/**Opus** |

RAG.3, RAG.9 y RAG.12 son independientes y pueden intercalarse como prompts cortos entre los mayores.

> **Enmiendas del 2026-07-28 (replanificación del corpus normativo).** El Bloque VIS se intercala **entre RAG.2 y RAG.3**: `ING.0.1→0.5` → carga del corpus v1 → `RAG.1` (baseline) → `RAG.2` (consolidación) → `VIS.1→VIS.3` → `RAG.3→RAG.14` → Bloque SYNC. Cuatro prompts de este bloque quedan enmendados en su detalle verbatim, marcado con `# ENMIENDA` in situ:
>
> | Prompt | Enmienda | Por qué |
> |---|---|---|
> | RAG.2 | La evidencia inicial del selector no se cementa como «índice de documentos» | ~72k tokens, no cabe; VIS.2 lo sustituye por el índice de submaterias (2.307 tokens) |
> | RAG.4 | El `tsvector` incorpora `termes_bilingues` de `doc_metadata` | El puente léxico despesa/gasto se regenera con SQL; en el embedding costaría GPU |
> | RAG.5 | `context_token_budget` **la crea VIS.2**; RAG.5 solo la consume | La columna la necesita antes la inyección de subconjunto del Nivel 2 |
> | RAG.7 | Solo se embebe contexto **estructural**; nunca la taxonomía | El vocabulario es revisable: taxonomía embebida ⇒ re-embedding en cada revisión |

### Reglas duras del bloque

- Ninguna mejora del retriever se cierra sin ejecutar la suite de RAG.1 y comparar contra baseline (adjuntar cifras en el cierre del prompt).
- **La taxonomía (ámbito, submaterias) nunca forma parte del texto embebido.** Es lo que mantiene revisable el vocabulario pendiente de validar por SG: reclasificar debe costar un `UPDATE`, no una reindexación.
- RAG.2 cumple el checklist de migración completo de CLAUDE.md: grep de referencias a `agent/graph.py` y a `Source` antiguo antes de cerrar; ningún import activo al código retirado.
- Los tests de retrieval de RAG.1 son **métricas puras sin LLM** (deben correr en CI en segundos); RAGAS queda para evaluación periódica, nunca como gate de CI.
- Todo router o servicio nuevo se etiqueta `Deploy: edge|cloud` en su docstring y se registra en `_register_edge`/`_register_cloud`.

### Prompts del bloque (detalle verbatim — 2ª pasada 2026-07-15)

---

### Prompt RAG.1 (RED/GREEN) — Dataset dorado + métricas de recuperación + CI de regresión

**Modelo sugerido**: **Sonnet** — métricas puras + harness; alcance cerrado, sin decisiones abiertas.

```
# PROMPT RAG.1 (RED/GREEN) — Dataset dorado y gate de CI de retrieval
# Deploy: edge

## Contratos (modules/agents_hub/evaluation/golden_dataset.py)
- GoldenQuery (Pydantic frozen): query, language ('ca'|'es'|'en'), expected_canonical_urls
  (list[str], min 1) | expected_document_ids, tags (list[str], p.ej. 'sigla', 'conversacional',
  'normativa'), history (list[str] | None — para RAG.10), notes.
- GoldenDataset: nombre, chatbot de referencia, documents_fingerprint (hash del corpus esperado,
  para detectar dataset desalineado del corpus), queries: list[GoldenQuery]. Loader JSON.

## Métricas (modules/agents_hub/evaluation/retrieval_metrics.py) — SIN LLM
- recall_at_k(retrieved_ids, expected_ids, k) -> float
- mrr(retrieved_ids, expected_ids) -> float
- Funciones puras sobre listas de IDs/URLs; nada de red ni BD.

## Harness (modules/agents_hub/evaluation/retrieval_eval.py)
- run_golden_eval(retriever, dataset, top_k) -> EvalReport {per_query: [...], recall_at_5,
  recall_at_10, mrr}: ejecuta HybridRetriever.hybrid_search por query y evalúa.
- Baseline versionada en server/tests/modules/agents_hub/evaluation/baselines/<dataset>.json.
- CLI (python -m ...evaluation.run_golden --dataset X --chatbot-id Y [--update-baseline]):
  informe tabular + diff contra baseline. --update-baseline regenera (uso deliberado, nunca CI).

## Dos niveles de ejecución (decisión de diseño)
1. CI: mini-corpus fixture determinista (15-25 .md pequeños en tests/fixtures/golden_corpus/,
   ingeridos en el setup del test vía IngestionWatcher sobre BD de test) + dataset dorado de
   ~25 queries. Gate: recall@5 y MRR >= baseline - 0.02 (tolerancia). Debe correr en segundos.
2. Manual/nightly: dataset completo (30-50 queries) contra el corpus de prueba cargado por
   ING.0.2 — vía CLI, no bloquea CI.

## RAGAS queda fuera de CI
- Documentar en evaluation/rag_metrics.py (docstring de módulo) que faithfulness/answer_relevancy
  son evaluación periódica manual; nunca gate de CI. Corregir de paso el `except Exception: pass`
  silencioso: log warning con el motivo del fallback léxico.

## Tests (RED primero) — tests/modules/agents_hub/evaluation/
# should_compute_recall_at_k_for_hit_and_miss
# should_compute_mrr_with_first_relevant_position
# should_load_and_validate_golden_dataset_schema
# should_reject_query_without_expected_targets
# should_run_eval_over_fixture_corpus_and_produce_report
# should_fail_gate_when_recall_drops_beyond_tolerance
# should_pass_gate_when_metrics_meet_baseline
# should_detect_corpus_fingerprint_mismatch

## Criterio de done
- [ ] Gate verde en CI con el mini-corpus (añadir al workflow ci.yml)
- [ ] Baseline inicial commiteada con las cifras del retriever actual (pre-mejoras)
- [ ] CLI probado contra el corpus de prueba de ING.0 (adjuntar cifras en el cierre)
```

---

### Prompt RAG.2 (RED/GREEN) — Consolidación de grafos: CoreGraph a producción

**Modelo sugerido**: **Opus** — migración multi-módulo con decisiones embebidas (unificación de contratos, port del loop agéntico, preservación del contrato SSE).

```
# PROMPT RAG.2 (RED/GREEN) — Un solo grafo: public_graphs/CoreGraph sirve /hub/chat
# Deploy: edge

## Objetivo
api/v1/hub_chat.py deja de construir el grafo con agent/graph.py:create_agent_graph y pasa a
usar public_graphs/core/graph_factory.py + CoreGraph. Entran en producción: quality gate con
fallback, cascada ConfigResolver (Plataforma→Organización→Chatbot), LanguagePolicy y el
contrato EvidenceItem.

## Qué se preserva (sin cambio de contrato observable)
- SSE: eventos status/token/done(sources)/error idénticos (astream_events v2). El evento done
  serializa EvidenceItem con el MISMO shape JSON actual (document_id, title, url, score) —
  el frontend/widget no se toca.
- enforce_citation_contract (agent/citation_validator.py) aplicado tras la generación.
- Router multi-materia (agent/router_node.py) ejecutado en el endpoint antes del grafo.
- Persistencia HubInteraction + trazas Langfuse (services/observability.py).
- agent/language_detector.py como implementación del nodo detect_language del CoreGraph.

## Port del modo agéntico
- El loop de agent/graph.py:_run_agentic_loop (bind_tools, máx. 10 iteraciones, acumulación de
  fuentes por read_document) se extrae a un componente del CoreGraph usado cuando
  retrieval_mode == MD_AGENT_SELECTOR. Los tools (agent/tools/) no cambian.
- strategies/md_agent_selector_pipeline.py deja de ser stub "índice completo": devuelve el
  índice de documentos como evidencia inicial y delega la selección al loop agéntico.
# ENMIENDA (2026-07-28, Bloque VIS): el índice de DOCUMENTOS es provisional y no se cementa.
# Medido en INFORME_MATERIES_I_METADADES_AGENTS.md §6.1: el catálogo de fichas son ~72k tokens
# y no cabe en el system prompt; el índice de las 58 submaterias son 2.307 tokens y sí cabe.
# VIS.2 lo sustituye por el índice de submaterias. Aquí basta con dejar el pipeline consolidado
# y el loop agéntico portado, con la selección aislada en un punto de extensión — sin asumir en
# los tests que la evidencia inicial es "todos los documentos".

## Unificación de contratos
- Source (agent/state.py) se retira; EvidenceItem (strategies/retrieval_contract.py) es el único
  contrato de evidencia. Las REGLAS DE CITA y format_sources_block de agent/prompts.py se
  integran en la TemplateStrategy del CoreGraph (una sola fuente del system prompt).

## Quality gate en producción
- cfg desde ConfigResolver (quality_threshold, min_retrieval_results, min_retrieval_score).
- Si el gate no pasa → nodo fallback: respuesta "no tengo información suficiente" (misma que
  usa el citation validator) emitida por SSE como respuesta normal + marcada en HubInteraction
  (nueva columna fallback_reason: 'quality_gate' | 'citation' | NULL — migración Alembic;
  RAG.14 la consume).

## Retirada (Caso B — borrado directo, checklist CLAUDE.md completo)
- agent/graph.py, Source en agent/state.py, partes de agent/prompts.py absorbidas.
- grep -r de create_agent_graph / AgentState.Source / imports de agent.graph antes de cerrar.
- Los tests que testeaban el grafo antiguo se migran al CoreGraph (no se borran aserciones de
  comportamiento: se reapuntan).

## Tests (RED primero) — tests/modules/agents_hub/ + tests/public_graphs/
# should_serve_chat_via_coregraph_in_rag_mode
# should_serve_chat_via_coregraph_in_long_context_mode
# should_serve_chat_via_coregraph_in_agent_selector_mode
# should_keep_sse_event_contract_unchanged           (snapshot de eventos)
# should_apply_quality_gate_fallback_on_low_evidence
# should_persist_fallback_reason_on_interaction
# should_resolve_config_cascade_in_live_chat         (org override visible en runtime)
# should_enforce_citation_contract_after_generation
# should_route_router_kind_chatbot_before_graph
# should_run_agentic_loop_with_tools_in_selector_mode
# should_have_no_references_to_retired_graph         (import scan)
+ suite e2e de chat existente (test_chat_flow.py, test_hub_chat_sse.py) verde SIN cambios de
  aserciones de contrato.

## Criterio de done
- [ ] Suite completa verde (backend) + RAG.1 sin regresión (adjuntar cifras)
- [ ] agent/graph.py eliminado; grep de referencias limpio
- [ ] Migración Alembic de fallback_reason aplicada (alembic current)
```

---

### Prompt RAG.3 (RED/GREEN) — Índice HNSW en pgvector

**Modelo sugerido**: **Sonnet** — migración puntual con verificación de plan de consulta.

```
# PROMPT RAG.3 (RED/GREEN) — Índice ANN para la búsqueda vectorial
# Deploy: edge

## Migración Alembic (server/migrations/versions/)
- CREATE INDEX ix_hub_document_chunks_embedding_hnsw ON hub_document_chunks
  USING hnsw (embedding vector_cosine_ops);  (defaults m=16, ef_construction=64)
- Ídem para hub_crawled_pages.page_embedding (lo usa el detector semántico 9Q).
- Downgrade: DROP INDEX. Requiere pgvector >= 0.5 (verificar versión de la imagen Docker;
  actualizar docker-compose si hace falta).

## Sin cambios de código
- La query de retriever.py (cosine_distance + ORDER BY) ya es indexable; no se toca.

## Tests (RED primero) — tests/modules/agents_hub/integration/test_hnsw_index.py
# should_use_hnsw_index_in_query_plan          (EXPLAIN contiene 'hnsw')
# should_return_same_top_k_as_exact_scan_on_small_corpus  (corpus fixture: ANN==exacto)
# should_apply_and_rollback_migration_cleanly

## Criterio de done
- [ ] uv run alembic upgrade head aplicado y alembic current mostrado
- [ ] Suite RAG.1 sin regresión (tolerancia del gate ya contempla ANN)
```

---

### Prompt RAG.4 (RED/GREEN) — Pata léxica real: tsvector + GIN sustituye ILIKE

**Modelo sugerido**: **Sonnet** — sustitución localizada en `_keyword_search`; contrato RRF intacto.

```
# PROMPT RAG.4 (RED/GREEN) — Full-text search de PostgreSQL en la rama léxica del híbrido
# Deploy: edge

## Migración Alembic
- Columna generada en hub_document_chunks:
  tsv tsvector GENERATED ALWAYS AS (to_tsvector(
    CASE WHEN language = 'es' THEN 'spanish'::regconfig ELSE 'simple'::regconfig END,
    coalesce(content, ''))) STORED
  (si el chunk no tiene columna language propia, derivarla del documento en la ingesta y
  añadirla primero — verificar el modelo real antes de escribir la migración).
- CREATE INDEX ... USING gin (tsv).
- Documentar limitación: catalán sin stemmer nativo en PG core → config 'simple' (sin stemming);
  posible diccionario Snowball/Hunspell catalán como mejora de despliegue, fuera de alcance.

## Retriever (services/retriever.py — _keyword_search)
- Sustituir el AND de ILIKE por websearch_to_tsquery(config_del_idioma, query) @@ tsv con
  ranking ts_rank_cd normalizado a [0,1] (dividir por el máximo del lote).
- Conservar: filtros chatbot_id / temporales / superseded / idioma, top_k*2, y la fusión RRF
  (k=60, vector_weight=0.7) SIN cambios. Si VIS.1 ya está cerrado, conservar también su
  MetadataFilter (ámbito / submateria / nivell_acces) — la sustitución es de la rama léxica,
  no del filtrado.
- BORRAR el código ILIKE (borra, no comentes).

# ENMIENDA (2026-07-28): puente léxico bilingüe en el tsvector, no en el embedding.
# El BM25 cross-lingüe falla del todo entre 'despesa' y 'gasto' (no comparten una letra). El
# informe de materias §6.2 propone pares bilingües del dominio como puente léxico. Su sitio es
# ESTA columna, no el texto embebido: el tsvector se regenera con una sentencia SQL, un
# embedding necesita GPU y horas.
# - La expresión del tsvector concatena content con los termes_bilingues del documento
#   (doc_metadata->>'termes_bilingues'). Como es columna generada y los términos viven en
#   hub_documents, la vía es o denormalizar esos términos al chunk en la ingesta, o pasar de
#   columna generada a columna materializada por trigger/ingesta. Elegir con el modelo real
#   delante y documentar la elección; NO meter la taxonomía (ámbito/submaterias) en ningún caso.
# - Test añadido: should_bridge_bilingual_terms_in_lexical_search  ('despesa' encuentra el chunk
#   castellano cuyo documento declara el par despesa/gasto).

## Tests (RED primero) — tests/modules/agents_hub/unit+integration/test_retriever.py (ampliar)
# should_match_stemmed_spanish_terms            ('becas' encuentra 'beca')
# should_rank_chunks_with_exact_terminology_first  (siglas/códigos: 'EBEP', 'RD 203/2021')
# should_use_simple_config_for_catalan_chunks
# should_return_normalized_keyword_scores
# should_keep_rrf_fusion_contract_unchanged
# should_use_gin_index_in_query_plan            (EXPLAIN)
# should_have_no_ilike_left_in_retriever        (scan del fichero)

## Criterio de done
- [ ] Migración aplicada (alembic current)
- [ ] RAG.1: mejora o igualdad de recall@5/MRR contra baseline, con cifras en el cierre
      (se esperan ganancias en las queries con tag 'sigla')
```

---

### Prompt RAG.5 (RED/GREEN) — Umbral de score aplicado + presupuesto de tokens del contexto

**Modelo sugerido**: **Sonnet** — consumo de config existente + empaquetador; decisiones acotadas aquí.

```
# PROMPT RAG.5 (RED/GREEN) — min_retrieval_score real + context packer con presupuesto
# Deploy: edge

## Umbral (decisión de diseño cerrada)
- min_retrieval_score (ya en HubChatbot, defaults org y ConfigResolver, default 0.25) se aplica
  sobre la SIMILITUD COSENO de la rama vectorial, ANTES de la fusión RRF (WHERE similarity >=
  umbral). La rama léxica no filtra por umbral (su señal es de ranking, no de similitud) —
  documentarlo en el docstring del retriever.
- El quality gate del CoreGraph (RAG.2) sigue usando quality_threshold sobre la media de
  evidencias: son dos controles distintos (por-chunk vs por-respuesta); documentar la relación.

## Empaquetador (services/retrieval/context_packer.py)
- pack(evidences: list[EvidenceItem], budget_tokens: int) -> PackedContext:
  1) ordenar por score desc; 2) fusionar chunks adyacentes del mismo documento (chunk_index
  consecutivos) eliminando solapamiento textual; 3) acumular hasta el presupuesto (contador de
  tokens reutilizando el que usa LongContextRetrievalStrategy para el límite de 128k); 4)
  registrar dropped_count para trazas/bypass.
- Config: nueva columna context_token_budget (nullable) en HubChatbot + default_context_token_budget
  en HubOrganizacion + default de plataforma 4000 en ConfigResolver (misma cascada que el resto).
  Migración Alembic + exposición en routers CRUD (hub_chatbots_router, hub_organizaciones_router).
# ENMIENDA (2026-07-28): la columna y su cascada las crea VIS.2, que las necesita antes para la
# inyección del subconjunto del Nivel 2. Aquí NO se crea la migración: solo se consume el valor
# ya resuelto por ConfigResolver. Se conserva el test should_resolve_budget_from_cascade_* como
# regresión. Si por lo que sea VIS.2 no estuviera cerrado al llegar aquí, crear la columna en
# este prompt y retirar el trozo correspondiente de VIS.2 — pero no en los dos.
# ENMIENDA (2026-07-31, decisión del usuario al cerrar el Bloque VIS): el default de plataforma
# es **128.000 y con carácter general**, no 4.000. Ya está creado y aplicado por VIS.2
# (migración d1m2n3o4p5q6). Bajarlo recortaría MD_LONG_CONTEXT a 4k y lo dejaría inservible, y
# un mismo valor no puede significar dos cosas según quién lo lea. El packer CONSUME este
# presupuesto tal cual; si necesita cortar antes por razones propias, con su constante y no
# tocando el default compartido.
- La estrategia RAG (vector_strategy / rag_vector_pipeline) usa el packer antes de construir el
  bloque DOCUMENTOS DISPONIBLES.

## Tests (RED primero)
# should_filter_vector_candidates_below_min_score
# should_keep_all_candidates_when_threshold_is_zero
# should_pack_context_within_token_budget
# should_drop_lowest_scored_evidence_first_when_cutting
# should_merge_adjacent_chunks_of_same_document
# should_resolve_budget_from_cascade_platform_org_chatbot
# should_report_dropped_count_in_packed_context

## Criterio de done
- [ ] Migración aplicada; flags visibles y FUNCIONALES desde la API admin
- [ ] RAG.1 sin regresión (el umbral 0.25 no debe recortar hits del dorado; si lo hace,
      ajustar default con datos y documentar)
```

---
