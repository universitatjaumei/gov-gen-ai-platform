## Bloque PIL — Los dos asistentes del piloto: Vertex, corpus real y pruebas en local

> **Planificado el 2026-08-15.** Análisis y decisiones en
> `docs/PLAN_CHATBOTS_E_INGESTA_LOCAL.md`, reescrito el mismo día contra el estado real del
> código y del corpus.

Este bloque deja montados en local, con el corpus normativo de verdad, los **dos asistentes
del piloto**: el **público de normativa** (298 documentos, widget anónimo) y el de
**Gerencia** (124 documentos, personal identificado). Es el ensayo previo al despliegue: lo
que aquí se mida decide umbrales, estrategia de recuperación y tamaño de la máquina.

**Cuatro decisiones tomadas por el usuario el 2026-08-15**, y que este bloque ejecuta sin
volver a preguntarlas:

1. **Los embeddings van por Vertex AI**, con adaptador propio. Es el proveedor del
   despliegue, así que el ensayo se parece a producción y el corpus no hay que re-embeberlo
   después.
2. **Gerencia se prueba en local como `authenticated`** y pasa a `restricted` +
   `allowed_saml_groups` al desplegar. En local no hay IdP; montar uno no aporta a lo que
   esta fase tiene que responder.
3. **El borrado de un chatbot se arregla en código**, no con un `DELETE` a mano: hoy deja
   documentos y embeddings huérfanos, y eso volvería a morder.
4. **El aviso de vigencia desplazada se hidrata antes de las pruebas.** Si no, una respuesta
   con texto desplazado durante el piloto no se puede distinguir de un fallo nuevo.

**Cuatro hallazgos del análisis que este bloque da por ciertos** (verificados contra el
código el 2026-08-15):

- El corpus **ya viene desdoblado en dos paquetes** listos —`generat/ingesta/normatiu` (298
  `.md`) y `generat/ingesta/gerencia` (124 `.md`)—, con `ambit_principal` y `submateries`
  emitidos **en campos reales** en el 100 % de los ficheros. Consecuencia dura:
  `assert_vocabulary` ya no pasa trivialmente y **aborta la ingesta entera** si el
  vocabulario no está cargado antes.
- **No existe adaptador de Vertex.** `GoogleEmbeddingService` habla con la API de AI Studio
  (`GOOGLE_API_KEY`) y `embedding_resolver` solo conoce `google_genai` y `local`.
- **Ningún adaptador por API expone `embed_batch`**, así que el watcher cae a una llamada por
  fragmento: ~21.400 llamadas secuenciales para este corpus.
- **`hub_documents.chatbot_id` no tiene FK** (se cayó con el split edge/cloud), así que
  borrar un chatbot no borra su corpus. Los fragmentos sí cascadean desde el documento.

**Prerrequisitos externos**: ✅ **resueltos el 2026-08-15.** Proyecto `uji-teclab`
(618806480921), facturación activa, `aiplatform.googleapis.com` **ya estaba habilitada**, y
ADC escrito en `%APPDATA%\gcloud\application_default_credentials.json` con `uji-teclab` como
proyecto de cuota. Medidas contra la API real en el cuadro de PIL.1.

`discoveryengine.googleapis.com` **no** está habilitada: es la del Ranking API que necesita
RAG.6b, que va detrás del bloque Deploy. No se habilita hasta que haga falta.

---

### Prompt PIL.1 (RED/GREEN) — Adaptador de Vertex AI para embeddings + lote por API

**Modelo sugerido**: **Opus** — decisión de contrato en la frontera de proveedores, más la
guarda del espacio vectorial, que si se rompe no da error sino resultados malos.

