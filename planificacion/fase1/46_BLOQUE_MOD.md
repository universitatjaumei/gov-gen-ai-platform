## Bloque MOD — Modelos de embedding y reranker: local en edge, API en cloud (2026-08-01)

> **Añadido a petición del usuario**, antes de ejecutar RAG.6 y **antes de cargar el corpus v1**.
> Decisión completa, con la verificación de la API de Google: `docs/DECISION_MODELOS_EMBEDDING_RERANKER.md`.
>
> Lo que lo motiva: BGE-M3 (1,1 GB) más el reranker local (~600 MB) son los 3-4 GB por instancia
> que `CLAUDE.md` fija como criterio de extracción a microservicio. En cloud queremos API; en
> edge queremos modelo local, porque el dato no sale. El mismo codebase debe servir a los dos.
>
> **Por qué antes de cargar el corpus**: cambiar de modelo después cuesta re-embeber las ~380
> normas con su índice HNSW detrás. Ahora es el momento más barato que va a existir.

---

### Prompt MOD.1 (RED/GREEN) — Propósito en la configuración + procedencia en el vector

**Modelo sugerido**: **Sonnet** — dos columnas y un guardarraíl; las decisiones están cerradas en el documento.

```
# PROMPT MOD.1 (RED/GREEN) — Que cambiar de modelo deje de ser un salto al vacio
# Deploy: cloud (configuracion) + edge (procedencia y guarda)

## Contexto medido (no repetir la investigacion)
- gemini-embedding-001 admite dimension FLEXIBLE de 128 a 3072: 1024 es valido. La columna
  Vector(1024), el indice HNSW y el corpus cargado sobreviven a un cambio de proveedor.
- Las dimensiones distintas de 3072 NO vienen normalizadas ("you must manually normalize
  non-3072 dimensions"). Normalizamos nosotros, siempre, venga como venga del proveedor.
- La guarda de dimension de hub_chatbots_router.py NO PUEDE SALTAR: compara dos getattr de
  atributos que no existen. Se arregla aqui.

## Configuracion (HubLLMConfig)
- purpose: 'chat' | 'embedding' | 'rerank', default 'chat', CON CheckConstraint —es una
  enumeracion estable con consumidor, mismo criterio que nivell_acces en ING.0.2.
- output_dimensionality: int | None. None = el default del modelo.
- Se REUTILIZA el panel existente (HubProvider con base_url y api_key, available-models, test
  de conexion, LLMConfigsPage). No se construye un panel nuevo: se filtra por purpose.

## Procedencia (HubDocumentChunk)
- embedding_model: str | None y embedding_dim: int | None, escritos por la ingesta.
- Sin esto, la configuracion es un interruptor que rompe en silencio: el coseno entre
  vectores de dos espacios distintos no da error, da resultados malos.

## Servicios
- LocalEmbeddingService y GoogleEmbeddingService exponen `model_name` y `dimensions`.
- GoogleEmbeddingService acepta modelo y output_dimensionality, y L2-normaliza su salida.
- get_embedding_service() sigue devolviendo el local: la seleccion por configuracion es MOD.2.

## Tests (RED primero)
# should_persist_purpose_and_output_dimensionality
# should_reject_an_unknown_purpose                  (el CHECK muerde)
# should_expose_model_name_and_dimensions_on_services
# should_l2_normalize_google_embeddings             (venga o no normalizado del proveedor)
# should_record_model_and_dimension_on_every_chunk  (la ingesta escribe procedencia)
# should_detect_a_corpus_embedded_with_another_model (la guarda ya puede saltar)

## Criterio de done
- [ ] Migracion aplicada y reversible
- [ ] La guarda de recalculate-corpus salta de verdad, con test que lo demuestre
- [ ] Contrato OpenAPI + Orval regenerados si cambia la API
```

---

### Prompt MOD.2 (RED/GREEN) — Seleccion del servicio de embeddings por configuracion

**Modelo sugerido**: **Sonnet** — cableado sobre la cascada que ya existe.

