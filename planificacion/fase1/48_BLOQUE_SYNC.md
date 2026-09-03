## Bloque SYNC — Sostenibilidad de la vigencia del corpus (PENDIENTE)

> **Contexto**: planificado el 2026-07-28. Cierra la pregunta de mantenimiento: quién actualiza el corpus cuando una norma cambia, y cómo se evita que envejezca en silencio. La decisión de fondo ya está tomada en el Bloque ING.0: **el `.md` autoritativo vive en la BD de publicación de la UJI y las circulares de Gerencia pasan por el mismo circuito**, así que hay un solo maestro y el hub es réplica.
>
> **Lo que este bloque NO construye**: UI de administrador con formulario de metadatos. Con un solo maestro no hace falta, y CLAUDE.md prohíbe el código especulativo. La carga manual de emergencia la cubre el CLI de ING.0.5.
>
> **Transporte disponible (dato del 2026-07-28)**: la UJI expone sus datasets por un **servicio MCP** (`execute_dataset`, argumentos `dataset_code` + `token` por dataset). El corpus normativo se publicará por esa vía o por un export incremental equivalente.
>
> **Este bloque añade un transporte, no un pipeline.** El pipeline de publicación no existirá hasta dentro de meses; hasta entonces el mantenimiento del corpus se hace por **CLI sobre carpeta local**, que es lo que entrega ING.0.5 junto con el reconciliador y el protocolo `CorpusSource`. SYNC.1 implementa una **segunda fuente** (`PublicationMcpSource`) sobre ese mismo reconciliador. Si SYNC.1 acaba reimplementando emparejamiento, deltas o poda, está mal: eso ya está en ING.0.5.

---

### Prompt SYNC.1 (RED/GREEN) — Fuente MCP sobre el reconciliador de ING.0.5

**Modelo sugerido**: **Sonnet** — cliente + adaptador de fuente; la reconciliación (censo, poda, emparejamiento) ya viene decidida e implementada en ING.0.5.

```
# PROMPT SYNC.1 (RED/GREEN) — Pull del corpus autoritativo, sin agente y sin borrar
# Deploy: edge  (el edge node tira del sistema de publicación del cliente; el cloud no ve el corpus)

## Regla número uno: esto es ETL, no una operación agéntica
El sync NO pasa por un LLM en ningún punto: un script llama a la tool, recibe texto, calcula
hash y escribe. Consecuencias que hay que respetar en el código:
- Cero tokens de modelo, cero trazas Langfuse en esta ruta.
- El token del dataset viaja como ARGUMENTO de la tool. Si esta llamada se hiciera desde un
  agente con trazas activas, el token quedaría escrito en el almacén de trazas. Va en variable
  de entorno / secreto, no se registra en logs ni en el informe de ejecución (redactar si se
  vuelca la petición para depurar).

## Cliente (ingestion/corpus/publication_client.py)
- Cliente MCP sobre HTTP (JSON-RPC) para la tool execute_dataset(dataset_code, token).
- Dos datasets, y esta es la decisión que hace el coste proporcional a los cambios y no al corpus:
  * ÍNDICE (censo completo): una entrada por norma con id estable, content_hash | updated_at y
    el bloque de metadatos. Pequeño; se pide entero y a menudo.
  * CONTENIDO: el .md. Solo se pide para las normas cuyo hash cambió. Si la tool no admite
    parámetros (hoy solo dataset_code + token), la variante es un dataset de "modificadas en los
    últimos N días"; el diseño de reconciliación es el mismo.
- Guardarraíl de tamaño: el corpus completo ronda los ~10 MB (≈380 normas × ~25k caracteres),
  que está en la zona de los límites de respuesta de una Lambda. Si la respuesta llega truncada
  o no parsea, **fallar ruidosamente**; nunca sincronizar con un censo parcial (produciría
  despublicaciones falsas).
- Configuración por entorno, añadida a .env.example y a scripts/generate_env.sh (precedente
  SEC.6): PUBLICATION_MCP_URL, PUBLICATION_DATASET_INDEX, PUBLICATION_DATASET_CONTENT,
  PUBLICATION_DATASET_TOKEN.

## Adaptador de fuente (ingestion/corpus/publication_source.py)
PublicationMcpSource implementa CorpusSource (ING.0.5):
- is_census() → True **solo** si la pasada obtuvo el índice completo. Si se usó el dataset de
  "modificadas en los últimos N días", es False, y entonces el reconciliador no poda: correcto,
  porque un delta no puede distinguir "retirada" de "no tocada".
- list_entries() → mapea el índice a CorpusDocumentEntry, con id_publicacio del registro.
- read_body() → pide el dataset de CONTENIDO solo para las entradas que el reconciliador marcó
  como cambiadas (lazy, no precargar el corpus).
Toda la semántica de emparejamiento, deltas, poda, salvaguarda de proporción, findings y
HubIngestionJob viene de ING.0.5 y **no se reimplementa aquí**. La retirada detectada por censo
usa motiu_exclusio='retirada_de_la_font' (mismo valor que el CLI): despublicada ≠ derogada, y la
distinción la hace una persona en la cola de revisión.

## Disparo
- CLI (python -m ...corpus.sync --chatbot-id [--dry-run] [--prune]).
- NO se engancha al scheduler en este prompt (decisión operativa posterior, igual que RAG.14).

## Tests (RED primero) — tests/modules/agents_hub/ingestion/test_publication_sync.py
# should_call_execute_dataset_with_code_and_token
# should_never_log_the_dataset_token
# should_fail_loudly_on_truncated_or_unparseable_index
# should_report_is_census_true_only_for_full_index
# should_report_is_census_false_for_delta_dataset
# should_map_index_entries_to_corpus_document_entries_with_id_publicacio
# should_request_content_only_for_changed_documents      (spy: nº de llamadas al dataset de contenido)
# should_reuse_reconciler_without_reimplementing_matching  (el sync no toca hub_documents
#                                                           directamente; lo hace el reconciliador)
# should_not_emit_llm_calls_during_sync                  (spy sobre model_factory)
+ los tests de reconciliación de ING.0.5 se ejecutan también con esta fuente (parametrizar el
  test del reconciliador por CorpusSource: carpeta local y MCP fake deben dar el mismo resultado).

## Criterio de done
- [ ] Ejecución real contra el entorno de pruebas de la UJI (o fake fiel si aún no publica el
      dataset del corpus), con el informe de recuentos pegado en el cierre
- [ ] La suite del reconciliador pasa con ambas fuentes
- [ ] Crawler confirmado desactivado para el chatbot sincronizado (fuente autoritativa única)
```