```
# PROMPT PIL.1 (RED/GREEN) — VertexEmbeddingService + embed_batch en los adaptadores por API
# Deploy: shared (services/embedding_*)

## Por qué
El despliegue va a GCP y el corpus se embebe UNA vez: el proveedor con que se ingiera es el
que manda durante toda la vida de ese corpus, porque `assert_embedding_space_matches`
devuelve 409 en cada consulta si no coincide. Hoy el único adaptador por API es el de AI
Studio (clave de API en el entorno), que no es lo que una universidad despliega en su
proyecto de GCP: Vertex autentica con ADC / cuenta de servicio, respeta la región y no
obliga a repartir una clave.

## Medido contra la API real (2026-08-15, proyecto uji-teclab)
No hay que volver a averiguarlo, y dos de estos datos cambian el diseño:

| Qué | Medido |
|---|---|
| Regiones que sirven `gemini-embedding-001` | `europe-southwest1` (Madrid), `europe-west1`, `europe-west4`, `europe-west9` — las cuatro con 1024 dimensiones |
| Tamaño de lote | **250 instancias por petición, sin error**. Probado 1, 2, 16, 64 y 250 |
| ¿La API normaliza a 1024 dim? | **NO.** Norma L2 medida = **0,6225**. Normalizar en el adaptador es obligatorio, y su ausencia NO da error: da un umbral de RAG.5 que compara números incomparables |
| `task_type` | Aceptado: `RETRIEVAL_DOCUMENT` y `RETRIEVAL_QUERY` responden los dos |

**Aviso para quien pruebe a mano desde PowerShell**: `Invoke-RestMethod` de PS 5.1 manda
`Expect: 100-continue` y el endpoint contesta **HTTP 417 con una página anti-bot de Google**,
que se lee como «la región no existe» y no lo es. Se desactiva con
`[System.Net.ServicePointManager]::Expect100Continue = $false`. Costó dar por no disponible
una región que sí lo estaba.

## Alcance 1 — el adaptador
- `VertexEmbeddingService` en `services/embedding_service.py`, junto a los otros dos.
- Modelo por defecto `gemini-embedding-001`, `output_dimensionality=1024`
  (DIMENSION_PLATAFORMA: es lo que permite convivir con BGE-M3 en edge sin migrar la columna
  Vector(1024) ni reconstruir el índice HNSW).
- **Normaliza L2 igual que GoogleEmbeddingService**, y por la misma razón: la API no
  normaliza las dimensiones distintas de 3072, y mezclar vectores normalizados y sin
  normalizar en la misma columna rompe el umbral absoluto de RAG.5.
- Cliente: `langchain_google_vertexai.VertexAIEmbeddings` (dependencia nueva en
  `server/pyproject.toml`). Proyecto y región de `GOOGLE_CLOUD_PROJECT` y
  `GOOGLE_CLOUD_LOCATION`; credenciales por ADC.
- **Región: `europe-southwest1` (Madrid)**, decidida el 2026-08-15. El texto normativo no
  sale de España, que es el argumento que sostiene la frontera edge-cloud ante protección de
  datos. Verificada sirviendo el modelo a 1024 dimensiones. **La región del embedding no
  ata a las demás**: el modelo de chat y el Ranking API de RAG.6b eligen la suya.
- **Sin fallback silencioso**: si falta el proyecto o la credencial, error explícito que diga
  qué falta y cómo se pone. Degradar a local dejaría medio corpus en otro espacio vectorial.

## Alcance 2 — el lote (el que hace la ingesta viable)
- `embed_batch` en `VertexEmbeddingService` y en `GoogleEmbeddingService`, sobre
  `aembed_documents`. Hoy ninguno lo expone y `watcher.py` cae, por `getattr`, a una llamada
  por fragmento: para este corpus son ~15.100 + ~6.300 llamadas secuenciales.
- Trocear la lista antes de llamar: **250 instancias por petición, medido** (arriba). El
  tamaño de lote es constante del módulo, no parámetro de negocio. Con eso, los ~21.400
  fragmentos del piloto caben en ~86 peticiones en vez de 21.400.
- **El orden de salida es el de entrada**, y eso se testea: un lote reordenado asigna
  vectores al fragmento equivocado y NO da error — da respuestas malas.

## Alcance 3 — el propósito del embedding (task_type asimétrico)
Decidido el 2026-08-15, y es lo único de este prompt que toca un protocolo compartido.

- **Al ingerir, `RETRIEVAL_DOCUMENT`; al preguntar, `RETRIEVAL_QUERY`.** Para eso existe el
  parámetro: sin él, el vector de una pregunta y el de un artículo tienen que parecerse por
  casualidad, y en un corpus normativo —donde el ciudadano no usa las palabras de la norma—
  es justo donde más se pierde.
- El protocolo hoy es `embed(text)` / `embed_batch(texts)`, sin noción de propósito. Se le
  añade el propósito **con default explícito**, y `LocalEmbeddingService` lo acepta y lo
  ignora: BGE-M3 no tiene tipos de tarea y no se le va a inventar uno.
- **El propósito viaja con la procedencia del vector** (MOD.1), junto a modelo y dimensiones.
  Sin eso, re-ingerir con otro tipo de tarea corrompe el índice **en silencio**:
  `assert_embedding_space_matches` compara modelo y dimensiones, que seguirían coincidiendo.
  Es el mismo fallo que MOD.1 vino a impedir, un nivel más abajo.
- **Los dos lados o ninguno.** Si la rama de consulta no adopta `RETRIEVAL_QUERY`, ingerir
  con `RETRIEVAL_DOCUMENT` es peor que no hacer nada: se comparan dos espacios distintos sin
  que nadie lo note. El test de extremo a extremo es el que cierra este alcance.

## Alcance 4 — la selección por configuración
- `provider_type = "google_vertexai"` en `embedding_resolver.resolve_embedding_service`.
- `HubProvider` sembrado para Vertex en `database/seeds.py`.
- El mensaje de `EmbeddingProviderNotSupported` enumera los tres tipos soportados.

## Tests (RED primero)
# tests/modules/agents_hub/unit/test_vertex_embedding_service.py
# should_normalize_l2_the_returned_vector
# should_default_to_platform_dimension_1024
# should_fail_with_actionable_error_when_project_missing
# should_split_a_large_batch_into_api_sized_requests      (tope medido: 250)
# should_preserve_input_order_across_batch_boundaries
# should_expose_embed_batch_on_both_api_adapters
# should_send_retrieval_document_task_type_when_ingesting
# should_send_retrieval_query_task_type_when_querying
# should_accept_and_ignore_the_purpose_in_the_local_adapter
# should_record_the_task_type_in_the_vector_provenance
# should_reject_a_corpus_embedded_with_a_different_task_type
# tests/modules/agents_hub/unit/test_embedding_resolver.py (ampliar)
# should_return_vertex_adapter_for_google_vertexai_provider_type
# should_name_all_supported_types_in_the_unsupported_error
# tests/modules/agents_hub/unit/test_embedding_text.py (ampliar)
# should_use_embed_batch_once_per_document_when_adapter_exposes_it

## Criterio de done
- [ ] Suite de `tests/modules/agents_hub` verde
- [ ] `docs/DECISION_MODELOS_EMBEDDING_RERANKER.md` menciona el tercer adaptador y sus
      variables de entorno
- [ ] `.env.example` con GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION=europe-southwest1 y la
      nota de ADC (`gcloud auth application-default login`, NO una clave de API)
- [ ] Ingesta y consulta usan tipos de tarea distintos, verificado de extremo a extremo
- [ ] grep: ningún módulo de negocio importa VertexEmbeddingService directamente (se resuelve
      por configuración, MOD.2)
```

