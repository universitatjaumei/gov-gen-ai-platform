## Bloque COR — Un documento, muchos chatbots (❌ DESCARTADO el 2026-08-11, el mismo día que se planificó)

> **Decisión: no se hace.** Los prompts se conservan porque el análisis sirve, pero **no se
> ejecutan**. Motivo del descarte, tras la contraargumentación del usuario:
>
> 1. **La deduplicación casi nunca se dispararía.** COR.2 solo comparte fragmentos cuando
>    coinciden `embedding_model`, `embedding_dim` y `chunking_strategy`. El piloto **varía la
>    estrategia a propósito** para comparar configuraciones, así que se pagaría la migración
>    de la tabla más caliente del sistema por un ahorro que en el caso real no llega.
> 2. **El problema de mantenimiento se resuelve fuera del esquema.** Un solo `.md` en disco y
>    dos cargas apuntando ahí. El reconciliador es incremental por hash, así que una
>    derogación es editar el fichero una vez y ejecutar un comando dos veces — no mantener
>    dos copias a mano.
> 3. **Filas separadas conservan una libertad que se quiere**: cada asistente elige su modelo
>    de embedding, que es exactamente el conmutador que la guarda de RAG.9 existe para hacer
>    seguro. Y admiten `nivell_acces`/`us_assistents` distintos por asistente sin mover la
>    política a una tabla de asociación.
> 4. **El coste de duplicar es pequeño**: decenas de MB de disco y céntimos de embeddings por
>    recarga completa. No compra una migración de esquema y de consultas.
>
> **Dos argumentos de la planificación original eran incorrectos y se anotan como tales**,
> para que nadie los reutilice:
>
> - *«El censo y la poda son de la organización y evaluarlos por chatbot debilita la
>   salvaguarda del 10 %»*: **falso**. Cada corpus se evalúa contra su propio tamaño, que es
>   lo que la salvaguarda quiere decir. Por chatbot es la granularidad correcta.
> - *«Una derogación hay que aplicarla N veces»*: cierto en el sentido literal, pero son N
>   ejecuciones de un comando incremental, no N ediciones. El riesgo que queda es operativo,
>   no de modelo de datos.
>
> ### Lo único que sí queda pendiente de decidir (candidato, 1 prompt)
>
> El riesgo real que la duplicación deja abierto es la **deriva**: que alguien recargue un
> asistente y no el otro, y la misma norma quede con dos contenidos distintos sin que nada
> avise. No necesita migración — es agrupar por `canonical_url` dentro de la organización y
> contar `content_hash` distintos — y encaja en la maquinaria de hallazgos de curación que ya
> existe (junto a `revisio_vencuda` de SYNC.2). **Sin planificar hasta que el usuario lo pida.**

---

> **Origen**: pregunta del usuario el 2026-08-11. Hoy `HubDocument` lleva `chatbot_id` y una
> unicidad `(chatbot_id, content_hash)`: **la misma norma usada en dos chatbots son dos filas,
> dos juegos de fragmentos y dos juegos de embeddings**. El usuario objeta por espacio y, sobre
> todo, por mantenimiento cuando lleguen derogaciones y cambios.
>
> **La objeción de mantenimiento es la que manda, y es correcta.** La de espacio es menor de lo
> que parece: un corpus de 262 documentos ronda los ~60-70 MB de fragmentos por chatbot, que en
> Cloud SQL no es un problema. Lo que sí es un problema es que **una derogación haya que
> aplicarla N veces** y que dos copias de la misma norma puedan divergir sin que nada lo
> detecte — exactamente la avería muda que este proyecto ya ha pagado tres veces.
>
> Hay un argumento estructural más fuerte todavía: el reconciliador de ING.0.5 exige
> `is_census()` para podar porque «la fuente es el corpus COMPLETO». **Eso es una afirmación
> sobre la organización, no sobre un chatbot.** Hoy hay que repetir la operación peligrosa una
> vez por chatbot; con el documento compartido se hace una vez, que es lo que la salvaguarda
> siempre quiso decir.
>
> **Va antes de la primera ingesta real** porque este es el momento más barato en que se podrá
> hacer: no hay corpus en producción, así que la migración de datos es «borrar y recargar» en
> vez de una reescritura con el sistema en marcha.
>
> ### El reparto correcto: qué se comparte y qué no
>
> | Cosa | ¿Compartible? | Por qué |
> |---|---|---|
> | **El documento** (texto, metadatos, vigencia, clasificación) | **Sí, siempre** | Es la norma. No depende de quién la use |
> | **Los fragmentos y sus vectores** | **Solo si coincide la receta** | Un vector de Vertex y uno de BGE-M3 no son comparables aunque midan 1024; y `chunking_strategy` decide qué trozos existen |
> | **La asociación documento↔chatbot** | Es lo nuevo | Cada documento se asocia individualmente a uno o varios chatbots |
>
> **La idea que ordena el bloque: los fragmentos son dato derivado.** Se regeneran del
> documento cuando haga falta. Compartirlos es una optimización; compartir **el documento** es
> una cuestión de corrección. Por eso el bloque hace primero lo segundo.
>
> Nota honesta sobre los dos pilotos: comparten normativa de la UJI, así que **el documento sí
> se deduplica**. Los fragmentos probablemente no, porque el diseño del piloto **varía la
> estrategia a propósito** para comparar. Es el comportamiento correcto, no una carencia.
>
> ### El riesgo real, y por qué se mide antes de migrar
>
> Hoy la consulta vectorial es `WHERE chunk.chatbot_id = X ORDER BY embedding <=> q LIMIT k`:
> igualdad sobre columna indexada, y el HNSW de RAG.3 se usa. Con el documento compartido, el
> subconjunto de un chatbot sale de la tabla de asociación, y eso **mete un filtro más en la
> ruta ANN**. Este proyecto ya midió en DET.1 que tocar esa consulta —añadir un segundo término
> al `ORDER BY`— la degradaba a `Seq Scan + Sort`. No se migra sin ese número.