```
# PROMPT MOD.2 (RED/GREEN) — get_embedding_service resuelve contra la config efectiva
# Deploy: shared

- La cascada Plataforma -> Organizacion -> Chatbot elige el servicio, igual que el resto de
  la configuracion. GoogleEmbeddingService deja de ser codigo muerto.
- Aqui encaja HttpEmbeddingService, previsto en CLAUDE.md para cuando BGE-M3 se extraiga a
  microservicio: el resto del codigo no cambia.
- SIN fallback silencioso: si el modelo configurado no carga, error explicito.
- El default de plataforma SIGUE siendo BGE-M3 local. Cambiarlo es un UPDATE, no un deploy.

## Despacho por provider_type, no por proposito (ampliacion del 2026-08-01)

MOD.1 dejo configurable QUE modelo y con QUE clave, pero QUE ADAPTADOR lo habla seguia
siendo codigo. El mecanismo para resolverlo ya existe y hay que aprovecharlo, no duplicarlo:
`HubProvider.provider_type` ('google_genai', 'openai_compatible', ...) es lo que usa
`model_factory._build_model` para elegir implementacion DESDE DATOS en el chat.

- La factoria de embeddings y la de rerank despachan por `provider_type`, igual que la de
  chat. Anadir un modelo o cambiar de proveedor DENTRO de un tipo ya soportado pasa a ser un
  UPDATE; el codigo solo se toca para un tipo de proveedor nuevo, que es irreducible.
- Los tres purpose comparten factoria y contrato de resolucion. Tres despachos paralelos
  divergen: ya paso con el system prompt antes de RAG.2.
- Test: should_resolve_the_adapter_from_provider_type_without_code_changes

## Medicion pendiente que este prompt habilita (no la ejecuta)

Cuando el corpus v1 este cargado, comparar BGE-M3 contra Google a 1024 con `run_golden.py`
sobre el dorado en valenciano. La documentacion de Google declara 100+ idiomas y lidera
MMTEB, pero NO publica lista por idioma y el catalan no aparece explicitamente: la calidad en
valenciano hay que medirla, no suponerla. Con la cascada por chatbot y la procedencia de
MOD.1 se pueden tener dos chatbots sobre el mismo corpus, uno por modelo, sin mezclar
espacios vectoriales.
```

---

### Prompt RAG.6 (RED/GREEN) — Reranker detrás de protocolo + activación de `reranker_enabled`

**Modelo sugerido**: **Opus** — integración con decisiones reales: normalización de scores, pool de candidatos, gestión del default heredado y medición.