---

### Prompt PIL.2 (RED/GREEN) — Borrar un chatbot se lleva su corpus

**Modelo sugerido**: **Sonnet** — alcance cerrado; la única decisión abierta ya está tomada
en el prompt (qué se borra y qué no).

```
# PROMPT PIL.2 (RED/GREEN) — el borrado de chatbot retira documentos y fragmentos
# Deploy: edge

## Por qué
`DELETE /hub/chatbots/{id}` borra la fila de configuración y nada más.
`hub_documents.chatbot_id` NO tiene FK —se cayó al separar HubConfigBase de
HubOperationalBase— así que el corpus y sus embeddings se quedan en la base sin dueño:
ocupan, contaminan los recuentos y `detectar_divergencias` los sigue viendo. Se descubre
justo al limpiar los chatbots de prueba antes del piloto.

## Qué se borra, y qué NO
- SE BORRA: `hub_documents` del chatbot. Los `hub_document_chunks` caen solos
  (`fk_chunk_document_id` es ON DELETE CASCADE desde ING.0.2).
- NO se borra: `hub_interactions`. Es registro de lo que pasó, no corpus; con RHR.1 encima es
  material de revisión. Un chatbot borrado no reescribe la historia de lo que contestó.
- Todo en la MISMA transacción que el borrado del chatbot: media limpieza es peor que ninguna.

## Alcance
- `hub_chatbots_router.delete_chatbot`: borrado explícito de los documentos antes del
  `DELETE` del chatbot.
- **No se añade la FK cross-base**: la separación de bases es deliberada (CLAUDE.md,
  frontera edge-cloud) y una FK de operacional a configuración la rompería. El borrado es
  explícito a propósito.

## Tests (RED primero) — tests/api/test_chatbots_router.py (ampliar)
# should_delete_documents_and_chunks_when_chatbot_is_deleted
# should_not_delete_documents_of_other_chatbots
# should_keep_interactions_after_chatbot_deletion
# should_delete_in_a_single_transaction   (fallo a mitad -> no deja el chatbot sin corpus)

## Criterio de done
- [ ] `tests/api` verde
- [ ] Verificado en navegador: borrar un chatbot de prueba desde el panel deja
      `corpus-stats` de los demás intacto
```

