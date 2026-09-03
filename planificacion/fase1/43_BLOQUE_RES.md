## Bloque RES — Que el asistente responda (PENDIENTE, va ANTES de Deploy)

> **Contexto**: al cerrar RAG.15 se midió la anchura y el resultado fue inaceptable, y lo dijo el
> usuario con el criterio correcto: **«no resulta aceptable un sistema que no contesta a casi la
> mitad de las preguntas»**, y **«todas las preguntas que he hecho deberían encontrar respuesta en
> el corpus»**. Lo segundo se comprobó por SQL y es cierto: los documentos están. Diagnóstico
> completo en `docs/DIAGNOSTICO_POR_QUE_NO_CONTESTA.html`.
>
> **Hay dos defectos independientes y `retrieval_top_k` no es ninguno de los dos.** Medido el
> 2026-08-25 sobre los dos chatbots, con 25 y 7 consultas reales:
>
> | `top_k` | 1 fuente (25 / 7) | media de todas, hoy | **mejor fragmento** |
> |---|---|---|---|
> | 2 | **6 / 5** | 20 / 4 | 20 / 4 |
> | 3 | 3 / 1 | 19 / 3 | **20 / 4** |
> | 5 | 0 / 0 | 18 / 2 | **20 / 4** |
> | 8 | 0 / 0 | 15 / 2 | **20 / 4** |
>
> La columna del mejor fragmento es **plana**: con esa política la anchura deja de decidir si se
> contesta. Y **`top_k=2` no es la salida** aunque la primera fila lo sugiera: contesta lo mismo
> con 6 de 25 y 5 de 7 respuestas de **fuente única**, que es el defecto que RAG.15 acababa de
> corregir. Un *suelo relativo al mejor* se probó y **da peor** (19 en vez de 20, y recorta el
> contexto hasta reintroducir fuentes únicas): descartado con datos, no por opinión.
>
> **Orden del bloque, y es el orden por el que está numerado**: la puerta primero porque no cuesta
> llamadas al modelo y ya recupera 2 y 2; el escalón de reformulación después porque **sólo se paga
> cuando la puerta falla** (28% de las consultas en Normativa, 71% en Gerencia); la expansión
> léxica en tercer lugar porque **su materia prima la produce el escalón** —cada reformulación que
> rescata una pregunta es, exactamente, el par que hay que aprender—; y la anchura al final, cuando
> ya no dependa de dos mandos a la vez.
>
> **Modelo sugerido siguiente**: RES.1 **Sonnet**, RES.2 y RES.3 **Opus**, RES.4 y RES.5 **Sonnet**.
>
> **RES.5 se añadió el 2026-08-25, cerrando RES.2, y no estaba previsto.** Al medir apareció que el
> contrato de citas descarta respuestas **correctas** cuando el modelo nombra la norma en prosa en
> vez de emitir un enlace: REAL-07 con nota 0,626 —la puerta la dejó pasar— y
> `fallback_reason = "citation"`. Va al final del bloque y **empieza por medir la frecuencia**,
> porque es intermitente y puede terminar en «no se hace».

### Lo que este bloque NO hace

- **No baja ningún umbral.** Con la puerta arreglada, `quality_threshold` cambia de significado y
  hay que volver a mirarlo con datos; bajarlo antes sería tapar el síntoma. La decisión sobre el
  0,35 del `economicoadministratiu` queda **pendiente del usuario** y anotada en `PROJECT_STATE.md`.
- **No arregla el pipeline agéntico.** `md_agent_selector_pipeline` asigna `score = 1.0` fijo, así
  que su puerta no rechaza nada con ninguna política. Que eso esté bien o mal es una pregunta
  distinta y va con la validación de Gerencia.
- **No cablea `needs_secondary_search`.** RES.2 construye una segunda pasada por *reformulación*;
  la segunda pasada por *lengua* que `LanguagePolicy` declara sigue sin llamarse desde el grafo.
  Mezclar las dos razones en un nodo es como se consigue un nodo que nadie entiende. Queda
  registrado como deuda, no resuelto de tapadillo.