```
# PROMPT RAG.6 (RED/GREEN) — Reranker detrás de protocolo, flag por chatbot
# Deploy: edge

# PARTIDO EN DOS (2026-08-01, decisión del usuario de habilitar los servicios de GCP todos a
# la vez durante el despliegue). Cada mitad entrega algo que funciona:
#
#   RAG.6a — EL MECANISMO. Se puede hacer YA, sin ningún servicio habilitado: protocolo
#     Reranker, resolución por configuración (purpose='rerank' + provider_type, patrón de
#     MOD.2), pool ampliado, sustitución del score, normalización y cableado en
#     rag_vector_pipeline por `_construir_estrategia`. Tests con un **reranker determinista**,
#     igual que RAG.1 mide el mecanismo de recuperación con un embedding determinista.
#
#   RAG.6b — EL ADAPTADOR REAL Y LA MEDICIÓN. **Va DESPUÉS del bloque Deploy**, porque el
#     Ranking API vive en Discovery Engine y lo habilita D.0. Aquí se comprueba que el
#     contrato escrito coincide con el real —un adaptador probado solo contra un doble está
#     verificado en su lógica, no en su integración— y se decide con datos si el flag se
#     enciende en algún sitio.
#
# Por qué se parte y no se espera entero: escribir un adaptador que nunca ha hablado con el
# servicio real es la familia de riesgo que este proyecto ya pisó tres veces el 2026-08-01
# —GoogleEmbeddingService inalcanzable durante meses, la guarda de dimensión que no podía
# saltar, y su test verificando un campo inventado—. Las tres pasaban los tests.
#
# La medición del idioma NO necesita el corpus v1: el dataset dorado ya está en valenciano y
# el corpus de fixture son 25 normas breves. RAG.6b depende solo de D.0.
#
# Al habilitar el servicio (en D.0), comprobar dos cosas que la documentación pública no deja
# cerradas:
#   1. Precio por consulta vigente (la referencia que se manejó, ~1 $/1.000 consultas, viene
#      de fuente secundaria: la pagina oficial de precios no se pudo leer).
#   2. Si aplica el **modelo de suscripción mensual** que Discovery Engine ofrece para apps y
#      data stores. El Ranking API es STATELESS —no indexa, no hay data store— asi que no
#      deberia aplicarle, pero es la unica via de coste fijo plausible y hay que confirmarlo.
#
# ELECCION DE MODELO, ya cerrada por medicion del codigo: `semantic-ranker-default-004`
# (1.024 tokens). Las variantes -003 y -002 son de 512 tokens y el chunker produce chunks de
# 4.000 caracteres (~1.000 tokens): truncarian la mitad de cada chunk.
#
# RIESGO ABIERTO que este prompt debe cerrar con datos: Google declara 25 idiomas y NO
# publica cuales; el catalan no aparece. Si el valenciano no esta, el reranker reordenaria
# por senales que no entiende y la degradacion seria silenciosa. Se decide con el gate de
# RAG.1 sobre el dorado en valenciano: dos ejecuciones, con y sin reranker.
#
# ENMIENDA (2026-08-01, decisión del usuario — ver docs/DECISION_MODELOS_EMBEDDING_RERANKER.md):
# **el reranker nace por API, no local.** El prompt original ponía LocalReranker como
# implementación de referencia; eso añade ~600 MB al contenedor y construye justo el problema
# que el Bloque MOD viene a evitar. Se invierte:
# - La implementación de referencia es por API (proveedor a decidir con datos de precio y
#   latencia: Vertex AI Ranking, Cohere Rerank u otro; NO se elige a ciegas en este prompt).
# - `LocalReranker` se conserva como opción de EDGE, detrás del mismo protocolo.
# - El proveedor y el modelo se configuran con `purpose='rerank'` en HubLLMConfig (MOD.1), no
#   con una constante en el código.
# - **Ojo al default**: `reranker_enabled` viene en True en toda la cascada, así que en cuanto
#   exista la implementación se activa para TODOS los chatbots. Decidir explícitamente si el
#   default se queda en True, con la misma disciplina que el umbral de RAG.5.

## Protocolo e implementación (services/reranker.py)
- class Reranker(Protocol): async def rerank(query: str, candidates: list[str], top_k: int)
  -> list[RerankResult {index, score}].
- LocalReranker (opción edge): sentence_transformers.CrossEncoder('BAAI/bge-reranker-v2-m3'),
  singleton lazy-load + asyncio.to_thread + batch, scores normalizados con sigmoide a [0,1]
  (mismo patrón que LocalEmbeddingService). get_reranker() para Depends.
- SIN fallback silencioso (regla CLAUDE.md): si reranker_enabled y el modelo no carga,
  error explícito en el arranque del servicio — no degradar a híbrido sin avisar.

## Integración (vector_strategy / rag_vector_pipeline)
- Si cfg.reranker_enabled: recuperar pool ampliado (max(30, top_k*3)) del híbrido →
  rerank(query, [content]) → quedarse top_k. El score del reranker SUSTITUYE al de fusión
  para el packer (RAG.5) y el quality gate (los umbrales operan sobre [0,1] coherente).
- Log de duración del rerank en la traza Langfuse (observability).

## Default heredado (decisión cerrada)
- reranker_enabled tiene default True desde 9B pero nunca se consumió. Al activarlo de verdad:
  migración Alembic que pone False en chatbots/organizaciones existentes + default False en
  modelo, routers y ConfigResolver. El admin lo activa por chatbot tras validar con RAG.1.
  (~1.1 GB extra de RAM in-process: mismo criterio de extracción a microservicio que BGE-M3,
  CLAUDE.md §microservicios; el protocolo ya deja listo un futuro HttpReranker.)

## Tests (RED primero) — unit con CrossEncoder mockeado; 1 test integración marcado slow
# should_rerank_candidates_with_relevant_first        (fixture con pares obvios)
# should_not_call_reranker_when_flag_disabled         (spy)
# should_retrieve_wider_pool_when_reranking
# should_normalize_scores_to_unit_interval
# should_replace_fusion_score_with_rerank_score
# should_fail_loudly_when_enabled_and_model_unavailable
# should_log_rerank_latency_in_trace
# should_default_to_disabled_after_migration

## Criterio de done
- [ ] RAG.1 con flag ON vs OFF: adjuntar tabla comparativa (recall@5, MRR, latencia media)
- [ ] Migración de defaults aplicada; sin flags muertos restantes en el contrato
```