---

### Prompt PIL.3 (RED/GREEN) — El aviso de vigencia desplazada llega a todos los fragmentos

**Modelo sugerido**: **Opus** — toca el montaje de la evidencia, que es lo que ve el modelo;
equivocarse aquí cambia respuestas sin dar error.

```
# PROMPT PIL.3 (RED/GREEN) — hidratar la nota de vigencia al montar la evidencia
# Deploy: edge

## Por qué (medido por la curación del corpus, 2026-08-10)
45 documentos tienen artículos VIGENTES cuyo contenido está DESPLAZADO por los Estatutos de
2025: el texto se aprobó y nadie lo ha modificado, pero lo que se aplica es otra cosa. El
corpus lo marca con `::: nota-vigencia` dentro del texto del artículo. El problema: un
artículo desplazado se parte en 3-6 fragmentos y la nota cae FÍSICAMENTE en uno de ellos.
De 86 unidades desplazadas, **83 tienen trozos sin el aviso**. Quien recupere uno de esos
trozos contesta un texto que no se aplica, sin ninguna señal.

## La solución, y por qué esta
El corpus da la nota por ancla en el front-matter del documento (`desplacat_per`), y **los
290 fragmentos de unidades desplazadas llevan `desplacat` en `classes`**, caiga donde caiga
el texto. Se hidrata al montar la evidencia:
- No depende de dónde cayó la nota al trocear. Las alternativas sí.
- La nota vive en un solo sitio: reescribirla no obliga a reindexar 290 fragmentos.
- **Es texto de la evidencia, no una instrucción al modelo.** Avisar en el prompt («ojo, este
  artículo puede estar desplazado») es justo lo que CRITERIS §1.4 prohíbe para algo que se
  puede resolver antes de llegar al modelo.
- Descartadas: `parent_child` (cambia el troceado de todo el corpus para resolver 45
  documentos, y solo ayuda si la respuesta se hace con el padre) y propagar la nota al
  trocear (duplica 400-700 caracteres en 290 fragmentos, y esos caracteres entran al
  embedding).

## Alcance
- Al construir el `EvidenceItem`: si `desplacat` está en `classes` del fragmento y el
  `desplacat_per` del documento tiene entrada para su `ancora`, el aviso va DELANTE del texto
  del fragmento.
- Un solo sitio: el mismo camino ha de servir a RAG y a MD_AGENT_SELECTOR. Si hoy son dos
  funciones, se unifica; no se duplica el aviso en dos ramas.
- El aviso nombra la norma que desplaza, su artículo y la fecha — lo que ya trae
  `desplacat_per`. No se redacta nada que el corpus no diga.
- **No toca el troceador ni el texto embebido**: es exclusivamente de lectura, en consulta.

## Tests (RED primero) — tests/modules/agents_hub/unit/test_evidence_vigencia.py
# should_prepend_notice_when_chunk_has_desplacat_class_and_matching_anchor
# should_not_touch_chunks_without_the_class
# should_not_touch_chunks_whose_anchor_has_no_entry
# should_hydrate_every_chunk_of_a_split_displaced_article   (el caso real: 1 de N lo tenía)
# should_name_the_displacing_norm_article_and_date
# should_apply_in_both_rag_and_agent_selector_paths
# should_not_alter_the_text_used_for_embedding

## Criterio de done
- [ ] Tests verdes
- [ ] Verificado tras la ingesta (PIL.6) con un artículo desplazado real: la respuesta lleva
      el aviso venga del fragmento que venga
```

