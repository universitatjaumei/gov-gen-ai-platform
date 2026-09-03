## Bloque VIS — Vistas del fundamento único: recuperación por metadatos (PENDIENTE)

> **Contexto**: implementa los Niveles 0, 1 y 2 de la estrategia (`INFORME_MATERIES_I_METADADES_AGENTS.md` §6.1, `INFORME_ESTRATEGIA_ASISTENTE_GERENCIA.md` §4). Hoy la recuperación filtra **solo** por `chatbot_id`, `is_temporary`/`owner_id` y opcionalmente `language` (`retriever.py:63-71,104-112`); no existe ni un operador JSONB en el código. Sin este bloque, los metadatos de ING.0 son decorativos y el control de acceso por perfil que exige `CRITERIS` §1.4 no es expresable.
>
> **Posición en el orden**: **después de RAG.2**. VIS.2 reescribe `md_agent_selector_pipeline`, que RAG.2 saca de su estado de stub al consolidar los grafos; hacerlo antes sería escribir contra `agent/graph.py`, que RAG.2 elimina.
>
> **Regla del bloque**: todo filtro se aplica **en SQL**, no en Python después del `LIMIT`. El precedente a no repetir es `_get_superseded_doc_ids` (`retriever.py:31-49`), que filtra en memoria tras el `top_k`: los documentos excluidos consumen plazas del resultado en vez de ser reemplazados.

---

### Prompt VIS.1 (RED/GREEN) — Filtro de metadatos en la capa de recuperación

**Modelo sugerido**: **Sonnet** — SQL + contrato de filtro; las decisiones (JOIN, fail-closed) vienen dadas.

```
# PROMPT VIS.1 (RED/GREEN) — Recuperación filtrada por ámbito, submateria y nivel de acceso
# Deploy: edge

## Contrato (services/retrieval/metadata_filter.py)
@dataclass(frozen=True) MetadataFilter:
    ambits: tuple[str, ...] = ()            # ámbito activo + secundarios + 'transversal'
    submateries: tuple[str, ...] = ()       # vacío = sin restringir por submateria
    max_nivell_acces: str = 'public'        # 'public' < 'intern' < 'restringit'
    include_non_canonical: bool = False
    include_superseded: bool = False

## Aplicación en retriever.py (vector_search, keyword_search, hybrid_search)
- JOIN hub_document_chunks → hub_documents por document_id (FK añadida en ING.0.2) y filtro en
  el WHERE, ANTES del ORDER BY / LIMIT.
- ambits: hub_documents.ambit_principal IN (...) OR ambits_secundaris && ARRAY[...]
- submateries: submateries && ARRAY[...] OR submateries_internes && ARRAY[...]
  (el operador && de solapamiento de arrays, que aprovecha el índice GIN de ING.0.2)
- max_nivell_acces: **fail-closed**. Si el nivel del actor no se puede determinar, 'public'.
  Nunca una instrucción al modelo: es filtro de recuperación (CRITERIS §1.4).
- us_assistents != 'no' siempre.
- canonica IS TRUE salvo include_non_canonical (VIS.3).
- Chunks temporales (document_id NULL, subida del propio usuario): NO se filtran por ámbito ni
  submateria — son del actor y ya están acotados por owner_id. Documentarlo y probarlo.

## Las otras dos estrategias, que hoy no filtran NADA
long_context_strategy.py:34-36 y agentic_strategy.py:20-36 seleccionan por chatbot_id (+lengua)
y ya está: ni superseded, ni nivell_acces, ni us_assistents. Un documento derogado se inyecta
entero en MD_LONG_CONTEXT y list_documents lo sigue listando. Ambas pasan a recibir y aplicar
MetadataFilter. Es una fuga de control de acceso, no una mejora de calidad.

## Tests (RED primero) — tests/modules/agents_hub/test_metadata_filter.py
# should_return_only_chunks_of_requested_ambit
# should_include_documents_matching_by_ambits_secundaris
# should_match_submateria_in_submateries_internes
# should_exclude_intern_documents_for_public_actor
# should_default_to_public_when_actor_level_unknown        (fail-closed)
# should_never_return_us_assistents_no_documents
# should_apply_filter_in_sql_before_limit                 (top_k no se degrada; se compara
#                                                          recuento con y sin filtro)
# should_not_filter_temporary_chunks_by_ambit
# should_apply_filter_in_long_context_strategy
# should_apply_filter_in_agentic_index
# should_exclude_superseded_in_all_three_strategies

## Criterio de done
- [ ] RAG.1 ejecutado y comparado con baseline (adjuntar recall@k/MRR)
- [ ] Test de fuga: un actor 'public' no recupera NI UN chunk de documento 'intern' por ninguna
      de las tres estrategias
```