---

### Prompt COR.0 (SPIKE, medición) — Cuánto cuesta filtrar por asociación en la ruta vectorial

**Modelo sugerido**: **Sonnet** — es medir y reportar; la decisión que habilita está acotada.

```
# PROMPT COR.0 (SPIKE) — El número que decide el diseño de COR.3
# Deploy: edge

## Qué medir, con EXPLAIN ANALYZE sobre Postgres real y datos sembrados
Sembrar ~20.000 fragmentos con embeddings reales de una organizacion, y comparar el plan y
el tiempo de estas cuatro formas de acotar la busqueda vectorial:

  A. `chunk.chatbot_id = :bot`                        (lo de hoy, linea base)
  B. `chunk.organizacion_id = :org`                   (sin subconjunto: el chatbot usa todo)
  C. B + `chunk.document_id IN (SELECT ... WHERE chatbot_id = :bot)`   (subconjunto AMPLIO, ~90 %)
  D. B + lo mismo con subconjunto ESTRECHO (~5 %)

## Qué hay que responder, con el EXPLAIN pegado en el informe
- ¿Sigue usandose `ix_hub_document_chunks_embedding_hnsw` en C y en D, o cae a Seq Scan?
- Con `iterative_scan` de pgvector activado, ¿devuelve C y D los `k` resultados esperados,
  o se quedan cortos? (un ANN filtrado puede devolver MENOS de k sin avisar, que es
  justo el fallo silencioso que este proyecto persigue)
- ¿Cuanto se aleja el recall de D respecto de una busqueda exacta?

## Qué NO hacer aqui
- No migrar nada. No tocar modelos. **Este prompt no cambia el esquema**: escribe
  `docs/MEDICION_CORPUS_COMPARTIDO.md` y nada mas.

## La decisión que habilita
Si C es equivalente a A, COR.3 filtra por asociacion sin mas. Si C se degrada, COR.3 tiene
que llevar el atajo del corpus completo (ver COR.3) y el subconjunto estrecho pasa a ser un
caso con coste declarado, no una sorpresa.
```

---

### Prompt COR.1 (RED/GREEN) — El documento es de la organización, no del chatbot

**Modelo sugerido**: **Opus** — toca la tabla central del corpus, su unicidad y sus índices, y
hay que decidir qué se conserva de la semántica actual en 12 ficheros que la consultan.