---

### Prompt SYNC.2 (RED/GREEN) — Caducidad activa del corpus

**Modelo sugerido**: **Sonnet** — detector corto sobre el mecanismo de findings ya existente.

```
# PROMPT SYNC.2 (RED/GREEN) — Que nada envejezca en silencio
# Deploy: edge

## El problema
Hoy un documento cargado se queda indefinidamente y nada avisa. El riesgo nº1 del informe es la
vigencia (312 de 314 fichas dicen «vigent?»), y el sync solo detecta lo que cambia en origen: una
norma que nadie toca durante tres años no genera ninguna señal.

## Detector (ingestion/quality/staleness_detector.py)
- Lee data_revisio_prevista (columna de ING.0.2). Vencida ⇒ HubContentFinding de tipo
  'revisio_vencuda' a nivel documento, con la fecha prevista y la última de actualización.
- Default de la fecha al ingerir, si el front-matter no la trae: 1 año. Las normas de vigencia
  anual (Presupuesto) la traen explícita y más corta.
- Deduplicación: no se emite un finding nuevo si hay uno abierto para el mismo documento.
- Los findings caen en la cola de revisión 9Q existente del admin, junto a los 'content_gap' de
  RAG.14 y las 'despublicada' de SYNC.1.

## Disparo
CLI (python -m ...quality.detect_stale --chatbot-id) + endpoint admin. Sin scheduler (igual que
RAG.14 y SYNC.1).

## Tests (RED primero)
# should_emit_finding_for_document_past_its_review_date
# should_not_emit_for_document_within_review_window
# should_default_review_date_to_one_year_on_ingest
# should_respect_explicit_review_date_from_frontmatter
# should_not_duplicate_open_finding_for_same_document
# should_keep_existing_9q_finding_tests_green

## Criterio de done
- [ ] Ejecución contra datos sembrados con fechas vencidas y vigentes (salida en el cierre)
- [ ] La cola de revisión del admin muestra los tres tipos de finding
```

---