---

### Prompt VIS.2 (RED/GREEN) — Niveles 0/1/2: índice de submaterias, selección e inyección de subconjunto

**Modelo sugerido**: **Opus** — es la pieza con más decisiones embebidas del bloque: qué va al prompt fijo, cómo se selecciona, cómo se degrada cuando no cabe.

```
# PROMPT VIS.2 (RED/GREEN) — El router ve temas, no documentos
# Deploy: edge

## El error que este prompt corrige
RAG.2 deja md_agent_selector_pipeline devolviendo «el índice de documentos» como evidencia
inicial. Medido en el informe: el catálogo de fichas con los campos del router son ~72k tokens
y NO cabe en un system prompt; el índice de las 58 submaterias son 2.307 tokens y sí cabe. El
router no necesita saber qué normas existen: necesita saber qué TEMAS existen.

## Nivel 0 — system prompt fijo (~6k tokens)
- Índice de submaterias desde VocabularyService.build_router_index (ING.0.1), vía ConfigProvider.
- Reglas de rango, vigencia y citación.
- Se integra en la TemplateStrategy del CoreGraph (única fuente del system prompt tras RAG.2).

## Nivel 1 — selección
- El modelo selecciona 1-3 submaterias con el tool list_documents, que se AMPLÍA con el
  parámetro submateries: list[str] (y ámbito implícito del chatbot). No se añade un tool nuevo:
  el índice ya está en el prompt, así que no hace falta un list_submaterias.
- Devuelve las fichas de los documentos de esas submaterias (~1.5k tokens), no su contenido.
- Retroceso escalonado (informe §4.2, la pieza que hace que esto supere a un corpus curado):
  nada encaja → fichas de TODAS las submaterias del ámbito → sigue sin encajar → catálogo global.
  Cada escalón se registra en el debug de la evidencia para poder medirlo.

## Nivel 2 — inyección del subconjunto
- read_document sobre 1-3 documentos, enteros (~25k tokens).
- LongContextRetrievalStrategy deja de significar «todo el corpus del chatbot» y pasa a aceptar
  un MetadataFilter (VIS.1): inyecta el SUBCONJUNTO.
- **Degradación en vez de excepción**: hoy la estrategia lanza ValueError si el corpus pasa de
  128k (long_context_strategy.py:41-46). En producción eso es una caída. Pasa a recortar por
  presupuesto y a marcar la evidencia como truncada, con el recuento de lo descartado.
- Columna context_token_budget (nullable) en HubChatbot + default_context_token_budget en
  HubOrganizacion + default de plataforma en ConfigResolver, misma cascada que el resto.
  **Se crea AQUÍ**, no en RAG.5 (ver enmienda): RAG.5 la consume para su packer.

## Tests (RED primero) — tests/public_graphs/test_vis_levels.py
# should_include_submateria_index_in_system_prompt
# should_keep_level0_index_within_token_order_of_magnitude
# should_list_documents_filtered_by_selected_submateries
# should_fall_back_to_ambit_wide_index_when_nothing_matches
# should_fall_back_to_global_catalog_as_last_resort
# should_record_fallback_level_in_evidence_debug
# should_inject_only_selected_documents_not_whole_corpus
# should_truncate_instead_of_raising_when_over_budget
# should_resolve_context_budget_from_cascade
# should_not_leak_documents_outside_the_actor_filter      (VIS.1 sigue mandando)

## Criterio de done
- [ ] Migración de context_token_budget aplicada y visible en la API admin
- [ ] RAG.1 sin regresión (adjuntar cifras)
- [ ] Traza real de una consulta: submaterias elegidas, documentos inyectados, tokens usados
```