---

### Prompt PIL.4 — Vocabulario cargado y los dos paquetes contra el validador real

**Modelo sugerido**: **Sonnet** — operación guiada; la parte de código es una corrección de
documentación y la guarda ya existe.

```
# PROMPT PIL.4 — vocabulario + puerta de validación de los dos paquetes
# Deploy: edge (operación)

## Prerrequisitos
- Docker arriba y `uv run alembic upgrade head` aplicado.
- UUID de la organización destino (los dos asistentes van a la MISMA: `load.py` aborta si no).

## Alcance
1. Cargar el vocabulario en ese orden —`ambit` PRIMERO, `submateria` DESPUÉS— desde
   `Descarregar_pdf/normativa_propia/vocabulari/`. Un `ambit` padre que falte rechaza el CSV
   de submaterias entero, a propósito. Primero `--dry-run`.
2. Pasar la puerta que en la máquina del corpus NO se puede pasar (allí falta `pydantic`):
   `--dry-run --verbose` de `corpus.load` sobre las dos carpetas. Eso ejecuta
   `LocalDirectorySource` + `assert_vocabulary` de verdad, que es la validación real.
   Debe dar **298 entradas** en `normatiu` y **124** en `gerencia`, sin códigos desconocidos.
3. **Sin `default_source_url`** (la orden ya lo hace así): los 37 documentos sin URL oficial
   caerían todos bajo la misma clave y la guarda VIS.3 los denunciaría como 37 versiones
   canónicas de la misma norma.
4. Corregir `docs/CARGA_VOCABULARIO.md` §«Después de cargar»: dice que los documentos aún no
   emiten `ambit_principal`/`submateries` y que la validación pasa trivialmente. **Ya los
   emiten los 422**, y sin vocabulario cargado la ingesta aborta. Es lo contrario de lo que
   el documento promete a quien lo siga.

## Criterio de done
- [ ] `NN términos leídos` y `creados/actualizados/sin_cambios` en las dos pasadas
- [ ] Los dos dry-run validan sin error, con los recuentos exactos anotados
- [ ] `docs/CARGA_VOCABULARIO.md` corregido
```

---

### Prompt PIL.5 — Crear los dos asistentes con su configuración