```
# PROMPT COR.1 (RED/GREEN) — Una norma, una fila
# Deploy: edge

## Modelo
- `HubDocument.chatbot_id` -> `HubDocument.organizacion_id`.
- Unicidad `(chatbot_id, content_hash)` -> `(organizacion_id, content_hash)`. **Es la que
  hace el trabajo**: dos ingestas del mismo `.md` en la misma organizacion son una fila.
- Tabla de asociacion `hub_document_chatbots (document_id, chatbot_id)`, PK compuesta,
  `ondelete=CASCADE` por los dos lados.
- Los indices `ix_hub_documents_chatbot_*` pasan a `organizacion_*`.
- Migracion Alembic. Los datos de desarrollo se recargan; **no** se escribe migracion de
  datos (ver la nota de COR.6 sobre por que aqui eso es legitimo y no lo sera despues).

## Servicio
- `asociar_documento(document_id, chatbot_id)` / `desasociar_documento(...)`, con la guarda
  de tenencia de SEC.8.1 por los DOS extremos: el documento y el chatbot tienen que ser de
  la organizacion del actor.
- **Desasociar NO borra el documento.** Es la diferencia entre «este chatbot ya no lo usa» y
  «esta norma ya no esta en el corpus», y confundirlas es como se pierde una norma sin que
  nadie lo pida. Borrar el documento es otra operacion, y solo si no le queda ninguna
  asociacion.

## Tests (RED primero)
# should_store_one_document_when_the_same_md_is_ingested_for_two_chatbots
# should_associate_an_existing_document_without_reingesting_it
# should_keep_the_document_when_one_chatbot_is_disassociated
# should_forbid_associating_a_document_of_another_organization   (gate SEC.8.1)
# should_forbid_associating_to_a_chatbot_of_another_organization
```

---

### Prompt COR.2 (RED/GREEN) — Los fragmentos se indexan por receta, no por chatbot

**Modelo sugerido**: **Opus** — decide la clave que define «mismo fragmento» y de ella depende
que la deduplicacion sea correcta o que dos chatbots se lean vectores ajenos.

```
# PROMPT COR.2 (RED/GREEN) — Mismo texto y misma receta, mismo fragmento
# Deploy: edge

## La clave
Un fragmento queda determinado por el documento MAS la receta con que se produjo:
`(document_id, chunk_index, embedding_model, embedding_dim, chunking_strategy)`.
`embedding_model` y `embedding_dim` YA son columnas (MOD.1); falta `chunking_strategy`.

**Sin entidad nueva.** No hay `HubCorpusIndex` ni tabla de recetas: son tres columnas y una
unicidad. Inventar la entidad obligaria a mantenerla sincronizada con la cascada, que es
donde la receta ya vive.

## Modelo
- `HubDocumentChunk.chatbot_id` -> `organizacion_id` (**desnormalizado a proposito**: viene
  del documento y no cambia; sin el, la guarda de espacio vectorial de RAG.9 —que corre en
  CADA consulta— pasaria a ser un JOIN).
- `chunking_strategy` nueva, no nula, con CHECK `('structural','parent_child')` — mismo
  vocabulario que `HubChatbot`, mismo motivo que en RHR.1.
- El indice `ix_hub_document_chunks_embedding_space` pasa a
  `(organizacion_id, embedding_model, embedding_dim, chunking_strategy)`.
- `owner_id` (subidas temporales de usuario) **no se toca**: esos fragmentos son de una
  persona y una sesion, no del corpus, y compartirlos seria una fuga.

## Comportamiento
- Ingerir un documento ya presente **con la misma receta** no re-embebe: asocia.
- Con receta distinta, embebe y guarda un juego nuevo. **Se dice en el log cuantos
  fragmentos se reutilizaron y cuantos se crearon**: si alguien espera compartir y no
  comparte, tiene que verlo, no deducirlo de la factura de embeddings.

## Tests (RED primero)
# should_reuse_chunks_when_the_recipe_matches
# should_create_a_second_set_when_the_chunking_strategy_differs
# should_create_a_second_set_when_the_embedding_model_differs
# should_never_share_a_user_upload_chunk_across_chatbots     (owner_id intacto)
# should_report_how_many_chunks_were_reused
```

---

### Prompt COR.3 (RED/GREEN) — Recuperar el subconjunto del chatbot sin perder el HNSW

**Modelo sugerido**: **Opus** — aplica lo medido en COR.0 a la consulta mas caliente del
sistema; equivocarse aqui degrada cada pregunta de cada usuario.