---

### Prompt VIS.3 (RED/GREEN) — Versión canónica bilingüe + advertencia de vigencia no validada

**Modelo sugerido**: **Sonnet** — dos reglas acotadas con efecto directo en la respuesta.

```
# PROMPT VIS.3 (RED/GREEN) — Una versión indexada y una advertencia honesta
# Deploy: edge

## Canónica (informe §6.3)
Medido: 233 fichas en valenciano y 81 en castellano, muchas la misma norma. Hoy el hub las
indexa como documentos distintos coexistiendo por (canonical_url, language)
(watcher.py:116-131) → el mismo contenido ocupa dos plazas del top-k.
- Solo canonica=True entra en la recuperación (VIS.1 ya lo aplica).
- La otra versión es recuperable por id con read_document, vía versio_idiomatica_de, cuando el
  usuario pide la cita literal en la otra lengua.
- El cargador (ING.0.5) enlaza los pares: canonica declarada en el front-matter; si ambas se
  declaran canónicas para el mismo url_oficial, error explícito (no elegir a ciegas).

## Advertencia de vigencia (riesgo nº1 del informe: 312 de 314 fichas dicen «vigent?»)
- Si un documento citado tiene vigencia_validada_el IS NULL, o estat_vigencia distinto de
  'vigent', la respuesta lo DICE. Se implementa en la capa de plantilla/evidencia del CoreGraph
  (flag en EvidenceItem + texto de la TemplateStrategy), NO como frase suelta en el system
  prompt: una instrucción al modelo no es garantía.
- Los documentos derogados (estat_vigencia='derogat') no se recuperan salvo petición explícita
  por id.

## Tests (RED primero)
# should_retrieve_only_canonical_version_by_default
# should_read_language_variant_by_id_on_demand
# should_error_when_two_canonical_versions_share_url
# should_warn_when_cited_document_has_unvalidated_vigencia
# should_not_warn_when_vigencia_is_validated
# should_exclude_derogated_documents_from_retrieval
# should_still_allow_derogated_document_by_explicit_id

## Criterio de done
- [ ] RAG.1 sin regresión; anotar el efecto de la desduplicación bilingüe en el top-k
- [ ] Una respuesta real con la advertencia de vigencia, pegada en el cierre
```

---

### Prompt RAG.15 (NUEVO, RED/GREEN) — El asistente contesta con un solo fragmento

**Modelo sugerido**: **Sonnet** — el defecto está localizado y medido; lo que hay que decidir
después (qué valor de `top_k`) se decide con el dorado delante.

**Objetivo**: `retrieval_top_k` **no lo lee ningún pipeline**. En
`rag_vector_pipeline.py:69` la estrategia se construye así:

```python
return VectorRetrievalStrategy(
    session=deps.session,
    embedding_service=deps.embedder,
    top_k=cfg.min_retrieval_results,      # <- no es retrieval_top_k
    min_score=getattr(cfg, "min_retrieval_score", 0.0) or 0.0,
    reranker=reranker,
)
```

Dos consecuencias, las dos medidas el 2026-08-24 sobre el chatbot `Normativa UJI`:

1. **El asistente responde con UN fragmento.** `min_retrieval_results` valía 1, así que el
   `top_k` efectivo era 1. En el lote ujirag: 25 de 25 respuestas con exactamente una fuente
   antes de tocar nada, y 20 de 20 después. Sobre un corpus de 23.306 fragmentos, la respuesta
   se compone leyendo uno.