**Modelo sugerido**: **Sonnet** — la configuración está cerrada en la tabla; el trabajo es
aplicarla y verificarla en navegador.

```
# PROMPT PIL.5 — alta de los dos chatbots del piloto
# Deploy: cloud (panel) + edge (lo que configuran)

## Antes
- Limpiar los chatbots de prueba anteriores con PIL.2 ya en el árbol, para que se lleven su
  corpus. Anotar cuáles se borran.
- Configurar el proveedor de embeddings: `HubProvider` de Vertex + fila `HubLLMConfig` con
  `purpose='embedding'`, `is_default=true`, `output_dimensionality=1024`.

## Configuración (los dos se crean por el panel, no por SQL: se verifica el panel de paso)

|  | Normativa UJI (público) | Gerència (interno) |
|---|---|---|
| access_mode | public_anon | authenticated (restricted al desplegar) |
| retrieval_mode | RAG | RAG |
| public_graph_profile | PUBLIC_KB_RICH | PUBLIC_KB_RICH |
| chunking_strategy | structural | structural |
| language_mode | prefer | prefer |
| quality_threshold | 0,7 | 0,5 |
| min_retrieval_score | 0,3 | 0,25 |
| min_retrieval_results | 2 | 1 |
| retrieval_top_k | 8 | 8 |
| reranker_enabled | false | false |
| query_rewriting_enabled | false | false |
| anon_ip_daily_token_quota | fijado | — |

- La asimetría de umbrales ES la decisión: ante el ciudadano callar cuesta menos que citar
  mal; ante el funcionario, una pista con su fuente ya sirve y quien lee sabe contrastar.
- `reranker_enabled: false` en los dos porque RAG.6b (Ranking API de Vertex) va DETRÁS del
  bloque Deploy y el reranker local desapareció con D.4.0.
- Credencial de sitio del público: `POST /hub/chatbots/{id}/widget-keys`. **Se muestra una
  sola vez**; sin ella el widget anónimo no abre.
- Anotar los dos UUID: son el `--chatbot-id` de PIL.6.

## Verificación en navegador (el agente, dentro del bloque)
- Los dos aparecen en el panel con los valores guardados (no los defaults).
- El widget público carga con su credencial; sin credencial, no.
- Consola y red limpias.

## Criterio de done
- [ ] Dos chatbots creados, UUID anotados, configuración verificada en la UI
- [ ] Credencial de widget emitida y guardada
- [ ] Chatbots de prueba anteriores borrados, sin documentos huérfanos
      (`SELECT count(*) FROM hub_documents WHERE chatbot_id NOT IN (SELECT id FROM hub_chatbots)` = 0)
```

---

### Prompt PIL.6 — Ingesta de los dos corpus, con medición

**Modelo sugerido**: **Sonnet** — la orden existe y está probada; lo que aporta valor es la
medida, no la decisión.

```
# PROMPT PIL.6 — carga real de los dos paquetes
# Deploy: edge

## Orden (una pasada por paquete: son carpetas distintas y chatbots distintos)
uv run python -m server.app.modules.agents_hub.ingestion.corpus.load \
    --dir <corpus>/generat/ingesta/normatiu --chatbot-id <UUID_PUBLICO> --dry-run --verbose
# y, si sale limpio, la misma sin --dry-run. Luego igual con gerencia.

- **Sin `--census` ni `--prune`** la primera vez. `--prune` sin `--census` no retira nada, y
  es deliberado: una carga parcial no distingue «retirada» de «no incluida».
- Los dos comparten documentos (`gerencia` es un subconjunto por materia, no un corpus
  disjunto): cada uno embebe su copia. Es el precio de que cada asistente elija su modelo, y
  es la razón por la que se descartó el bloque COR.

## Qué medir, y anotarlo en el informe
- Documentos y fragmentos por asistente. Referencia del corpus: ~50 fragmentos por documento
  => ~15.100 en el público y ~6.300 en Gerencia. Una desviación grande es señal, no ruido.
- Tiempo de pared y coste de embedding (~6,8M tokens entre los dos paquetes).
- Que `embed_batch` de PIL.1 se está usando (si no, el tiempo lo canta).
- Las líneas del informe: `+` nuevo, `~` cuerpo cambiado, `= (metadatos)` UPDATE sin
  re-trocear, `- (retirado)` solo con poda.

## Comprobación al terminar
- `corpus-stats` de cada chatbot cuadra con lo cargado.
- Una consulta real devuelve cita con artículo y URL oficial.
- El aviso de deriva entre copias (DER.2) al final de la segunda carga: si aparece, se
  entiende antes de seguir.

## Criterio de done
- [ ] Los dos dry-run limpios antes de escribir nada
- [ ] Dos cargas completadas con recuentos anotados
- [ ] Sin divergencias inesperadas entre los dos asistentes
```