```
# PROMPT COR.3 (RED/GREEN) — El subconjunto se paga solo cuando existe
# Deploy: edge

## La consulta
`retriever.py` deja de filtrar por `chunk.chatbot_id` y pasa a:
  `organizacion_id = :org` + la receta (3 igualdades sobre el indice de COR.2)
  + el subconjunto del chatbot.

## El atajo, que es la parte importante
`HubChatbot.usa_todo_el_corpus` (bool, default `true`). Cuando es cierto —el caso normal— el
filtro de asociacion **no se anade**, y la consulta tiene exactamente la misma forma que hoy:
igualdades sobre columnas indexadas y el HNSW intacto. Solo el chatbot que de verdad usa un
subconjunto paga el filtro extra, con el coste que COR.0 haya medido.

Es la misma logica que el proyecto ya aplica en otros sitios: no cobrar a todos por una
capacidad que usan pocos.

## Lo que NO se puede romper
- La guarda de espacio vectorial de RAG.9 sigue corriendo por consulta y ahora mira
  `(organizacion_id, modelo, dim, estrategia)`.
- El desempate determinista de DET.1 sigue siendo por `content_hash`, y **sigue aplicandose
  en Python tras el LIMIT en la rama vectorial** — meterlo en el `ORDER BY` es exactamente
  lo que DET.1 midio que inutiliza el indice.
- El filtrado fail-closed de VIS.1 (`nivell_acces`, `us_assistents`) es por documento y no
  cambia de sitio.

## Tests (RED primero)
# should_only_retrieve_chunks_of_documents_associated_to_the_chatbot
# should_not_add_the_association_filter_when_the_chatbot_uses_the_whole_corpus
# should_not_leak_chunks_of_another_organization                (el fallo mas grave posible)
# should_not_retrieve_chunks_embedded_with_another_model        (RAG.9 sigue en pie)
# should_keep_the_deterministic_tiebreak                        (DET.1 sigue en pie)
```

---

### Prompt COR.4 (RED/GREEN) — Ingesta y reconciliación pasan a ser de la organización

**Modelo sugerido**: **Opus** — el reconciliador tiene la salvaguarda de poda, y cambiarle el
ambito mal significa retirar normas que nadie pidio retirar.

```
# PROMPT COR.4 (RED/GREEN) — El censo es de la organizacion, que es lo que siempre quiso decir
# Deploy: edge

- `corpus.load` y el reconciliador de ING.0.5 toman `organizacion_id`, no `chatbot_id`, y
  opcionalmente la lista de chatbots a los que asociar lo cargado.
- La salvaguarda de proporcion de la poda se evalua **una vez sobre el corpus de la
  organizacion**. Hoy se evalua N veces sobre N copias, lo que ademas la debilita: cada
  pasada ve menos documentos y el 10 % es un numero distinto.
- `HubIngestionJob` conserva `chatbot_id` cuando el trabajo nace de un chatbot, pero el
  documento que produce es de la organizacion.
- El puente bilingue y `data_revisio_prevista` (SYNC.2) se calculan una vez por documento.

## Tests (RED primero)
# should_prune_once_for_the_whole_organization
# should_apply_the_proportion_safeguard_to_the_organization_corpus
# should_associate_the_loaded_documents_to_the_requested_chatbots
# should_not_reingest_a_document_already_present_in_the_organization
```

---

### Prompt COR.5 (RED/GREEN) — Asociar documentos a chatbots desde el panel

**Modelo sugerido**: **Sonnet** — pantalla sobre un contrato ya cerrado por COR.1.

```
# PROMPT COR.5 (RED/GREEN) — Elegir que normas ve cada asistente
# Deploy: cloud (panel) sobre endpoints edge

- `DocumentsPage` pasa a listar el corpus **de la organizacion**, con una columna de en
  cuantos chatbots se usa.
- Asociar/desasociar por documento y en lote. **Desasociar avisa de que no borra la norma**,
  y borrar avisa de a cuantos chatbots afecta.
- El interruptor `usa_todo_el_corpus` del chatbot, con su consecuencia explicada: al
  apagarlo hay que elegir documentos.
- i18n es/ca/en. Sin cadenas sueltas.

## Tests (Vitest)
# should_list_the_organization_corpus_not_the_chatbot_one
# should_show_in_how_many_chatbots_a_document_is_used
# should_warn_that_disassociating_does_not_delete
# should_require_choosing_documents_when_the_whole_corpus_switch_is_off
```

---

### Prompt COR.6 (RED/GREEN) — Retirada del camino por chatbot

**Modelo sugerido**: **Sonnet** — retirada verificable con `grep -r` a cero.