- **No reindexa nada.** La expansión léxica vive en `bilingual_terms`, que alimenta el `tsvector`;
  el texto que se embebe no se toca, y eso lo vigila el guardarraíl que ya existe.

---

### Prompt RES.1 (RED/GREEN) — La puerta puntúa con el mejor fragmento, no con la media

**Modelo sugerido**: **Sonnet** — el cambio está en una función, la decisión ya está medida y las
consecuencias están enumeradas abajo.

**Objetivo**: `core_graph.merge_node` calcula la nota que decide si hay respuesta como **media de
todas** las puntuaciones:

```python
scores = [i.score for i in items if i.score is not None]
avg = sum(scores) / len(scores) if scores else 0.5
count_ok = len(items) >= self.cfg.min_retrieval_results
score = avg if count_ok else avg * 0.5
```

Consecuencia: **la cola vota sobre si hay respuesta**, y ampliar la búsqueda baja mecánicamente la
nota. Dos casos medidos que lo retratan:

- `SGE-01` (créditos por ser miembro del Claustro): mejor fragmento **0,637**, media **0,371**,
  umbral 0,50 → se rinde. La evidencia estaba y la enterró el promedio.
- `REAL-07` (dieta con ingresos externos): mejor **0,626**, media **0,327**, umbral 0,35 → se rinde.

**Cambio**: la nota es la del **mejor** fragmento. La penalización por número de resultados se
queda como está, porque responde a otra pregunta.

```
# PROMPT RES.1 (RED/GREEN) — La puerta pregunta si hay UNA fuente buena
# Deploy: edge

## Cambio
- En `merge_node`, la nota del gate pasa a ser `max(scores)` en vez de la media.
- La penalizacion `len(items) < min_retrieval_results -> nota * 0.5` NO se toca: mide otra cosa
  (cuantos resultados hay), y desacoplarla del top_k fue justo lo que arreglo RAG.15.
- `items` vacio sigue dando 0.0, y `scores` vacio con items presentes sigue dando el 0.5 de
  cortesia que ya habia: son dos casos distintos y ya estaban distinguidos.
- La traza debe decir **cual** fragmento fijo la nota (titulo y puntuacion). Sin eso, depurar una
  respuesta rechazada pasa de leer un numero a reproducir la consulta.

## Lo que este cambio significa, y hay que escribirlo donde se lea
- `quality_threshold` CAMBIA DE SIGNIFICADO: pasa de «mis fuentes son buenas de media» a «tengo
  al menos una fuente buena». Un admin que puso 0,35 lo puso con el significado viejo.
- Por tanto: actualizar el texto de ayuda del campo en el panel y su docstring en el modelo, y
  anotar el cambio en `docs/DEPURAR_CONTEXTO_RAG.md`.
- NO se ajusta ningun umbral en este prompt. Con el mejor fragmento los umbrales actuales dan
  20/25 y 4/7, que es mejor que hoy en los dos casos: no hay nada que compensar todavia.

## Por que no otras politicas (medido, no supuesto)
- `media de 3` y `mediana`: 18/25 y 2/7. No mejoran.
- Suelo relativo al mejor (0,6 y 0,75) y luego media: 19/25, y recorta el contexto hasta
  reintroducir respuestas de fuente unica. Descartado.
- `top_k = 2`: contesta igual pero con 6/25 y 5/7 de fuente unica.

## Tests (RED primero)
# should_score_the_gate_on_the_best_fragment
# should_not_let_the_weak_tail_lower_the_score
#     scores [0.637, 0.30, 0.29, 0.28] con umbral 0.5 -> PASA (hoy falla con media 0.374)
# should_still_penalise_when_fewer_items_than_the_minimum
# should_keep_zero_when_there_are_no_items
# should_record_which_fragment_set_the_score

## Cierre
- [ ] Lote ujirag: de 18 a 20 respuestas de 25, con las dos cifras anotadas
- [ ] Bateria de Gerencia: de 2 a 4 de 7
- [ ] Dorado de RAG.1 sin regresion
- [ ] Ninguna respuesta nueva apoyada en una sola fuente (comprobado, no supuesto)
```

---