---

### Prompt RAG.7 (RED/GREEN) — Contextual retrieval estructural (headers en el texto embebido)

**Modelo sugerido**: **Sonnet** — cambio localizado en chunker/watcher + regeneración con herramienta existente.

```
# PROMPT RAG.7 (RED/GREEN) — Embeber chunks con su contexto jerárquico
# Deploy: edge

## Chunker (ingestion/chunker.py)
- Cada chunk expone embedding_text = "<título documento> > <header_1> > <header_2> > <header_3>
  \n\n<content>" (niveles presentes; sin duplicar si el content empieza por el propio header).
- El content ALMACENADO y mostrado como evidencia NO cambia; embedding_text no se persiste.

# ENMIENDA (2026-07-28): la jerarquía son CUATRO niveles y la taxonomía no entra.
# - Tras ING.0.4 el chunker sigue header_1..header_5 (documento / título / capítulo / sección /
#   unidad citable, según docs/CONTRATO_MD_CORPUS.md). embedding_text los usa todos, y usa
#   'ruta' cuando esté disponible.
# - REGLA DURA: en embedding_text solo entra contexto ESTRUCTURAL (título del documento y
#   encabezados). NUNCA ambit_principal, submateries, submateries_internes ni ninguna etiqueta
#   del vocabulario. Motivo: el vocabulario está pendiente de validar por SG y debe seguir
#   siendo revisable; taxonomía embebida ⇒ cada revisión cuesta un re-embedding del corpus.
#   Los pares bilingües van al tsvector de RAG.4, por lo mismo.
# - El ancla ({#art-14}) NO va en embedding_text: es ruido para el vector. Va en chunk_metadata
#   y se usa para construir la URL de la cita.
# - Test añadido: should_not_include_taxonomy_or_anchor_in_embedding_text

## Watcher (ingestion/watcher.py)
- embed(embedding_text) en lugar de embed(content).
- De paso: embeber por LOTES (encode acepta lista) en vez de chunk a chunk (watcher es hoy
  secuencial) — mismo prompt porque toca la misma línea.

## Hook de nivel 2 (definir, NO implementar)
- Protocolo ContextEnricher (enrich(document, chunk) -> str) con NoopEnricher por defecto,
  inyectado en el chunker. El enricher LLM (frase de contexto generada en ingesta, técnica
  "contextual retrieval") queda documentado como candidato post-corpus-definitivo. Sin código
  muerto: solo el protocolo + Noop que ya se usa.

## Regeneración del corpus
- Reutilizar services/corpus_recalculator.py (ya regenera chunks al cambiar de modo) para
  re-chunk+re-embed del corpus de prueba tras el cambio. Si RAG.9 ya está hecho, usar su CLI.

## Tests (RED primero)
# should_build_embedding_text_with_title_and_header_hierarchy
# should_not_duplicate_header_when_content_starts_with_it
# should_keep_stored_content_unchanged
# should_embed_enriched_text_not_raw_content      (spy sobre embedding_service)
# should_embed_chunks_in_batches
# should_regenerate_corpus_via_recalculator

## Criterio de done
- [ ] Corpus de prueba regenerado; RAG.1 comparado (adjuntar cifras; se espera mejora en
      queries cuya respuesta vive en secciones profundas)
```