```
# PROMPT COR.6 (RED/GREEN) — Que no quede el camino viejo
# Deploy: edge

- `grep -r "HubDocument.chatbot_id"` y `grep -r "HubDocumentChunk.chatbot_id"` a **cero**.
- El dataset dorado (RAG.1) y `run_golden` apuntan a la organizacion.
- `corpus_reclassifier` y `corpus_recalculator` operan por organizacion: reclasificar deja
  de repetirse por chatbot, que era el sintoma de CLAUDE.md §5 —«reclasificar debe costar un
  UPDATE»— multiplicado por N.
- `staleness_detector` y `selection_service` (curacion) revisados: la curacion ya era de la
  organizacion, asi que aqui se alinean en vez de traducir.

## Nota sobre la migracion de datos
COR.1 no escribe migracion de datos porque **no hay corpus en produccion**. Esa excepcion
caduca con la primera carga real: a partir de ahi cualquier cambio equivalente necesita
migracion de datos escrita y probada. Dejarlo dicho aqui para que nadie lea la ausencia como
precedente.
```

---

## Prompt FIX.4 (RED/GREEN) — La carga del corpus embebe con el modelo configurado ✅ HECHO el 2026-08-11

**Modelo sugerido**: **Sonnet** — el mecanismo correcto ya existe (MOD.2); esto es cablearlo
donde no se cableó.

> **Hallazgo del 2026-08-11**, al preparar el bloque DER. **Ejecutado el mismo día**; lo que
> sigue es lo que resultó ser, que era más de lo que el hallazgo decía.
>
> `corpus/load.py` y `corpus/sync.py` construían **`LocalEmbeddingService()` a pelo**,
> contradiciendo MOD.2 —que existe para que el modelo salga de la cascada y no de un
> `import`—. El efecto no era «falla sin el extra», como decía la primera redacción: era que
> **la carga ignoraba la configuración**. Con el extra instalado, el corpus quedaba embebido
> con BGE-M3 aunque el despliegue estuviera configurado con Google, y la guarda de RAG.9 lo
> descubría en la primera consulta de chat — con la ingesta entera ya pagada.
>
> **Y al ejecutarlo apareció algo peor, introducido por D.4.0**: las dos CLIs morían con
> SIGSEGV en Windows. El comentario de cabecera decía que importar `MarkdownChunker` arriba
> forzaba la carga de torch antes de que asyncpg abriera conexión; D.4.0 movió el import de
> `langchain_text_splitters` dentro del constructor del chunker y dejó esa precarga sin
> efecto, **sin que el comentario dejara de afirmar que funcionaba**. La carga del corpus
> estaba rota de punta a punta y nadie lo sabía, porque ningún test ejecuta la CLI.

```
# PROMPT FIX.4 (RED/GREEN) — El corpus se embebe con el modelo del chatbot
# Deploy: edge

- `corpus/load.py` y `corpus/sync.py` resuelven el servicio de embedding **por la cascada
  del chatbot**, como el resto del sistema (MOD.2), en vez de instanciar el local.
- La guarda de procedencia de MOD.1/RAG.9 sigue corriendo: si el corpus ya está embebido con
  otro modelo, se dice antes de escribir, no después.
- Si la cascada resuelve al servicio local y el extra `[local-models]` no está instalado, el
  error de D.4.0 ya explica qué instalar. **No se añade fallback**: elegir otro modelo en
  silencio es exactamente lo que la guarda de espacio vectorial existe para impedir.

## Tests (RED primero)
# should_use_the_embedding_service_resolved_from_the_chatbot_cascade
# should_not_import_the_local_stack_when_the_chatbot_uses_an_api_model
# should_refuse_when_the_corpus_was_embedded_with_another_model
# should_preload_the_splitter_before_touching_the_database   (anadido al ejecutarlo)
```

**Resultado**: 10 tests en `test_corpus_load_embedding_provider.py`. La guarda de espacio
vectorial **se añadió a la carga**, donde no estaba: hasta ahora solo corría en el chat y en
`recalculate-corpus`, así que una carga podía meter un segundo espacio vectorial en un corpus
existente y no se detectaba hasta que alguien preguntaba. Ahora aborta con código 3 antes de
escribir. Y la precarga del splitter pasa a comprobarse con dos tests sobre el AST —presencia
y **orden respecto al import de la conexión de BD**—, porque un comentario no falla cuando
deja de ser cierto.

---