2. **`retrieval_top_k` es configuración muerta y editable.** Está en el modelo
   (`config_models.py:386`), en el alta y en la edición del router
   (`hub_chatbots_router.py:66,126,177,324`) y por tanto en el panel: un admin puede cambiar
   un número que no hace nada, y creer que ha ajustado la recuperación.

Y un efecto de segundo orden que confundió el diagnóstico del umbral: como
`top_k == min_retrieval_results`, la comprobación `len(items) >= min_retrieval_results` del
quality gate sólo se cumple cuando se recuperan **exactamente** todos los que caben, y si falta
uno el score se **multiplica por 0,5**. Subir el mínimo no endurecía un mínimo: ampliaba la
recuperación y a la vez hacía más probable el castigo.

```
# PROMPT RAG.15 (RED/GREEN) — top_k es top_k, y el minimo es un minimo
# Deploy: edge

## Cambios
- `_construir_estrategia` pasa `top_k=cfg.retrieval_top_k`. `min_retrieval_results` vuelve a
  ser lo que su nombre dice: el minimo de resultados por debajo del cual el quality gate
  penaliza.
- Revisar los otros pipelines por el mismo error: `md_long_context_pipeline` y
  `md_agent_selector_pipeline` tambien construyen su recuperacion.
- Con el reranker encendido, `pool_size(top_k)` pasa a ser `max(30, top_k*3)`: comprobar que
  el pool sigue siendo razonable con top_k=8 y anotar el coste por consulta del Ranking API.

## Decidir con datos, no de memoria
- El valor de `retrieval_top_k` se elige ejecutando el dorado de RAG.1 y el lote ujirag con
  varios valores, igual que se hizo con el umbral. NO dar por bueno el 8 por defecto sin
  medirlo: se escribio cuando nadie lo leia.
- Con mas contexto por respuesta, el `quality_threshold` de 0,50 —calibrado sobre respuestas de
  un solo fragmento— hay que volver a mirarlo. Los dos numeros se mueven juntos.

## Tests (RED primero)
# should_pass_retrieval_top_k_to_the_strategy
# should_not_use_min_retrieval_results_as_top_k
# should_penalise_only_when_fewer_items_than_the_minimum   (el gate, desacoplado del top_k)

## Cierre
- [ ] Una respuesta del lote ujirag cita mas de un documento cuando la pregunta lo pide
- [ ] Dorado de RAG.1 sin regresion, con las cifras del antes y el despues anotadas
- [ ] `retrieval_top_k` del panel cambia el comportamiento de verdad (probarlo)
- [ ] Reevaluado el umbral tras el cambio, con el lote ujirag delante
```

---

### Prompt VIS.4 (NUEVO, RED/GREEN) — Primero vigente, después lengua

**Modelo sugerido**: **Sonnet** — una regla de prioridad acotada, con el caso de prueba ya
medido.

**Objetivo**: `PreferLanguagePolicy` resuelve bien lo que se le pidió —si no hay evidencia en
la lengua de la pregunta, busca otra vez y acepta la otra lengua— pero **no distingue dos
cosas que en la UJI no son la misma**: que la única versión disponible esté en otra lengua, y
que esté en otro curso académico.

Medido el 2026-08-24 en el corpus real: las directrices académicas de **2026/2027 sólo existen
en castellano** y las de **2025/2026 sólo en valencià**, las cuatro marcadas vigentes y
validadas. Con la política actual, «usa la otra lengua» y «usa una versión anterior» son la
misma acción, y para quien pregunta son cosas muy distintas.

**Decisión del usuario (2026-08-24)**: entre dos versiones de la misma norma manda **primero la
vigente y después la lengua**. Si la vigente sólo existe en la otra lengua, se cita la vigente
y se advierte de la lengua; nunca al revés.