---

### Prompt RAG.8 (RED/GREEN) — Parent-child chunking + chunking configurable por chatbot

**Modelo sugerido**: **Sonnet** — patrón conocido (LAMB `hierarchical_ingest`/`parent_child_query`) sobre infraestructura propia ya existente.

```
# PROMPT RAG.8 (RED/GREEN) — Small-to-big opcional + parámetros de chunking en la cascada
# Deploy: edge

## Config por chatbot (migración Alembic + cascada)
- HubChatbot: chunk_size (int, nullable), chunk_overlap (int, nullable),
  chunking_strategy ('structural' | 'parent_child', nullable).
- Defaults org (default_chunk_*) + plataforma (1000/100/'structural') vía ConfigResolver.
- watcher deja de instanciar MarkdownChunker con defaults hardcodeados: lee la config resuelta.
- Exponer en routers CRUD (contract-first: el frontend los recibe del contrato OpenAPI).

## Estrategia parent_child (ingestion/chunker.py)
- Hijos: RecursiveCharacterTextSplitter con chunk_size_child (default 400) DENTRO de cada
  sección estructural; el embedding es del hijo (compone con embedding_text de RAG.7).
- Padre: la sección estructural completa → columna parent_content (Text, nullable) en
  HubDocumentChunk (migración). Decisión: columna directa, no join — simplicidad y el
  padre ya existe como texto en el documento.
- Retrieval: cuando parent_content no es NULL, la evidencia devuelve parent_content como
  excerpt (vector_strategy agrupa por documento: el "mejor chunk" pasa a ser "mejor padre",
  deduplicando hijos del mismo padre).

## Cambio de estrategia = regeneración
- corpus_recalculator soporta el cambio chunking_strategy (borra chunks y regenera), igual
  que hace hoy con retrieval_mode.

## Tests (RED primero)
# should_use_per_chatbot_chunk_size_and_overlap
# should_fall_back_to_cascade_defaults_when_unset
# should_split_children_within_structural_sections
# should_store_parent_section_on_child_chunks
# should_return_parent_content_as_evidence
# should_deduplicate_children_of_same_parent_in_results
# should_regenerate_chunks_on_strategy_change

## Criterio de done
- [ ] Migraciones aplicadas; config visible y funcional en API admin
- [ ] RAG.1 sobre el fixture con parent_child ON vs OFF: cifras en el cierre
```

---

### Prompt RAG.9 (RED/GREEN) — Metadato de embeddings + validación + re-embedding masivo

**Modelo sugerido**: **Sonnet** — patrón LAMB "config por colección" adaptado; alcance enumerado.

```
# PROMPT RAG.9 (RED/GREEN) — Trazabilidad y migrabilidad del modelo de embedding
# Deploy: edge

## Esquema (migración Alembic)
- HubDocumentChunk: embedding_model (String, nullable=False tras backfill),
  embedding_dim (Integer). Backfill: filas existentes → 'BAAI/bge-m3' / 1024.

## Servicio (services/embedding_service.py)
- El protocolo EmbeddingService expone model_name y dim; LocalEmbeddingService ('BAAI/bge-m3',
  1024) y GoogleEmbeddingService ('models/text-embedding-004', 768) los implementan.
- El watcher estampa model_name/dim en cada chunk al ingerir.

## Guardas (decisión cerrada: un solo modelo por despliegue edge)
- En query: si el corpus del chatbot contiene embedding_model distinto del servicio activo →
  error explícito con instrucción de re-embedding (nunca resultados silenciosamente malos).
- Al crear/activar chatbot: validación con embedding de prueba del servicio activo (patrón
  LAMB) — falla rápido si el servicio no está operativo.
- Documentar en el docstring del módulo: la incompatibilidad Google-768d vs Vector(1024) se
  resuelve por re-embedding completo del despliegue, no por convivencia de dimensiones.

## CLI de re-embedding (python -m ...ingestion.reembed)
- Argumentos: --chatbot-id [--all] [--dry-run]. Recorre chunks en lotes (streaming, sin cargar
  el corpus en memoria), re-embebe con el servicio activo y estampa metadato nuevo.
- Idempotente: chunks ya en el modelo activo se saltan (salvo --force).
- Es la herramienta operativa de RAG.7/RAG.8 cuando el corpus ya está cargado.

## Tests (RED primero)
# should_stamp_model_and_dim_on_ingestion
# should_backfill_existing_chunks_in_migration
# should_raise_clear_error_on_model_mismatch_at_query
# should_validate_embedding_service_on_chatbot_creation
# should_reembed_corpus_in_batches_via_cli
# should_skip_chunks_already_on_active_model
# should_report_plan_in_dry_run

## Criterio de done
- [ ] Migración + backfill aplicados (alembic current)
- [ ] CLI ejecutado en dry-run contra el corpus de prueba (salida en el cierre)
```