### Prompt RES.2 (RED/GREEN) — Segunda búsqueda con la consulta reformulada, sólo cuando la primera falla

**Modelo sugerido**: **Opus** — cambia la topología del grafo, necesita una guarda contra bucles,
un prompt nuevo que no existe y una decisión sobre qué se le cuenta al usuario.

**Objetivo**: no existe normalización de la consulta en la primera pregunta, y **no es un flag
apagado**. `query_rewriting_enabled` está en `t` en los tres chatbots, pero:

```python
def necesita_reescritura(habilitado: bool, historial: list[str]) -> bool:
    return bool(habilitado) and len(historial or []) >= 2
```

La reescritura se diseñó para resolver referencias de seguimiento («i si és a l'estranger?»), así
que en una primera pregunta **no se ejecuta nunca**. Medido: `rewritten_query` fue `None` en las 14
ejecuciones de la batería de Gerencia.

El efecto es de vocabulario. Una pregunta redactada como **intención** se busca tal cual contra un
corpus redactado como **norma**, y no comparten ni una palabra clave —así que ni el vector se
parece ni la rama léxica tiene de dónde agarrarse—. Sonda del 2026-08-25, reformulando a mano al
vocabulario de la norma:

| Pregunta | Mejor, tal cual | Mejor, reformulada |
|---|---|---|
| Compra de un equipo de 6.500 € | 0,126 | **0,640** |
| Contratar un servicio de 6.500 € | 0,172 | **0,643** |
| Requisitos de los contratos menores | 0,354 | **0,775** |
| Portátil / equipo de alta gama | 0,157 | 0,267, pero **acierta el documento** |

La prueba interna de que es vocabulario y no corpus: `REAL-02` («quin és el límit d'un contracte
menor?») **sí se contesta**, porque usa las palabras de la norma; `REAL-04`, que es la misma materia
dicha como intención, puntúa 0,126.

> **Advertencia que hay que arrastrar a este prompt**: esas reformulaciones las escribió el agente
> **conociendo el corpus**. Los 0,64 son un **techo**, no lo que dará un reformulador automático.
> El criterio de éxito del prompt es la mejora medida, no llegar a esa cifra.

```
# PROMPT RES.2 (RED/GREEN) — Si la puerta rechaza, reformula y busca otra vez
# Deploy: edge

## Topologia
- Hoy: retrieve -> merge -> quality_gate -> {generate_answer | fallback}.
- Nueva rama: quality_gate -> reformular -> retrieve -> merge -> quality_gate -> {generate | fallback}
- Guarda contra bucles: un campo de estado (`ya_reformulado`) que el gate consulta. La segunda
  pasada NO puede pedir una tercera. Sin la guarda esto es un bucle infinito con coste por vuelta.
- El bypass de depuracion (RAG.11) sigue mandando: si esta activo, el gate informa y no desvia,
  asi que tampoco dispara la reformulacion.

## El prompt de reformulacion es NUEVO
- `PLANTILLA` de `query_rewriter.py` NO sirve tal cual: esta escrita para resolver pronombres y
  referencias con el turno anterior. Aqui no hay pronombres que resolver.
- Lo que hace falta es otra tarea: **pasar de como lo dice una persona a como lo dice la norma**.
  Vive en el mismo modulo, junto a la que ya hay, y tampoco es editable por el admin: es una
  instruccion de maquina, y exponerla convierte un fallo de recuperacion en una consulta de
  soporte.
- Se mantienen las dos reglas que ya rigen la reescritura, y por los mismos motivos:
  (1) el chat NUNCA falla por esto -> excepcion, timeout o respuesta anomala => se usa la
      consulta original y se sigue; (2) la reformulacion NO llega a la generacion.
- Reutilizar `get_rewrite_model`, que ya existe con tope de 100 tokens para devolver una linea.

## Coste, que es el argumento de este diseno
- Se paga SOLO cuando la primera pasada no llega al umbral: medido, el 28% de las consultas de
  Normativa y el 71% de las de Gerencia. Normalizar siempre costaria una llamada en el camino
  critico de todas.
- Anotar el coste real por consulta rescatada al cerrar, para poder decidir despues si conviene
  adelantar la normalizacion a la primera pasada.

## Que se le cuenta al usuario
- La segunda busqueda es **silenciosa**: no se le hace esperar dos veces con un mensaje en medio.
- Pero el hecho **se expone en el contrato** (`reformulada: bool` en la respuesta y en el
  `HubTestRun`), porque el frontend decide como mostrarlo y porque una respuesta rescatada
  reformulando no se revisa igual que una directa.
- El texto que vea el ciudadano es decision de producto y NO se cierra aqui.

## Lo que este prompt NO hace
- No cablea `needs_secondary_search` de `LanguagePolicy`. Existe, tiene tests y el grafo no lo
  llama: es una segunda pasada por LENGUA, que es otra razon. Se deja anotado.

## Tests (RED primero)
# should_not_reformulate_when_the_first_pass_passes
# should_reformulate_once_and_only_once            (la guarda contra bucles)
# should_answer_with_the_evidence_of_the_second_pass
# should_fall_back_when_both_passes_fail
# should_never_send_the_reformulation_to_the_generator
# should_not_break_the_chat_when_the_rewrite_model_fails      (timeout y excepcion)
# should_not_reformulate_in_debug_bypass
# should_expose_that_the_answer_came_from_a_reformulation

## Cierre
- [ ] Bateria de Gerencia: cuantas de las 5 mudas se rescatan de verdad, con el numero real y
      **sin compararlo con el techo de la sonda manual**
- [ ] Lote ujirag: cifras antes y despues, y cuantas consultas dispararon la segunda pasada
- [ ] Latencia medida en los dos casos: consulta que pasa a la primera y consulta rescatada
- [ ] Ninguna respuesta contiene la consulta reformulada
```

---

### Prompt RES.3 (RED/GREEN) — Expansión léxica: el candidato lo produce el fallo, la persona sólo aprueba

**Modelo sugerido**: **Opus** — tabla nueva con ámbito de multitenencia, invariante de proyección
derivada, y el diseño de la cosecha de candidatos.

**Objetivo**: que el sistema aprenda el vocabulario de sus usuarios sin pagar una llamada al modelo
por consulta, y **sin repetir el intento que ya fracasó**. Para el chatbot anterior se pidió a los
servicios que generaran lotes de preguntas y respuestas en hojas Excel y no funcionó. El motivo
importa para el diseño: aquel método pedía **inventar** pares en frío, que es trabajo cognitivo alto
y sin recompensa visible. Aquí el candidato no lo inventa nadie y a la persona sólo se le pide
**aprobar o rechazar** — el mismo giro que hizo funcionar la curación del corpus.

**El hueco ya existe y ya está cableado.** `hub_document_chunks` tiene una columna
`bilingual_terms`, y `tsv` es una columna **generada**:

```python
tsv = Computed(
    "to_tsvector(CASE WHEN language = 'es' THEN 'spanish'::regconfig ELSE 'simple'::regconfig END, "
    "coalesce(content, '') || ' ' || coalesce(bilingual_terms, ''))", persisted=True)
```

Es decir: escribir términos ahí es un `UPDATE`, el índice GIN se regenera solo y **no hay que
volver a calcular embeddings**. Es exactamente el «reclasificar cuesta un `UPDATE`» del contrato del
proyecto.

**Y la materia prima la produce RES.2 gratis.** Cada vez que el escalón de reformulación rescata una
pregunta, deja un par: lo que escribió la persona y la consulta que **sí funcionó**, ya validada por
el hecho de haber funcionado. Eso es el candidato, con su documento asociado.

```
# PROMPT RES.3 (RED/GREEN) — Del fallo al termino, con una persona en medio
# Deploy: edge (la proyeccion) + cloud (la revision)

## Modelo de datos
- Tabla nueva de pares lexicos en `HubConfigBase`, con `__ambito__ = "organizacion"` (lo exige
  MT.1 y el guardarrail lo caza si falta).
- Campos minimos: `organizacion_id`, `document_id`, `termino_de_usuario`, `termino_normativo`,
  `estado` (propuesto | aprobado | rechazado), `origen` (reformulacion | manual), `vigent`,
  `substituit_per_codi`, `revisado_por`, `revisado_el`.
- Se sigue la forma que ya tiene `hub_vocabulary_terms` —vocabulario como DATO, con `vigent` y
  `substituit_per_codi`— y por el mismo motivo: renombrar y fusionar sin migracion.
- PROHIBIDO expresar los terminos como Enum de Python o CheckConstraint. Son datos.

## Invariante: bilingual_terms es DERIVADO
- `bilingual_terms` se calcula **solo** a partir de los pares aprobados, y se puede regenerar
  entero desde la tabla. Nadie lo edita a mano.
- Sin esto, en seis meses nadie sabe de donde salio un termino ni como quitarlo, y volvemos a
  «reindexar» lo que deberia costar un UPDATE.
- Un par que pasa a `rechazado` o a `vigent = false` desaparece de la proyeccion en la siguiente
  regeneracion. Reversible por construccion.

## La cosecha
- Origen 1: los pares que deja RES.2 al rescatar una consulta (consulta original, reformulacion
  que funciono, documento que respondio).
- Origen 2: `hub_interactions` con `fallback_reason` puesto o `review_verdict` negativo — las
  preguntas que fallaron de verdad. Las columnas del bucle YA existen: `feedback_score`,
  `feedback_text`, `review_verdict`, `review_note`, `review_by`, `review_at`.
- El modelo propone el par **en lote y fuera del camino critico**, nunca durante una consulta.
- La pantalla de revision reutiliza el patron de la curacion: lista de propuestas, aprobar o
  rechazar, y nada mas. No se pide redactar.

## Lo que NO se toca
- El texto que se embebe. La taxonomia y el lexico NUNCA entran en `embedding_text`: solo va
  contexto estructural. Ya hay guardarrail; este prompt tiene que seguir pasandolo.
- El vocabulario de ambitos y submaterias (`hub_vocabulary_terms`): es clasificacion, no sinonimia.
  Son dos cosas distintas y comparten forma, no tabla.

## Tests (RED primero)
# should_declare_the_scope_of_the_new_table
# should_propose_a_pair_from_a_failed_question_and_its_working_reformulation
# should_not_apply_a_pair_until_a_person_approves_it
# should_project_only_approved_pairs_into_bilingual_terms
# should_regenerate_the_projection_from_the_table_alone     (derivado, no editado a mano)
# should_drop_a_rejected_pair_from_the_projection
# should_never_put_the_lexicon_into_the_embedded_text
# should_retrieve_the_document_after_approving_the_pair     (el end-to-end de REAL-04)
# should_scope_pairs_to_the_organizacion                    (no se filtran entre organizaciones)

## Cierre
- [ ] Con los pares de la bateria de Gerencia aprobados, medir cuantas de las mudas se recuperan
      **sin** la segunda pasada de RES.2 — que es el objetivo: quitar llamadas al modelo
- [ ] Regenerar la proyeccion desde cero y comprobar que da el mismo `bilingual_terms`
- [ ] Guardarrail del texto embebido en verde
- [ ] `docs/MULTITENENCIA.md` actualizado con la tabla nueva (lo exige el test de MT.7)
```

---

### Prompt RES.4 (medición) — Y ahora sí, la anchura y el umbral

**Modelo sugerido**: **Sonnet** — las herramientas de medida ya están escritas; esto es ejecutarlas
y leerlas.

**Objetivo**: cerrar el bloque midiendo lo que hasta ahora no se podía medir sin ruido. Con la
puerta desacoplada de la anchura, `retrieval_top_k` vuelve a decidir **una sola cosa** —cuánto
contexto entra— y entonces su valor se elige por calidad de la respuesta.

Los guiones están hechos y viven en `_local/golden/`: `diagnostico_puerta.py` (rejilla, sin llamadas
al modelo), `comparar_topk_respuestas.py` (comparación ciega con juez y doble vuelta) y
`bateria_gerencia.py` (variantes para validación humana).

```
# PROMPT RES.4 (medicion) — Elegir la anchura cuando ya solo significa una cosa
# Deploy: —

## Medir
- Rejilla de `diagnostico_puerta.py` con la puerta nueva, en los dos chatbots.
- `comparar_topk_respuestas.py` con 3, 4 y 5, con juez y doble vuelta intercambiando el orden.
  La doble vuelta NO es opcional: en la tanda del 2026-08-25, 6 de 25 veredictos se dieron la
  vuelta al invertir el orden, y con una sola vuelta se habria reportado un ganador inexistente.
- Reevaluar `quality_threshold` en los dos chatbots, ahora que significa «tengo una fuente buena».
  Incluida la decision pendiente sobre el 0,35 del `economicoadministratiu`.

## Y regenerar la bateria de Gerencia
- La hoja de validacion (`docs/VALIDACION_GERENCIA_AUTONOMA.html`) esta hecha y **el usuario
  decidio esperar a enviarla**: hoy 5 de sus 7 preguntas muestran «no contesta» en tres de las
  cuatro variantes, y eso no se puede validar.
- Regenerarla con la configuracion resultante del bloque, y entonces enviarla.

## Cierre
- [ ] Valor de `retrieval_top_k` elegido con las cifras delante, en los dos chatbots
- [ ] Umbrales reevaluados y la decision del 0,35 resuelta
- [ ] Cuantas de las 32 consultas reales quedan sin respuesta, una por una y con su causa
- [ ] Hoja de validacion regenerada y lista para enviar
```

---

### Prompt RES.5 ✅ EJECUTADO Y CERRADO SIN IMPLEMENTAR (2026-08-25) — Una respuesta correcta que no cita en formato no es una respuesta inventada

> ✅ **Paso 1 hecho: 96 ejecuciones (3 tandas × 32 consultas), 85 pasaron la puerta y
> `citation` no aparece ni una vez.** Los 11 rechazos son todos de la puerta. Aplicando la regla
> acordada —el paso 2 se implementa si hay al menos un descarte cuya respuesta mencione el título
> literal de un documento recuperado—, hay cero, así que **no se implementa**. El paso 3 estaba
> aplazado por diseño.
>
> **Lo que la cifra NO dice es «no pasa nunca».** Cero en 85 es compatible con una tasa real de
> hasta el **4,4%**, y el caso se observó una vez —REAL-07 con `top_k=5`— antes de cerrar RES.4.
> Queda como **línea base** para repetirlo con tráfico del piloto sobre
> `hub_interactions.fallback_reason`, que es donde el dato saldrá gratis y con intervalo estrecho.
>
> **Hipótesis de por qué ya no aparece, y es hipótesis**: RES.4 dejó `retrieval_top_k = 3`, o sea
> menos URLs compitiendo en el contexto, y citar una bien es más fácil. REAL-07 responde ahora en
> las tres tandas con nota 0,626 estable, cuando antes aparecía y desaparecía.
>
> **Verificación del propio instrumento, porque hacía falta**: se comprobó aparte que el producto
> SÍ registra el descarte —una respuesta que cita con corchetes y sin URL da `fallback_used=True`
> y `motivo='citation'`—, así que el cero sale de la contabilidad del producto y no de la ausencia
> de contabilidad. La sonda dejó 3 registros de 96 que no se pudieron reconciliar con el estado
> final; no afectan a la cifra, porque la cifra se lee de `fallback_reason` y no de la sonda, pero
> quedan anotados: **la clasificación de motivos de esa sonda no es de fiar** y habría que
> depurarla antes de usarla para decidir algo.

**El prompt original queda abajo tal cual, para cuando el piloto dé la tasa.**

**Modelo sugerido**: **Sonnet** — el defecto está localizado y el prompt lleva la decisión escrita;
lo único abierto es si merece la pena, y eso lo contesta la medición del primer paso.

**Objetivo**: el contrato de citas descarta respuestas **correctas** cuando el modelo nombra la
norma en prosa en vez de emitir un enlace markdown. Encontrado el 2026-08-25 cerrando RES.2, en la
consulta REAL-07 del `economicoadministratiu` («com es justifica una dieta d'un curs amb ingressos
externs?»): nota de calidad **0,626** —muy por encima del umbral de 0,35, o sea que la puerta la
dejó pasar— y `fallback_reason = "citation"`.

Lo que había escrito el modelo, capturado espiando `enforce_citation_contract`:

> «...les factures corresponents (a les quals es refereix **l'article 8 del mateix reglament**)...»

Y las tres URLs que se le permitían citar estaban ahí y eran las correctas: el `REGLAMENT SOBRE
INDEMNITZACIONS PER RAÓ DEL SERVEI` con su ancla `#art-17`, el DOGV y el BOE. **No citó mal: no
citó en el formato que el contrato sabe leer.**

El arreglo del 2026-08-24 sigue en su sitio y funciona —`degradar_anclas` reescribe al documento la
cita cuyo ancla no reconoce—. Lo que queda intacto son las dos cosas que el propio docstring
declara: citar un documento que nunca se recuperó, y **no citar nada**. Este caso es el segundo, y
el contrato no puede distinguirlo de una respuesta inventada porque sólo mira enlaces
`[texto](url)`.

> ⚠️ **Es intermitente y no se sabe cuánto pasa.** La misma consulta, repetida, sí citó y pasó. Y
> el trabajo de citas del 2026-08-24 dejó los descartes en **0 sobre 25**. Por eso el primer paso
> de este prompt es medir.
>
> **Corrección del 2026-08-25, decisión del usuario: el listón NO es un porcentaje.** La versión
> anterior ponía «< 2% ⇒ no se hace», y al preguntarse si debía ser 4% o 5% salió que **la medición
> no puede distinguir esas cifras**. Tres tandas dan ~84 respuestas que pasan la puerta, y con esa
> muestra el intervalo de confianza al 95% de **cero** eventos llega hasta el **4,4%**; el de cuatro
> eventos (4,8%) va de 1,9% a 11,6%. Para separar el 2% del 5% harían falta ~25 tandas (700
> respuestas). Poner el listón en cualquier punto de ese rango es elegir entre números que el dato
> no resuelve — y con un listón del 5%, observar 4 descartes diría «no implementar» cuando la tasa
> real podría ser del 11%.
>
> Y había un segundo defecto en aquella redacción: **un solo listón para dos pasos con costes muy
> distintos**. Se sustituye por dos reglas, cada una a la altura de lo que cuesta su paso.
>
> Hay además una asimetría que empuja: un descarte no es cosmético, es un **«no tengo información
> suficiente» falso** cuando el sistema sí la tenía y sí había redactado bien. Es la misma cosa que
> el usuario declaró inaceptable al 40%; al 2-5% le toca a uno de cada 20-50.

```
# PROMPT RES.5 (medicion -> RED/GREEN) — Primero medir cuanto pasa, y solo despues arreglarlo
# Deploy: edge

## PASO 1 — Medir la frecuencia. Sin esto no se implementa nada.
- Ejecutar el lote ujirag (25) y la bateria de Gerencia (7) **tres veces cada uno**, contando
  cuantas respuestas caen con `fallback_reason == "citation"` **teniendo nota por encima del
  umbral** — que es el caso que interesa: la puerta dijo si y el contrato dijo no.
- Distinguir los dos motivos, porque piden arreglos distintos:
  (a) no hay ningun enlace markdown en la respuesta;
  (b) hay enlaces pero ninguno resiste ni la degradacion al documento.
- Anotar tambien cuantas veces el modelo NOMBRA un documento recuperado en prosa (titulo literal),
  que es lo que decide si el paso 2 sirve para algo.

## Las dos reglas de decision (sustituyen al liston del 2%, que no era medible)
- **Paso 2 — criterio CUALITATIVO, no estadistico.** Se implementa si aparece **al menos un**
  descarte cuya respuesta mencione el titulo literal de un documento recuperado: o sea, prueba de
  que el mecanismo disparia. Cuesta ~20 lineas, cero llamadas al modelo, cero latencia, y es la
  misma forma que `degradar_anclas`, que ya existe y ya se confia en ella. Con ese coste, el lado
  malo de equivocarse es despreciable y el bueno es que alguien reciba una respuesta real en vez de
  un «no lo se» falso. Pedirle un porcentaje a un cambio de veinte lineas es pedir precision que la
  muestra no da para tomar una decision que no la necesita.
- **Paso 3 — APLAZADO a datos del piloto.** El reintento si merece un liston de verdad —rama nueva
  del grafo, guarda contra bucles, llamada extra y espera justo donde el usuario ya esperaba—, y
  84 muestras no pueden darlo. `hub_interactions.fallback_reason` **ya registra el motivo**, asi que
  cuando el piloto tenga trafico una consulta sobre unos miles de conversaciones dara la tasa con
  un intervalo estrecho y sin coste. Hasta entonces NO se implementa el paso 3: se anota la cifra
  de las tres tandas como linea base y se deja la consulta escrita para repetirla con datos reales.

## PASO 2 — Enlazado determinista (segun la regla de arriba)
- Si la respuesta menciona **literalmente** el titulo de un documento recuperado, se convierte esa
  mencion en enlace a su URL antes de evaluar el contrato.
- Es el mismo criterio que `degradar_anclas` y por eso es seguro: **no acepta un puntero vago,
  crea uno verificable**. El documento SI se recupero y SI se leyo.
- Coste cero: ni llamadas al modelo ni latencia.
- Limite conocido y aceptado: solo dispara cuando el titulo aparece tal cual. Si el modelo escribe
  «el reglamento de indemnizaciones» en vez del titulo completo, no lo caza — y arreglar ESO seria
  emparejamiento difuso, que es otra cosa y con otro riesgo.

## PASO 3 — Un reintento, y uno solo — APLAZADO, no descartado
- **No se implementa en este prompt.** Queda escrito para cuando el piloto de la tasa real.
- Diseño acordado, para no volver a decidirlo: si tras el enlazado sigue sin haber cita valida, se
  regenera **una vez** con la instruccion de citas reforzada y se vuelve a evaluar; si tampoco,
  entonces si, fallback. Misma forma que RES.2 y por el mismo motivo —se paga solo cuando falla—,
  con guarda contra bucles, y la instruccion reforzada se añade delante de `CITATION_RULES`, no la
  sustituye.
- Ataca la causa real: el modelo olvido el formato, no el contenido.
- Condicion para retomarlo: tasa medida sobre trafico real del piloto, con intervalo estrecho, y
  que el paso 2 no haya bastado.

## Lo que este prompt NO hace, y son decisiones, no olvidos
- **No adjunta las fuentes y conserva la respuesta.** Es la opcion facil y la peor: pone una lista
  de fuentes plausible debajo de afirmaciones que no estan atadas a ninguna en concreto. Fabrica la
  apariencia de respaldo, y la medicion del 2026-08-25 dijo que en este corpus una cita segura y
  equivocada cuesta mas que una respuesta corta (`curso_caducado` en 15 de 25 escenarios).
- **No acepta referencias en prosa como cita.** «El articulo 8 del mismo reglamento» no es un
  puntero verificable, y producir punteros verificables es para lo que existe el modulo.
- **No toca las dos guardas que se quedan**: citar un documento no recuperado sigue siendo rechazo,
  y una respuesta sin ninguna fuente localizable sigue siendo rechazo.

## Tests (RED primero) — solo del paso 2; los del 3 llegan cuando llegue el 3
# should_link_a_literal_title_mention_to_its_document
# should_not_link_a_title_that_was_never_retrieved
# should_not_touch_an_answer_that_already_cites_correctly
# should_prefer_the_anchor_url_when_the_document_has_one
# should_keep_rejecting_a_citation_to_a_document_never_retrieved
# should_keep_rejecting_an_answer_with_no_locatable_source

## Cierre
- [ ] La cifra del paso 1, con las tres tandas y los dos motivos separados, anotada como **linea
      base** para repetirla con trafico del piloto
- [ ] Cuantas respuestas recupera el enlazado determinista, y con **cero** llamadas extra al modelo
- [ ] Ninguna respuesta nueva cita un documento que no se recupero (comprobado, no supuesto)
- [ ] La consulta sobre `hub_interactions.fallback_reason` escrita y guardada, para el paso 3
```

---