---

### Prompt PIL.7 (RED/GREEN) — Pruebas en local y ajuste con evidencia

**Modelo sugerido**: **Opus** — es donde se decide si la configuración vale; requiere leer
respuestas reales y atribuir los fallos a la pieza correcta.

```
# PROMPT PIL.7 — batería de pruebas del piloto
# Deploy: edge

## 1. Escenarios de prueba (RAG.13), sembrados desde el corpus
- `PREGUNTES_GERENCIA.md` del repositorio del corpus son preguntas reales de gestión
  económica: es el dorado de Gerencia, no hay que inventarlo.
- Para el público, `preguntes_tipus` del front-matter (las trae cada documento) da preguntas
  con su norma esperada.
- **No sembrar el dorado desde el texto de las FAQ**: la entrada sería circular, porque el
  documento que contiene la frase la recupera siempre. Ya se descartó en FAQ.2.

## 2. Verificación en navegador (el agente)
- Widget público con su credencial: pregunta con respuesta esperada, pregunta sin fuente
  (tiene que decir que no sabe, no improvisar), y una en castellano sobre norma valenciana
  (el puente léxico `despesa/gasto` del tsvector).
- Panel de Gerencia con usuario identificado: pregunta de procedimiento, una que dé con la
  FAQ, y un artículo DESPLAZADO —el aviso de PIL.3 tiene que salir venga del fragmento que
  venga—.
- `read_console_messages` y `read_network_requests` limpios en las dos superficies.

## 3. Ajuste con evidencia, no a ojo
- Los umbrales de PIL.5 son un punto de partida razonado, no medido. Se mueven con el dorado
  delante: cuántas preguntas caen al fallback por umbral y cuántas contestan con fuente
  floja.
- **Comparación RAG vs MD_AGENT_SELECTOR en Gerencia**: es una columna del chatbot, no una
  reingesta. Con 124 documentos el índice de submaterias cabe en ~2.300 tokens, y el
  front-matter trae `resum_router` y `preguntes_tipus` escritos justo para que un encaminador
  decida. Se mide con el mismo dorado y se decide con el número.
- `query_rewriting_enabled` en el público: candidato claro (el ciudadano no usa las palabras
  de la norma) pero añade latencia y una llamada. Se mide antes de encenderlo.

## 4. Cierre
- Informe con cifras reales, no estimadas.
- `pruebas_manuales_bloquePIL.bat` SOLO con lo que el agente no puede verificar: juicio sobre
  la calidad de las respuestas normativas, identidad visual del widget y lectura con lector
  de pantalla.

## Criterio de done
- [ ] Escenarios cargados y ejecutados en los dos asistentes
- [ ] Recorrido en navegador completo, con evidencia (URL, texto encontrado, consola)
- [ ] Umbrales ajustados con la medida delante, y el porqué escrito
- [ ] Decisión sobre el modo de recuperación de Gerencia, con el número que la sostiene
- [ ] `.bat` generado en ANSI sin BOM
```

---