---

### Prompt RAG.10 (RED/GREEN) — Query rewriting conversacional

**Modelo sugerido**: **Sonnet** — patrón `context_aware_rag` de LAMB con fallbacks; alcance cerrado.

```
# PROMPT RAG.10 (RED/GREEN) — Reescritura de consulta con historial antes del retrieve
# Deploy: edge

## Nodo (public_graphs/core/) — antes del retrieve en CoreGraph
- Condición: cfg.query_rewriting_enabled Y len(historial) >= 2 turnos. Si no → passthrough.
- LLM pequeño-rápido vía model_factory. Config en cascada: rewrite_llm_config_id (nullable) en
  organización; fallback al LLM del chatbot con max_tokens bajo (~100). Prompt de optimización
  fijo (plantilla en el módulo, no editable por admin en este prompt): "genera la consulta de
  búsqueda autónoma que capture la intención del último mensaje usando el contexto" sobre los
  últimos 10 mensajes.
- Triple fallback (patrón LAMB): excepción → timeout (2 s) → respuesta vacía/anómala ⇒ usar el
  último mensaje del usuario tal cual. El chat NUNCA falla por el rewriting.
- La query reescrita se usa SOLO para retrieval; la generación recibe el historial original.
  Se guarda en el estado del grafo (rewritten_query) → visible en trazas Langfuse y en el
  bypass (RAG.11).

## Config
- query_rewriting_enabled (bool) en HubChatbot + default org + plataforma False (migración,
  cascada, routers CRUD). Default False hasta validar con datos.

## Tests (RED primero) — LLM mockeado
# should_skip_rewriting_on_first_turn
# should_skip_rewriting_when_disabled
# should_rewrite_followup_query_using_history
# should_fallback_to_last_message_on_llm_error
# should_fallback_to_last_message_on_timeout
# should_use_rewritten_query_only_for_retrieval
# should_record_rewritten_query_in_graph_state

## Criterio de done
- [ ] Subconjunto 'conversacional' del dataset dorado (queries con history, RAG.1) evaluado
      con flag ON vs OFF: cifras en el cierre
```

---

### Prompt RAG.11 (RED/GREEN) — Modo bypass/debug del pipeline

**Modelo sugerido**: **Sonnet** — patrón connector `bypass` de LAMB; corto y cerrado.

```
# PROMPT RAG.11 (RED/GREEN) — Prompt final construido sin llamar al LLM
# Deploy: edge

## Endpoint (api/v1/hub_chat.py)
- Body opcional debug_bypass: true. Gate estricto: rol admin/superadmin o PAT con scope
  chat:debug (scope nuevo). El widget/público NUNCA lo recibe (403).
- Con bypass: el grafo ejecuta todo (detect_language → rewrite → retrieve → gate → packer)
  y se detiene ANTES de invocar el LLM. Respuesta JSON (no SSE): {system_prompt, messages,
  packed_context {evidencias, dropped_count}, sources, rewritten_query, resolved_config
  (snapshot de la cascada), quality_gate {score, passed}}. Cero tokens de LLM.
- No persiste HubInteraction (es inspección, no conversación) — decisión cerrada.

## Implementación
- Flag en el estado del CoreGraph; el nodo generate_answer lo comprueba y devuelve los
  mensajes construidos en lugar de invocar (spy-friendly por diseño).

## Tests (RED primero)
# should_return_final_prompt_without_calling_llm      (spy: 0 invocaciones)
# should_include_packed_context_sources_and_resolved_config
# should_include_rewritten_query_when_rewriting_enabled
# should_reject_bypass_for_non_admin_without_scope
# should_not_persist_interaction_on_bypass
# should_report_quality_gate_result_in_bypass

## Criterio de done
- [ ] Verificado manualmente contra el corpus de prueba (una consulta real, salida en el cierre)
- [ ] docs: sección breve en docs/ sobre cómo depurar contexto con bypass
```