```
# PROMPT VIS.4 (RED/GREEN) — La preferencia de lengua opera DENTRO de la versión vigente
# Deploy: edge

## Regla
- La preferencia de lengua se aplica **entre versiones equivalentes en vigencia**, no entre
  versiones de distinta vigencia.
- Orden: (1) vigente en la lengua de la pregunta; (2) vigente en la otra lengua, con aviso de
  lengua; (3) no vigente en la lengua de la pregunta, con el aviso de vigencia que ya existe;
  (4) el resto.
- No se inventa una jerarquía nueva: `estat_vigencia` y `vigencia_validada_el` ya están en el
  documento y VIS.3 ya los consume.

## Dónde
- `PreferLanguagePolicy` en `strategies/protocols.py`. `StrictLanguagePolicy` no cambia: filtra
  a la lengua del usuario por definición, y ahí la vigencia no compite con nada.

## Tests (RED primero)
# should_prefer_the_current_version_even_if_it_is_in_the_other_language
# should_prefer_the_query_language_between_two_current_versions
# should_warn_about_language_when_only_the_other_language_is_current
# should_not_change_behaviour_when_there_is_a_single_version   (el caso de hoy)

## Nota sobre la medición
Con el corpus actual esta regla **no cambia ningún resultado**, porque cada norma tiene una
sola versión: el emparejamiento bilingüe está incompleto (47 traducciones sin declarar de qué
norma son versión). Empezará a decidir en cuanto entren las que faltan, y por eso conviene
tenerla escrita antes y no después.

## Cierre
- [ ] El lote ujirag sin regresión (20/25 al cerrar el 2026-08-24)
- [ ] Un caso con dos versiones sembradas a mano que demuestre el orden
```

---

### Prompt VIS.5 (NUEVO, RED/GREEN) — El aviso de traducción avisa de lo que no es

**Modelo sugerido**: **Sonnet** — un bug acotado con tres defectos visibles y su redacción.

**Objetivo**: `_build_translation_warning` (`api/v1/hub_chat.py:168`) llega al usuario —el
widget lo pinta— pero **dice lo contrario de lo que hace falta**:

```python
def _build_translation_warning(language: str) -> str | None:
    if not language or language == "es":
        return None
    lang_names = {"ca": "catalan", "en": "ingles", "fr": "frances"}
    return f"⚠️ La pregunta se detecto en {lang_display}. La respuesta puede estar en ese idioma."
```

Tres defectos, cada uno con su consecuencia:

1. **Avisa del idioma de la pregunta, no del de la fuente.** Que alguien pregunte en valencià
   no es una anomalía en la UJI. Lo que hay que decirle es que **la norma que se le cita está
   en castellano**, porque el enlace le va a llevar a un documento en otra lengua.
2. **Se calla si la pregunta es en castellano** (`language == "es"` → `None`). Es justo el caso
   más frecuente del corpus real: 195 de 290 normas sólo existen en valencià, así que preguntar
   en castellano y recibir una norma en valencià es lo habitual — y nunca avisa.
3. **Está redactado en castellano y sin acentos**, y se le muestra a quien acaba de escribir en
   valencià.

```
# PROMPT VIS.5 (RED/GREEN) — El aviso sale de la lengua de la FUENTE
# Deploy: edge

## Cambios
- El aviso se deriva de `context_source_language` —que el CoreGraph ya calcula y ya viaja en
  `translation_warning`— y no de la lengua de la pregunta.
- Se emite siempre que la lengua de la fuente difiera de la de la pregunta, en las dos
  direcciones. Sin la excepción del castellano.
- Redactado en la lengua de la pregunta, con acentos.
- Que el escenario de prueba (`hub_test_scenarios_router`) y el ejecutor del lote lo expongan:
  hoy los dos pasan `translation_warning: False` y el defecto era invisible desde ahí.

## Tests (RED primero)
# should_warn_when_the_source_language_differs_from_the_question
# should_warn_when_asking_in_spanish_and_citing_a_valencian_norm   (el caso que se callaba)
# should_not_warn_when_both_match
# should_write_the_warning_in_the_language_of_the_question

## Cierre
- [ ] Una consulta real en castellano sobre una norma que sólo existe en valencià muestra el
      aviso, con la captura pegada
```

---