---

### Prompt RAG.12 (RED/GREEN) — Progreso granular de jobs de ingesta

**Modelo sugerido**: **Sonnet** — patrón `FileRegistry`/`progress_callback` de LAMB; mecánico.

```
# PROMPT RAG.12 (RED/GREEN) — HubIngestionJob con progreso y estadísticas por etapa
# Deploy: edge

## Esquema (migración Alembic) — HubIngestionJob
- progress_current (int), progress_total (int|null), progress_message (String),
  processing_stats (JSON), processing_started_at / processing_completed_at (DateTime).

## Watcher (ingestion/watcher.py)
- run_job / process_user_upload aceptan progress_callback(current, total, message) y lo
  invocan por etapa: convert (Docling) → chunk → embed (por lote, no por chunk) → persist.
- Throttle: actualizar la fila como máximo una vez por lote/etapa (no por chunk).
- processing_stats al completar (y lo acumulado al fallar): n_chunks, total_chars,
  duración por etapa (ms), n_batches de embedding, embedding_model usado.

## Exposición
- El endpoint de estado de jobs existente (routers de ingesta) devuelve los campos nuevos.
- El CLI de ING.0.2 usa el mismo callback para reportar progreso por consola en cargas masivas.

## Tests (RED primero)
# should_update_progress_per_embedding_batch
# should_record_stage_timings_in_processing_stats
# should_persist_partial_stats_on_failure
# should_expose_progress_fields_in_job_status_endpoint
# should_throttle_progress_writes_per_batch
# should_report_progress_in_bulk_corpus_cli

## Criterio de done
- [ ] Migración aplicada (alembic current)
- [ ] Carga del corpus de prueba mostrando progreso (salida del CLI en el cierre)
```

---

### Prompt RAG.13 (RED/GREEN) — Test scenarios por chatbot (backend + UI admin mínima)

**Modelo sugerido**: **Sonnet** — patrón LAMB test scenarios; CRUD + ejecución por pipeline real + UI enumerada.

```
# PROMPT RAG.13 (RED/GREEN) — Escenarios de prueba con veredicto humano
# Deploy: edge (modelos y ejecución; la UI admin lo consume vía API)

## ORM (operational_models.py — HubOperationalBase, keyed por chatbot_id)
- HubTestScenario: chatbot_id, name, prompt, history (JSON|null), expectation_note (Text|null),
  created_by, timestamps.
- HubTestRun: scenario_id (FK CASCADE), executed_at, answer (Text), sources (JSON),
  bypass_snapshot (JSON|null — captura de RAG.11), verdict ('good'|'bad'|'mixed'|null),
  verdict_note, verdict_by.
- Migración Alembic.

## Endpoints (router nuevo, docstring Deploy: edge, registrado en _register_edge)
- CRUD de escenarios por chatbot (scope admin).
- POST /run: ejecuta el escenario por el PIPELINE REAL (CoreGraph completo, LLM incluido) y
  guarda answer+sources; con ?capture_context=true adjunta además el bypass_snapshot
  (reutiliza RAG.11 internamente).
- PATCH /runs/{id}/verdict: registra el veredicto humano.
- Aislamiento por chatbot_id en toda query (mismo patrón que el resto del módulo).

## UI admin mínima (frontend/src/admin/) — contract-first
- Página por chatbot: lista de escenarios, crear/editar, botón "Ejecutar", historial de runs
  con respuesta + fuentes + (desplegable) contexto capturado, botones de veredicto good/bad/mixed.
- Hooks Orval regenerados desde openapi.json; react-hook-form + zodResolver; i18n es/ca/en
  (ninguna string hardcodeada).

## Tests (RED primero)
# backend — tests/modules/agents_hub/
# should_crud_scenarios_scoped_by_chatbot
# should_execute_scenario_through_real_pipeline     (LLM fake del harness de tests)
# should_capture_bypass_snapshot_when_requested
# should_record_human_verdict_on_run
# should_reject_access_without_admin_scope
# frontend — Vitest
# should_render_scenarios_from_contract
# should_run_scenario_and_show_answer_with_sources
# should_submit_verdict

## Criterio de done
- [ ] Migración aplicada; Orval regenerado; tsc + Vitest verdes
- [ ] Este prompt SÍ genera pruebas manuales (hay UI): .bat según CLAUDE.md al ejecutarlo
```

---

### Prompt RAG.14 (RED/GREEN) — Feedback → huecos de corpus

**Modelo sugerido**: **Opus** — clustering + integración con los contratos 9Q; decisiones de agregación abiertas.

```
# PROMPT RAG.14 (RED/GREEN) — Detección de huecos de contenido desde señales de fallo
# Deploy: edge

## Señales de entrada (ya existen tras RAG.2)
- HubInteraction con feedback_score <= umbral (config del detector, default 2 sobre 5).
- HubInteraction con fallback_reason IN ('quality_gate', 'citation') — la señal gratuita de
  "no encontré nada" que persiste RAG.2.

## Detector (ingestion/quality/gap_detector.py — integra el subsistema 9Q)
- Ventana temporal configurable (default 30 días), por chatbot.
- Embebe las queries de las interacciones-señal (embedding service existente) y clusteriza
  reutilizando las utilidades de clustering de quality/semantic_detector.py.
- Cluster con >= min_cluster_size (default 3) ⇒ HubContentFinding de tipo 'content_gap':
  payload con queries representativas (máx. 5), recuento, rango de fechas y términos top.
  Extensión del contrato/modelo de findings 9Q: finding a nivel chatbot (page_id nullable) —
  migración Alembic + ajuste de contracts.py/findings_repo.py preservando los tests 9Q verdes.
- Deduplicación: no crear finding nuevo si existe uno 'content_gap' abierto cuyo centroide
  esté a distancia coseno < umbral del cluster nuevo (se actualiza su recuento).

## Disparo
- Comando manual (python -m ...quality.detect_gaps --chatbot-id) + endpoint admin POST
  /hub/quality/gaps/analyze. NO se integra en el scheduler periódico 9Q en este prompt
  (el scheduler arranca hoy con detectores vacíos; integrarlo es decisión operativa posterior).
- Los findings aparecen en la cola de revisión 9Q existente del admin.

## Tests (RED primero) — tests/modules/agents_hub/ (unit con embeddings fake deterministas)
# should_collect_low_feedback_interactions_as_signals
# should_collect_citation_and_gate_fallbacks_as_signals
# should_cluster_similar_queries_into_one_gap
# should_ignore_clusters_below_min_size
# should_create_content_gap_finding_with_representative_queries
# should_not_duplicate_open_finding_for_same_cluster
# should_scope_analysis_by_chatbot_and_time_window
# should_keep_existing_9q_finding_tests_green      (regresión de la extensión del contrato)

## Criterio de done
- [ ] Migración aplicada; suite 9Q completa verde tras la extensión del contrato
- [ ] Ejecución del comando contra datos sembrados de prueba (salida en el cierre)
```

### Continuación tras el bloque RAG

Sigue el orden acordado: **Bloque SYNC** → resto del Bloque SEC (SEC.1-5, SEC.7) → Bloque CAL → Deploy GCP. El hook LLM de contextual retrieval nivel 2 y la variante conversacional ampliada del dataset dorado quedan como candidatos post-deploy.

---
