# Bloque HIB — madurar el asistente para el piloto con informadores, y elegir configuración con lo que las 25 consultas pueden decidir

> **Reescrito el 2026-08-26**, después de ejecutar HIB.0 y de revisar la literatura
> (`docs/LITERATURA_ASISTENTES_NORMATIVA.html`, 43 trabajos, 9 a texto completo). La primera
> versión de este bloque se escribió leyendo el código deprisa y **dos de sus prompts tenían la
> premisa equivocada**; lo que sigue está reordenado por lo que la medición y lo publicado
> sostienen, no por lo que parecía.
>
> **Para qué sirve este bloque, dicho por el usuario**: a los informadores ya se les ha pedido
> ayuda varias veces, así que el piloto tiene que llegarles **suficientemente maduro como para
> que compense el esfuerzo de afinarlo**. Eso ordena la lista: los defectos que se VEN van antes
> que las métricas que no se ven.
>
> **Qué pueden decidir las 25 consultas y qué no.** Son un instrumento para **elegir entre
> configuraciones** —comparaciones A/B sobre las mismas preguntas—, no un certificado de
> calidad. Son casi todas de la Unitat d'Orientació: estudiantado, matrícula y becas. No hay
> nada de Gerencia, de personal ni de contratación. Cualquier cifra absoluta que salga de aquí
> se reporta como lo que es.

## Dos premisas caídas, para que nadie las reintroduzca

- **«El contrato tira respuestas por las remisiones»**: falso. Basta UNA cita válida para pasar.
  El defecto real, medido con la sonda, era el modelo citando en prosa sin URL. Lo arregló HIB.0.
- **«El agéntico no consulta los embeddings»**: falso. `AgenticRetrievalStrategy.get_agent_tools`
  expone `search_knowledge`, que embebe la consulta y llama a `hybrid_search`. Sus fragmentos no
  son peso muerto. Lo que sigue roto es otra cosa: `score = 1.0` fijo.

---

### Prompt HIB.A (MEDICIÓN) — ¿El reranker suma o resta? Ablación con y sin

**Modelo sugerido**: **Sonnet** — no hay diseño que decidir: se ejecuta la batería dos veces y se
comparan las dos salidas con el instrumental que ya existe.

**Objetivo**: damos por bueno que el reranker mejora, y sobre eso se apoyan el umbral, la puerta
de calidad y la asimetría RAG-contra-agéntico que hemos documentado. **LegalBench-RAG midió lo
contrario** con un reranker comercial de uso general sobre texto jurídico: peor que no usarlo,
atribuido a que no entiende el dominio [4]. Nuestro caso no es idéntico —Vertex Ranking entiende
valenciano y devuelve scores ya en [0,1]— pero es una pieza del camino crítico que **nadie ha
medido aquí**.

**Va primero porque bloquea al resto**: recalibrar umbrales sobre un reranker que resta es
calibrar ruido.

```
# PROMPT HIB.A (MEDICION) — La pieza del camino critico que nadie ha medido
# Deploy: edge

## Que se ejecuta
- La bateria de 25 sobre `Normativa UJI`, con el corpus con padre, en dos variantes:
  `reranker_enabled = true` (la de hoy) y `reranker_enabled = false`.
- Juez a ciegas con doble vuelta contra la rubrica del informador, igual que en RES.4.

## La trampa que hay que declarar, y no es menor
Sin reranker la nota NO esta en la misma escala: es la fusion RRF normalizada
(`min(1.0, score / RRF_MAX_SCORE)`), y con reranker es la del propio reranker en [0,1]. Por
tanto **«cuantas contesta» NO es comparable entre las dos variantes**: el umbral significa cosas
distintas en cada una. Lo comparable es:

1. **Que documentos vuelven** — solapamiento de los conjuntos recuperados por consulta, y si el
   documento que el informador esperaba esta dentro. Esto es recuperacion pura y es lo que la
   ablacion viene a medir.
2. **Que respuesta se redacta** — el juez, sobre las que ambas contestan.

Si solo se compara el recuento de respuestas, se estara midiendo el cambio de escala.

## Criterio de decision, escrito ANTES de ver el resultado
- Si sin reranker **entra el documento esperado en igual o mas consultas** y el juez no lo
  prefiere con reranker: se apaga, y se recalibra el umbral sobre la escala RRF.
- Si con reranker gana en cualquiera de los dos ejes: se queda, y queda medido por primera vez.
- Si empatan: se queda, porque es el que ya esta calibrado, y se anota que no aporta lo que
  creiamos.

## Criterio de done
- [ ] Las dos tandas guardadas en `_local/golden/`
- [ ] Solapamiento de documentos recuperados por consulta, no solo el recuento de respuestas
- [ ] Veredicto del juez con la doble vuelta y su tasa de desacuerdo
- [ ] La decision tomada segun el criterio de arriba, y anotada con su cifra
```

---

> **Ampliado el 2026-08-26 (segunda vez), con HIB.A cerrado.** El reranker se apagó por
> medición, y apagarlo cambió dos cosas más que nadie pidió (ver HIB.J). Además, el bloque sólo
> dejaba listo el asistente de Normativa; el usuario quiere abrir **también** el piloto de
> Gerencia, se use o no para el artículo. Lo que sigue: ajustes a HIB.B–HIB.F, y diez prompts
> nuevos (HIB.G–HIB.P) en dos ramas. **Orden de ejecución recomendado al final del bloque.**

### Prompt HIB.B (RED/GREEN) — La reformulación no se emite como si fuera la respuesta

**Modelo sugerido**: **Opus** (antes Sonnet) — la revisión del 2026-08-26 encontró dos decisiones
que el prompt daba por hechas: qué nodos pueden emitir tokens, y cómo se «sustituye» algo que
ya viajó por SSE. Ver «Ajuste» dentro del prompt.

**Objetivo**: es el defecto **más visible** de todos, y por eso sube: quien pruebe el piloto y
haga una pregunta que la puerta rechace ve una línea suelta en castellano —la consulta
reformulada— en vez del mensaje de «no tengo fundamento». Reproducido el 2026-08-26 en la base:
pregunta sobre conservación de expedientes → respuesta `plazo de conservación expedientes
contratación menor`, `fallback_reason = quality_gate`.

```
# PROMPT HIB.B (RED/GREEN) — Al usuario solo le llegan los tokens de la respuesta
# Deploy: edge

## Cambio
- Filtrar `on_chat_model_stream` por `event["metadata"]["langgraph_node"]`: solo se emiten los
  tokens de `generate_answer`.
- El mensaje de rendicion se emite SIEMPRE que haya `fallback_answer`, sustituyendo lo que
  hubiera llegado antes, no solo cuando no llego nada.
- `assistant_message` guarda lo mismo que vio el usuario: hoy guarda la reformulacion.

## Por que no se noto antes
Antes de RES.2 el modelo de reescritura casi nunca corria: `necesita_reescritura` exige dos
turnos previos. RES.2 lo puso en el camino del 28% de las consultas de Normativa.

## Ajuste del 2026-08-26 (2): dos decisiones que el prompt daba por hechas

1. **La lista de nodos que emiten tokens no se escribe a mano.** Filtrar por
   `langgraph_node == "generate_answer"` enmudece cualquier otro nodo que genere la respuesta
   (long-context, agentico, los que vengan). Paso 0: inventariar en `core_graph.py` que nodos
   producen la respuesta final; la lista permitida se DERIVA del grafo (misma regla que P1 del
   marco: un catalogo escrito en un prompt diverge del sistema en el primer cambio), y un test
   se pone rojo cuando aparece un nodo generador sin declarar.
2. **Por SSE no se retira lo ya enviado.** «Sustituir lo que hubiera llegado antes» no es
   implementable solo en el servidor. Con el filtro de nodos puesto, el unico camino en que
   llegan tokens y luego hay rendicion es el **contrato de citas**, que corre despues de
   generar. Decision que hay que tomar en el prompt, con recomendacion:
   - **(recomendada)** retener los tokens de `generate_answer` hasta que el contrato pase, y
     emitir de golpe la respuesta o la rendicion. Una sola fuente de verdad, sin tocar el
     contrato SSE que RAG.2 fijo por snapshot. Precio: latencia percibida en la primera
     palabra; medirla.
   - alternativa: evento nuevo de descarte en el contrato SSE + cambio en el widget. Mas
     complejo y toca un contrato con snapshot.

## Tests (RED primero)
# should_not_stream_tokens_from_the_rewrite_model
# should_derive_the_allowed_nodes_from_the_graph
# should_fail_when_a_generating_node_is_not_declared
# should_emit_the_no_answer_message_even_if_other_nodes_streamed
# should_store_what_the_user_saw

## Criterio de done
- [ ] Verificado en el widget del sitio del corpus con una consulta que la puerta rechace
- [ ] La decision sobre la retencion tomada y escrita, con la latencia a primera palabra medida
```

---

### Prompt HIB.C (RED/GREEN) — El seguimiento conserva el contexto de la pregunta anterior

**Modelo sugerido**: **Opus** — hay que decidir cuándo una pregunta es continuación, y eso es
diseño.

**Objetivo**: el segundo defecto más visible, y el que más va a aparecer en un piloto, porque un
informador prueba **conversando**, no lanzando preguntas sueltas. `necesita_reescritura` exige
**dos turnos previos**, así que en el segundo turno no actúa. Caso real del 2026-08-26:
«requisitos para la mención de doctorado internacional» → «¿hacen falta requisitos adicionales
para el acto de defensa?» → contesta con **tesis confidenciales y cotutela**.

```
# PROMPT HIB.C (RED/GREEN) — Una repregunta es una repregunta desde el primer turno
# Deploy: edge

## Cambio
- `necesita_reescritura` pasa a exigir **un** turno previo, no dos.
- Se paga una llamada al modelo de reescritura en cada turno que no sea el primero. Medir el
  coste real antes de darlo por bueno.

## La trampa a evitar
No mezclar esto con la reformulacion de RES.2, que responde a otra pregunta —la primera consulta
no encontro nada— y tiene su propia plantilla y su propio plazo. Son dos mecanismos con dos
razones; fundirlos es como se consigue un nodo que nadie entiende.

## Ajuste del 2026-08-26 (2)
- **Depende de HIB.B.** Este prompt lleva la reescritura de un 28% de las consultas a casi
  todos los turnos no iniciales; si entra antes que HIB.B multiplica el defecto mas visible.
  El orden ya es el bueno; queda escrito para que un reordenamiento no lo rompa.
- **Una repregunta autocontenida no se toca.** Con un solo turno previo, el caso comun pasa a
  ser la pregunta que no necesita antecedente; reescribirla introduce deriva. Test nuevo.
- **El criterio de coste se escribe antes de medir**: se acepta hasta +N ms de latencia mediana
  y +M tokens por turno. **Fijado por el usuario el 2026-08-26: N = 800 ms, M = 400 tokens.**
  Si se supera, se reporta y se decide; no se da por bueno en silencio.

## Tests (RED primero)
# should_rewrite_the_query_on_the_second_turn
# should_not_rewrite_on_the_very_first_question
# should_not_change_a_self_contained_follow_up
# should_keep_the_subject_of_the_previous_turn

## Criterio de done
- [ ] El caso del doctorado internacional, reproducido y verde
- [ ] Coste medido sobre el lote de HIB.G contra el criterio escrito
```

---

### Prompt HIB.D (RED/GREEN) — Las citas del agéntico abren el artículo, no el documento

**Modelo sugerido**: **Sonnet** — alcance cerrado, **si el defecto existe**.

**Objetivo**: se cree que el pipeline agéntico cita `canonical_url` sin ancla. **Este prompt
empieza comprobándolo en el código**, no dándolo por bueno: dos de los prompts de la primera
versión de este bloque partían de una lectura rápida y estaban equivocados. Si el defecto no
existe, el prompt se cierra sin cambios y eso es un resultado.

Por qué importa más de lo que parece: la literatura sobre exceso de confianza dice que quien usa
un chatbot muestra **más seguridad incluso cuando acierta menos**, y que los descargos apenas lo
corrigen [33]. El ancla al artículo exacto es lo que convierte la verificación en un clic; es
mecanismo, no adorno.

```
# PROMPT HIB.D (RED/GREEN) — El ancla tambien en el modo selector
# Deploy: edge

## Paso 0 (obligatorio)
Comprobar en el codigo si la cita del modo agentico lleva ancla. Si la lleva, cerrar el prompt
con la comprobacion escrita y pasar al siguiente.

Lectura del 2026-08-26 (2), a confirmar en el paso 0: `md_agent_selector_pipeline.py:79` emite
`source_url=d.canonical_url` sin ancla en el indice, y el agentico inyecta documentos enteros
via `read_document`, asi que **puede no haber fragmento del que sacar el ancla**. El paso 0
anota POR QUE hay o no hay ancla, porque eso decide si el arreglo es posible en este modo:
si no hay fragmento, la fuente del ancla es la puntuacion de `search_knowledge` (HIB.E) o no
hay arreglo, y eso se documenta como limite del modo.

## Cambio, si procede
- La cita del modo agentico pasa por `url_de_cita`, igual que el RAG.
- El ancla sale del fragmento mejor puntuado del documento.

## Tests (RED primero)
# should_cite_with_the_anchor_of_the_best_ranked_chunk
# should_fall_back_to_the_document_url_when_the_chunk_has_no_anchor

## Criterio de done
- [ ] Verificado en navegador: una cita del agentico abre el articulo
```

---

### Prompt HIB.E (RED/GREEN + MEDICIÓN) — La nota del agéntico es real, y el umbral se elige sobre una curva de dos ejes

**Modelo sugerido**: **Opus** — el cambio de código es corto; lo que exige criterio es el barrido.

**Objetivo**: `md_agent_selector_pipeline.py:82` asigna `score = 1.0` fijo, así que el agéntico
**responde siempre** y su puerta de calidad no puede rechazar nada con ningún umbral. Su 7 de 7
frente al 6 de 7 del RAG no mide recuperación: mide la ausencia de filtro.

**Lo que añade la literatura, y cambia cómo se mide**: la abstención tiene **dos ejes** —respuestas
que saldrían mal y preguntas que no deben responderse— y un solo score calibrado no los separa
[19]; aparece también como abstención estructural frente a estadística [21]. Elegir un umbral es
elegir un punto de una curva, no un número.

```
# PROMPT HIB.E (RED/GREEN + MEDICION) — Una nota de verdad, y una curva en vez de un numero
# Deploy: edge

## Cambio
- El `EvidenceItem` del pipeline agentico lleva la puntuacion real del documento en vez de 1.0.
- Con eso, `quality_threshold` actua en este modo por primera vez.

## Como se barre el umbral (y esto es lo que cambia respecto a la version anterior)
Al probar 2-3 umbrales se anotan **DOS columnas separadas**, no una:
- **callo y habia respuesta** (el fallo que el bloque RES vino a corregir)
- **contesto y no debia** (el fallo que la puerta existe para evitar)
Coste cero: la bateria ya se va a ejecutar. Sin esa separacion el umbral elegido no es
defendible, porque no se sabe que se esta comprando con el.

## Lo que hay que decir donde se lea
- El agentico PASARA A RENDIRSE en consultas que hoy contesta. Es la funcion, no la averia.
- El umbral esta hoy en 0,50 y se puso cuando no hacia nada: no se hereda, se elige.
- **No se fija el umbral definitivo en este prompt**: se produce la curva. El punto de operacion
  se elige con el lote de los informadores, que es el que tendra negativos de verdad.

## Tests (RED primero)
# should_carry_the_real_score_into_the_evidence_item
# should_surrender_when_no_document_reaches_the_threshold
# should_answer_when_the_best_document_reaches_the_threshold

## Ajuste del 2026-08-26 (2): el lote
La «bateria de Gerencia» son **7 consultas** sin fuente esperada
(`_local/golden/consultas_gerencia_econadm.json`: solo `name` y `prompt`). Barrer un umbral
sobre 7 observaciones no produce una curva: produce tres puntos de siete. **Este prompt se
ejecuta sobre el lote de Gerencia de HIB.G** (30-40 consultas, con negativos), no antes.

## Criterio de done
- [ ] Lote de Gerencia (HIB.G) con 2-3 umbrales y las dos columnas
- [ ] `docs/INFORME_CHATBOTS_NORMATIVA_Y_GERENCIA.html` actualizado: la asimetria desaparece
```

**DECIDIDO AL EJECUTAR (2026-08-27) — con qué se puntúa.** El prompt pedía «la puntuación real
del documento» sin decir cuál. Es **similitud coseno entre la consulta y el fragmento más
parecido del documento leído**, y la elección no es libre: HIB.J puso al *quality gate* a leer
coseno en la rama vectorial, y con escalas distintas un umbral de 0,50 significaría una cosa en
el RAG y otra en el agéntico — con lo que la comparación entre los dos asistentes de Gerencia,
que es el objeto de toda la rama, no querría decir nada.

Contra los **fragmentos** y no contra el documento entero por dos razones: el agéntico lee
`markdown_content` y ese texto no tiene vector, y un artículo que contesta bien dentro de una ley
de 279.425 tokens se diluiría en cualquier promedio del documento.

**Y cuando no se puede medir, se dice.** Sin embedder o con un documento sin fragmentos la nota
sigue en 1.0 pero queda marcada con `score_sin_medir`. Una nota inventada indistinguible de una
medida es lo que sostuvo la conclusión de que el agéntico iba mejor que el RAG durante un informe
entero. Y un puntuador roto no tumba la respuesta: rendirse porque no se pudo puntuar cambiaría
un fallo de instrumentación por un fallo de servicio.

---

### Prompt HIB.F (RED/GREEN) — Medir el contrato de citas por lo que garantiza, no por lo que rompe

**Modelo sugerido**: **Opus** — hay que definir la métrica y su forma de calcularla.

**Objetivo**: hoy medimos el contrato por su daño colateral —«1 → 2 → 5 descartes»—, y esa cifra
resultó ser **ruido entre tandas**. La literatura tiene desde 2023 dos métricas con definición
formal: **precisión y exhaustividad de cita por implicación textual** [22]. Miden lo que de
verdad importa: si cada afirmación está sostenida por lo que cita.

Para el objetivo declarado —elegir configuración— esto es lo que falta: una métrica que no
dependa de cuántas veces se dispara nuestro propio contrato.

```
# PROMPT HIB.F (RED/GREEN) — Precision y exhaustividad de cita
# Deploy: edge

## Cambio
- Instrumento en `_local/golden/` que, por respuesta, descomponga en afirmaciones y compruebe
  cual esta sostenida por el fragmento citado (juez con la evidencia delante, no de memoria).
- Se aplica a las tandas ya guardadas: no hace falta volver a generar.

## Por que en `_local/` y no en el repo
Opera contra el corpus real y las credenciales, como el resto del instrumental de evaluacion.

## Ajuste del 2026-08-26 (2): tres cosas sin las que la metrica no es defendible
1. **La remision sale del denominador.** HIB.0 legitimo nombrar una norma sin enlazarla. Si la
   precision de cita cuenta toda referencia, cada respuesta que menciona correctamente la Ley
   9/2017 pierde precision por algo que el contrato permite a proposito. Cita de fundamento
   entra en la metrica; remision se cuenta aparte y se reporta aparte.
2. **El juez de la metrica se valida antes de creerselo.** ALCE usa un modelo de implicacion
   textual, no la misma familia que genera; usar el mismo modelo invita a la autopreferencia.
   Antes de la primera cifra: 20-30 afirmaciones etiquetadas a mano (sostenida / no sostenida
   por el fragmento) y la concordancia del juez con esa etiqueta. Si baja de 0,8 de acuerdo
   simple, se cambia de juez o de plantilla, no se publica la cifra.
3. **Tanda de referencia declarada.** Las tandas guardadas son de antes de HIB.0 y de antes de
   apagar el reranker. Sirven para construir el instrumento; la cifra que se reporta se toma
   sobre el lote de HIB.G con la configuracion vigente.

## Criterio de done
- [ ] Juez validado contra las 20-30 afirmaciones etiquetadas, con su acuerdo anotado
- [ ] Las tandas de hoy medidas con la metrica nueva (construccion del instrumento)
- [ ] El lote de HIB.G medido con la configuracion vigente (cifra de referencia)
- [ ] El informe deja de citar «descartes» como medida de calidad
```

---

---

## Rama común — instrumentación que los dos pilotos necesitan

### Prompt HIB.G (DATOS + RED/GREEN) — El lote de configuración: fuente esperada por artículo, clases y negativos

**Modelo sugerido**: **Opus** — decidir qué es «fuente esperada» cuando la respuesta cruza dos
normas, y qué cuenta como negativo, es criterio; y el lote fija lo que todo lo demás puede medir.

**Objetivo**: hoy hay dos lotes y ninguno sirve para medir sin un humano delante. El de
Normativa (25, `escenarios_ujirag_2024.json`) tiene la fuente esperada **en prosa**
(`expectation_note`), sin negativos, de un solo dominio y sin balance por lengua. El de Gerencia
son **7** consultas con `name` y `prompt`. Sin fuente esperada estructurada, ni HIB.E ni HIB.F ni
ninguna ablación se re-ejecutan sin volver a pedir trabajo a los informadores.

**Lo que NO se hace**: escribir un lote nuevo desde el corpus. Una pregunta redactada mirando el
artículo comparte su vocabulario e **infla la recuperación léxica**; es la diferencia documentada
entre los lotes generados (ObliQA) y los de preguntas reales (BSARD). Las 25 reales se conservan
y se enriquecen; lo que se añade se marca por procedencia.

```
# PROMPT HIB.G (DATOS + RED/GREEN) — Un lote que se pueda medir sin un humano delante
# Deploy: edge (instrumental en _local/golden/, formato en el repo)

## Formato de escenario (extiende el actual, no lo sustituye)
Cada escenario anade a `name`, `prompt`, `history`, `expectation_note`:
- `expected_sources`: lista de {`canonical_url` o `document_id`, `anchor`}, en DOS conjuntos:
  `required` (sin ellos la respuesta es incorrecta) y `acceptable` (pueden aparecer sin penalizar).
  El ancla es la del articulo, no del documento: permite medir HIB.D y la precision de cita.
- `answerable`: true | false. Si false, `refusal_reason`: fuera_de_alcance | premisa_falsa |
  vigencia_no_validada | dato_no_normativo.
- `kind`: articulo_unico | varios_articulos | tabla_o_dato | seguimiento | negativo.
- `language`: ca | es.
- `domain`: para Normativa, la submateria del vocabulario vigente; para Gerencia, uno de
  contratacion | subvenciones | presupuesto | patrimonio | personal.
- `provenance`: real | informador | equipo_provisional | sintetico.
- `reference_answer`: breve, para resolver desacuerdos entre informadores, no prosa pulida.

## Tamanos y composicion
- Normativa: 60-80. Las 25 reales + ampliacion. ~25% negativos. Balance ca/es. 8-10 escenarios
  de dos turnos (para HIB.C). Al menos 5 de tipo tabla_o_dato.
- Gerencia: 30-40. Las 7 reales + candidatas sacadas de las interacciones ya guardadas
  (`hub_interactions` del asistente economico-administrativo) + negativos escritos a proposito.
  Los cinco dominios representados. Al menos 5 tabla_o_dato (limites, umbrales, plazos).

## Quien anota
La fuente esperada la anota un informador. Si no hay tiempo antes de los ensayos, la anota el
equipo y se marca `provenance: equipo_provisional`; el informador confirma o corrige despues y
la marca cambia. **Una cifra sobre fuentes anotadas por quien afino el sistema no se publica.**

## Afinado y informe se separan
El lote AFINA (top_k, umbral, reranker); el PILOTO informa. Si se elige la configuracion sobre el
lote y se reporta sobre el lote, es conjunto de entrenamiento. Queda escrito en el `meta`.

## Reutiliza
La taxonomia `failure_modes` del `meta` actual (curso_caducado, ambito_equivocado...) se conserva
y se usa para etiquetar los fallos; es la mejor parte del lote de 25 y no se reescribe.

## Tests (RED primero) — sobre el formato, en el repo
# should_reject_a_scenario_without_expected_sources_when_answerable
# should_reject_an_unanswerable_scenario_without_refusal_reason
# should_require_language_kind_and_provenance
# should_accept_the_existing_25_after_enrichment

## Criterio de done
- [ ] Normativa 60-80 y Gerencia 30-40 en `_local/golden/`, validados por el esquema
- [ ] Composicion reportada: por kind, language, domain, provenance, answerable
- [ ] `ejecutar_ujirag.py` (o su sucesor) calcula automaticamente: fuente esperada en el
      conjunto recuperado (si/no), ancla correcta (si/no), y rendicion correcta en los negativos
- [ ] Ninguna cifra del lote se reporta sin la columna de procedencia
```

**DESVIACIÓN DOCUMENTADA (2026-08-27) — los tamaños, a cambio de la procedencia.** Los lotes
salieron con **48 escenarios en Normativa y 18 en Gerencia**, no 60-80 y 30-40. El prompt pedía
ese volumen y a la vez prohibía redactar preguntas mirando el articulado, porque una pregunta
escrita desde la norma comparte su vocabulario e infla la recuperación léxica. Con los
informadores de vacaciones las dos cosas no se podían cumplir, y se cumplió la segunda: **36 de
los 48 escenarios de Normativa los escribió una persona que quería una respuesta** (25 del
ensayo con veredicto + 10 llegadas por el widget + 1 más) y ninguno se inventó.

Tres cosas que salieron de hacerlo así y no estaban previstas:

- **Seis preguntas reales llegaron al asistente equivocado**, y son el mejor negativo del lote.
  Preguntaban por contratación menor y crédito presupuestario al asistente de Normativa, donde
  las 24 leyes estatales y autonómicas que lo regulan están con `us_assistents='no'` —el
  reconciliador las retiró al salir de su manifiesto, correctamente, porque son de Gerencia—. El
  asistente no puede verlas, así que lo correcto es **declinar y remitir**; lo que hizo fue
  contestar con la norma de la UJI más parecida. Las mismas seis entran en el lote de Gerencia
  como **contestables**, con `meta.gemelo_negativo`: un par que sólo se distingue por el corpus
  del asistente prueba la rendición por ámbito en los dos sentidos.
- **El mandato del Síndic de Greuges se preguntó siete veces** por el widget, dos con fallback
  por *quality gate*, y la fuente está en el corpus (`Reglament de la Sindicatura de Greuges`,
  art. 9). Es la consulta real más repetida y la que peor iba.
- **Cinco contestables se quedaron sin fuente esperada** (ORI-12, ORI-18, SGE-03, SGE-04,
  REA-06, y REAL-07 en Gerencia). No entran en el lote —sin fuente no miden nada— y esperan en
  `_local/golden/pendientes_de_anotar.json`. Relajar el contrato para meterlas habría dado un
  lote más grande y menos medible.

La anotación es `equipo_provisional`: se localizó el candidato con `resolver_fuentes.py`
—búsqueda conjuntiva **por los términos de lo que el informador exige, no por las palabras de
la pregunta**, para no construir la verdad con el mismo criterio léxico que luego se mide— y se
verificó **leyendo el artículo**. De las 30 fuentes de Normativa, 9 llevan ancla verificada;
el resto exige a nivel de norma, que es justamente el nivel de la queja que abrió esto.

---

### Prompt HIB.H (RED/GREEN) — El panel de revisión captura la solución, no sólo el veredicto

**Modelo sugerido**: **Opus** — hay que decidir la forma del dato (varios artículos por respuesta,
distinción necesario/aceptable) y es una migración que el piloto va a llenar.

**Objetivo**: `HubInteraction` guarda `review_verdict`, `review_note`, `review_by`, `review_at`
(REV.1), y `HubTestScenario` guarda `expectation_note` en prosa. **No hay ningún campo para el
artículo esperado ni para la respuesta de referencia.** El usuario quiere que los informadores
den la solución: sin sitio estructurado donde ponerla, cada consulta revisada vale una vez; con
él, cada ablación posterior se mide sin volver a molestar a nadie, y el piloto produce juicios de
relevancia —que es lo que convierte sus datos en banco de pruebas publicable.

```
# PROMPT HIB.H (RED/GREEN) — La revision deja una referencia reutilizable
# Deploy: edge (tabla operacional) + frontend admin

## Cambio en datos
- `hub_interactions`: `review_expected_sources` JSONB nullable (misma forma que
  `expected_sources` de HIB.G: required/acceptable con url+anchor) y `review_reference_answer`
  Text nullable. **Nullable y sin default**: NULL es «no anotado», no lista vacia.
- `hub_test_scenarios`: `expected_sources` JSONB nullable con la MISMA forma. Un solo esquema
  para las dos tablas, validado por el mismo modelo Pydantic; dos formas divergirian.
- `expectation_note` se conserva: es la nota que lee quien juzga, y HubTestScenario ya explica
  por que no se convierte en asercion. Lo estructurado es ADEMAS, no en lugar de.
- Migracion Alembic; `alembic upgrade`.

## Cambio en API y UI
- `ReviewVerdictRequest` admite `expected_sources` y `reference_answer` opcionales.
- `InteractionReviewOut` los devuelve. Contrato regenerado (Orval).
- `RevisionInteraccionesPage`: selector de fuente esperada que **elige entre los documentos del
  corpus del chatbot** (busqueda por titulo, y el ancla de la lista de articulos del documento),
  nunca texto libre: una URL escrita a mano no casa con `canonical_url` y la metrica se pierde.
  Casilla «tambien aceptable». Campo de respuesta de referencia. i18n en las tres lenguas.
- Exportacion CSV incluye los campos nuevos.

## Lo que se pide de todo y lo que se pide de una parte (para el piloto)
- De TODAS: el veredicto. Es rapido y es la metrica primaria.
- De las UNICAS tras deduplicar: fuente esperada y respuesta breve.
- De ~100: doble evaluacion (para la kappa de HIB.K). El panel muestra si una interaccion ya
  tiene revision de otra persona SOLO despues de guardar la propia (ciego).

## Tests (RED primero)
# should_store_expected_sources_with_required_and_acceptable
# should_reject_an_expected_source_not_in_the_chatbot_corpus
# should_keep_null_when_the_reviewer_gives_no_sources
# should_export_expected_sources_in_the_csv
# should_hide_other_reviewers_verdicts_until_own_is_saved
# frontend: should_pick_sources_from_the_corpus_not_free_text

## Criterio de done
- [ ] Migracion aplicada, `alembic current` mostrado
- [ ] Verificado en navegador: revisar una interaccion, elegir dos articulos, exportar CSV
- [ ] `docs/MULTITENENCIA.md` sin cambios de ambito (la tabla ya es operacional) — comprobado
```

---

### Prompt HIB.I (RED/GREEN) — Cada interacción guarda lo que hace falta para re-correr una ablación

**Modelo sugerido**: **Sonnet** — la lista de campos está cerrada; el trabajo es llevarlos del
grafo a `interaction_metadata` y fijarlos por snapshot.

**Objetivo**: `hub_chat.py` guarda `interaction_metadata={"usage_source": ...}` y nada más. Con
el piloto en marcha ya es tarde para los datos que no se guardaron: sin los identificadores y
puntuaciones de lo recuperado no se puede saber, meses después, si una respuesta mala fue de
recuperación o de redacción, ni re-ejecutar una ablación sobre las mismas consultas.

```
# PROMPT HIB.I (RED/GREEN) — La traza que permite volver atras
# Deploy: edge

## Cambio
`interaction_metadata` pasa a llevar, ademas de `usage_source`:
- `retrieval_mode`, `chunking_strategy`, `retrieval_top_k`, `quality_threshold`,
  `reranker_enabled` — la configuracion VIGENTE en esa respuesta, no un puntero a la del chatbot,
  que cambia.
- `retrieved`: lista de {document_id, chunk_id, anchor, score} de lo que llego al modelo, en el
  orden en que llego, y `dropped_count` del packer.
- `best_score` y `gate_passed`.
- `language`, `source_language`, `translation_warning`.
- `turn_index` y `rewritten_query` (si HIB.C reescribio), `reformulada` (RES.2).
- `last_index_level` (agentico).
- `latency_ms` total y `first_token_ms`.
- `fallback_reason` ya existe como columna; no se duplica.

## Lo que NO se guarda
El contenido de los fragmentos: ya esta en `hub_document_chunks` por `chunk_id`, y duplicarlo
multiplica la tabla por el tamano del contexto.

## Por que JSONB y no columnas
Son campos de diagnostico cuya lista va a crecer con cada prompt de medicion; una migracion por
campo es lo que hace que dejen de anadirse. Las CLAVES se fijan por snapshot en un test para que
un cambio silencioso rompa.

## Tests (RED primero)
# should_store_the_effective_configuration_of_the_answer
# should_store_retrieved_ids_scores_and_anchors_in_order
# should_store_turn_index_and_rewritten_query
# should_keep_the_metadata_keys_stable (snapshot)

## Criterio de done
- [ ] Una consulta real en la base con todos los campos; mostrada
- [ ] `_local/golden/` puede reconstruir «que se recupero» de una interaccion sin re-ejecutarla
```

---

### Prompt HIB.J (RED/GREEN + MEDICIÓN) — Apagar el reranker apagó también el pool; recalibrar en la escala RRF

**Modelo sugerido**: **Opus** — qué significa la puerta de calidad en la escala RRF es una
decisión de diseño, no un ajuste; y hay que separar dos cambios que hoy van juntos en una línea.

**Objetivo**: HIB.A apagó el reranker con cuatro ejes coincidiendo, y bien. Pero en
`vector_strategy.py:69`:

    candidatos = pool_size(self._top_k) if self._reranker else self._top_k

con `POOL_MINIMO = 30` y `top_k = 3`, el híbrido pedía **30** fragmentos y ahora pide **3**. Justo
después se agrupa por `document_id` y se queda el mejor fragmento de cada documento: con
`parent_child` (60.859 fragmentos / 297 documentos) los 3 mejores pueden salir del mismo
documento, así que `top_k = 3` ya no significa tres documentos sino «hasta tres, probablemente
menos». Y `top_k = 3` lo eligió RES.4 **con el reranker encendido**: está descalibrado.

Segundo efecto: sin reranker, `score = min(1, rrf / RRF_MAX_SCORE)` mide **coincidencia de rango
entre las dos ramas**, no relevancia. Un documento en el top-3 de ambas ramas da ≈0,98; uno que
aparece sólo en una da ≈0,50. Con umbral 0,40, **las dos situaciones pasan**: la predicción es
que la puerta ha dejado de rechazar casi nada. Es el mismo defecto que HIB.E arregla en el
agéntico —puerta que es teatro— reapareciendo en el RAG por otra vía. Se comprueba en cinco
minutos sobre la tanda «sin reranker» de HIB.A, cuyas notas están guardadas.

**Va antes que HIB.B**: la verificación de HIB.B es «una consulta que la puerta rechace», y hoy
no se sabe si la puerta rechaza algo.

```
# PROMPT HIB.J (RED/GREEN + MEDICION) — Dos cambios que iban en una linea
# Deploy: edge

## Paso 0 (medicion, cinco minutos)
Sobre la tanda sin reranker de HIB.A: distribucion de `best_score` normalizado, cuantas
consultas quedaron bajo 0,40, y cuantos DOCUMENTOS DISTINTOS llegaron al modelo por consulta.
Se anota antes de tocar nada.

## Cambio de codigo
- El pool de candidatos deja de depender del reranker: `candidate_k` explicito en la
  configuracion del chatbot (heredable plataforma -> organizacion -> chatbot, como el resto),
  con defecto `pool_size(top_k)`. RRF ordena el pool; el reranker, si esta, reordena. Apagar el
  reranker ya no encoge el pool.
- La agrupacion por documento se hace SOBRE el pool, y `top_k` pasa a significar lo que dice:
  documentos distintos que llegan al modelo.

## Medicion
- Barrido de `top_k` in {2, 3, 4} x umbral in {0,50; 0,65; 0,80} en la escala RRF. Umbrales
  altos a proposito: si la nota es casi binaria, el punto util esta arriba.
- **Sobre que lote**: HIB.J va antes que HIB.G (orden aprobado), asi que la rejilla se ejecuta
  sobre las 25 actuales y la columna «contesto y no debia» queda VACIA y se dice: sin negativos
  no se puede rellenar. El punto de operacion que salga es provisional por partida doble, y la
  rejilla se REPITE sobre el lote de HIB.G cuando exista (es una tarea de HIB.G, no de este
  prompt). Lo que si decide este prompt con las 25: el codigo, el pool y los documentos
  distintos por consulta.
- Dos columnas por celda, como en HIB.E: «callo y habia respuesta» y «contesto y no debia».
  Los negativos del lote son lo que hace medible la segunda.
- Documentos distintos inyectados por consulta, media y minimo: es el numero que cambio en
  silencio y no se ve en ningun otro eje.

## Decision
Se elige un punto de operacion PROVISIONAL para Normativa y se marca como tal: el definitivo
sale del piloto. Se registra como cambio de configuracion (marco §7), con la cifra que lo
justifica.

## Tests (RED primero)
# should_keep_the_candidate_pool_when_the_reranker_is_off
# should_count_top_k_in_distinct_documents_not_chunks
# should_inherit_candidate_k_through_the_cascade
# should_keep_the_rrf_normalisation_unchanged (regresion)

## Criterio de done
- [ ] Paso 0 anotado con sus cifras ANTES del cambio
- [ ] Rejilla 3x3 con las dos columnas y los documentos distintos por consulta
- [ ] Punto de operacion provisional elegido y justificado; `docs/GERENCIA_TOP_K_Y_UMBRAL.html`
      o sucesor actualizado
```

---

### Prompt HIB.K (PROCESO + MEDICIÓN) — La rúbrica se calibra con los informadores antes de medir el sistema

**Modelo sugerido**: **Sonnet** — el trabajo es organizar la calibración y calcular la
concordancia; el criterio está cerrado.

**Objetivo**: el juez de HIB.A puntúa «contra la rúbrica del informador» y el de HIB.F hará lo
mismo. Si la concordancia entre informadores es desconocida, las dos métricas descansan sobre un
instrumento sin validar. La literatura avisa de que en dimensiones subjetivas los humanos entre
sí quedan en kappa ≈0,34; en objetivas suben a 0,53–0,61 [35]. Ninguna n arregla una rúbrica
inestable: se estaría midiendo con precisión creciente una opinión que cambia.

```
# PROMPT HIB.K (PROCESO + MEDICION) — Primero medir al que mide
# Deploy: n/a (instrumental en _local/golden/ y documento)

## Que se hace
- Rubrica escrita en una pagina, con la metrica primaria BINARIA: «utilizable tal cual» /
  «no utilizable». Secundarias (completitud, exactitud de la cita, tono) aparte y como tales.
- 40-60 respuestas del lote de HIB.G, dos informadores, a ciegas y en orden aleatorio.
- Kappa de Cohen sobre la primaria; acuerdo simple sobre las secundarias.
- Si kappa < 0,6: se leen los desacuerdos, se reescribe la rubrica, se repite sobre otras 20.
  No se toca el sistema hasta que la rubrica se sostenga.

## Que se guarda
- La rubrica versionada en `docs/` (es lo que el piloto y el articulo van a citar).
- La kappa con su intervalo. Con 40-60 items el intervalo es ±0,13-0,15: sirve para decidir si
  la rubrica vale, NO para publicar la cifra; para eso hacen falta ~100 doblemente evaluados,
  que los dara el piloto (HIB.H).

## Criterio de done
- [ ] Rubrica en `docs/RUBRICA_INFORMADORES.md`, versionada
- [ ] Kappa calculada y anotada con su n y su intervalo
- [ ] El juez LLM de `_local/golden/` puntua contra ESA rubrica, y su acuerdo con los
      informadores sobre las mismas 40-60 queda anotado
```

---

## Rama Gerencia — dejar los dos asistentes económico-administrativos listos para el piloto

> El asistente RAG de Gerencia sigue en `structural` sin padre y el agéntico responde siempre.
> Esta rama los lleva al mismo grado de madurez que Normativa. **Los dos se abren al piloto
> sobre las mismas consultas**, con la estrategia en la traza (HIB.I): es la comparación
> controlada interna que el informe de literatura pide, y no cuesta más que lo que ya se va a
> pedir a los informadores.

### Prompt HIB.L (DECISIÓN + RED/GREEN) — Techo del padre en las normas externas

**Modelo sugerido**: **Opus** — es la decisión aplazada del 2026-08-26 y tiene dos salidas
razonables con costes distintos.

**Objetivo**: los padres de las normas externas llegan a **236.691 caracteres (~59.000 tokens)**.
El packer tiene presupuesto de 128.000 y corta con criterio: con `top_k = 3`, dos padres largos
lo llenan y el tercero cae (`dropped_count`). No es un fallo de corrección, es de coste y de
latencia: ~118.000 tokens de entrada por consulta, que en un piloto con funcionarios es dinero
visible y una espera visible. El usuario aplazó la decisión con un argumento válido —para el
asistente económico-administrativo, el contexto completo de la norma estatal es lo adecuado—;
este prompt la toma con cifras.

```
# PROMPT HIB.L (DECISION + RED/GREEN) — Cuanto padre cabe
# Deploy: edge

## Paso 0 (medicion)
Sobre las 22 normas externas: distribucion del tamano de sus secciones-padre (caracteres y
tokens estimados). Cuantas superan 8.000, 16.000, 32.000 tokens. Cual es la unidad estructural
inmediatamente inferior (capitulo -> articulo) y su distribucion.

## Opciones, con recomendacion
- **(recomendada)** Padre = la unidad estructural mas fina que quepa en un techo por documento
  (`parent_max_tokens`, heredable, defecto 8.000). Para normas UJI el padre sigue siendo la
  seccion (caben); para una ley estatal el padre baja a capitulo o articulo. El techo es
  configuracion, no codigo, y se decide por chatbot: Gerencia puede subirlo.
- Alternativa: techo duro por truncado del padre. Mas simple, pero corta articulos por la mitad
  y eso es exactamente lo que el padre existe para evitar.

## Lo que hay que decir donde se lea
Bajar el padre a capitulo en una ley estatal NO es «menos contexto»: con un techo de 8.000 el
modelo recibe el capitulo entero, que es la unidad que un jurista lee. Lo que se pierde es la
ley completa, que a 59.000 tokens tampoco se leia entera: se cortaba en el packer sin que nadie
lo viera.

## Tests (RED primero)
# should_choose_the_finest_structural_unit_under_the_token_cap
# should_keep_the_section_as_parent_when_it_fits
# should_inherit_parent_max_tokens_through_the_cascade
# should_never_split_an_article_in_two_parents

## Criterio de done
- [ ] Paso 0 con la distribucion
- [ ] Decision tomada y escrita en `docs/DECISION_MODELOS_EMBEDDING_RERANKER.md` o documento
      propio, con el coste por consulta antes y despues (tokens y ms)
```

---

### Prompt HIB.M (MEDICIÓN) — La ablación del reranker, sobre el corpus de Gerencia

**Modelo sugerido**: **Sonnet** — mismo instrumental y mismo criterio escrito que HIB.A, sobre
otro lote.

**Objetivo**: la decisión de HIB.A **no se traslada**: otro corpus, normas estatales largas,
castellano, y consultas de tabla («¿cuál es el límite de un contrato menor?»), que es justo el
patrón donde el léxico y el vector se comportan distinto. Lo que se midió en Normativa dice qué
esperar; no dice qué pasa aquí.

```
# PROMPT HIB.M (MEDICION) — Lo mismo, en el otro corpus
# Deploy: edge

## Que se ejecuta
- El lote de Gerencia de HIB.G sobre el asistente RAG de Gerencia, con y sin reranker.
- Con el pool desacoplado de HIB.J, para que la ablacion mida el reranker y no el pool.
- Mismos ejes que HIB.A: fuente esperada en el conjunto recuperado, solapamiento (Jaccard) de
  documentos, juez a ciegas con doble vuelta, descartes por citas. Y uno mas que HIB.A no tenia:
  **rendicion correcta en los negativos**, porque este lote los tiene.

## Criterio de decision, escrito ANTES
El de HIB.A, palabra por palabra. Si empatan, se queda apagado por coherencia con Normativa y
por coste, y se anota.

## Criterio de done
- [ ] Las dos tandas en `_local/golden/`
- [ ] Decision segun el criterio, con sus cifras
- [ ] Anotado que se vuelve a medir con el lote del piloto (decision del usuario 2026-08-26)
```

---

### Prompt HIB.N (RED/GREEN) — Gerencia pasa a `parent_child` reutilizando lo ya embebido

**Modelo sugerido**: **Opus** — la copia entre corpus es la clase de operación en la que un
metadato mal remapeado rompe la recuperación en silencio.

**Objetivo**: el antiguo HIB.6, que el bloque reescrito aplazó «hasta después de HIB.A». HIB.A
está cerrado y HIB.L fija el techo del padre; ahora se sabe con qué configuración re-trocear.
Las 22 normas externas están en los tres chatbots **con `content_hash` idéntico** (comprobado el
2026-08-26) y las de Normativa UJI ya están troceadas con padre.

```
# PROMPT HIB.N (RED/GREEN) — Lo mismo no se embebe dos veces
# Deploy: edge

## Cambio
- Script de copia: los fragmentos de un documento de un chatbot se copian a su gemelo de otro
  chatbot cuando coinciden `content_hash` Y la estrategia de troceado Y el techo del padre
  (HIB.L). Si difiere cualquiera de los tres, se niega y lo dice.
- Se remapean `chatbot_id`, `document_id` Y el `document_id` que va DENTRO de `chunk_metadata`.
  Sin lo tercero, la agrupacion por documento del retrieval se rompe sin dar ningun error.
- Lo propio de Gerencia (102 documentos, 4.388 fragmentos hoy) SI se re-ingiere, con el padre
  y el techo de HIB.L.
- El agentico NO se re-trocea: lee `markdown_content`.

## Cuentas (a confirmar al ejecutar)
Copiar ~27.353 fragmentos por chatbot a coste cero; re-embeber ~11.000. El 71% ya pagado —si el
techo de HIB.L no ha cambiado el troceado de las externas; si lo cambio, esas tambien se
re-embeben y la cuenta se rehace ANTES de lanzar.

## Tests (RED primero)
# should_copy_chunks_only_when_hash_strategy_and_cap_match
# should_remap_the_document_id_inside_chunk_metadata
# should_refuse_to_copy_when_the_chunking_strategy_differs
# should_be_idempotent
# should_leave_zero_chunks_with_inconsistent_document_id

## Criterio de done
- [ ] Lote de Gerencia (HIB.G) antes y despues, con fuente esperada en el conjunto recuperado
- [ ] Cero fragmentos con `document_id` inconsistente entre columna y metadato (consulta SQL
      mostrada)
- [ ] Coste real de embeddings anotado
```

**CORRECCIÓN DEL PROMPT (2026-08-27) — el permiso de copia no se puede dar comparando
configuraciones.** El prompt decía «cuando coinciden `content_hash` Y la estrategia de troceado
Y el techo del padre». Los dos últimos, leídos de la configuración, dan luz verde en falso: la
configuración de Normativa **declara** techo de 8.000 tokens y sus datos **tienen** padres de
59.172, porque sus fragmentos se crearon antes de que HIB.L fijara ese techo. Comparar lo que se
pretendía habría metido en Gerencia padres que su propio techo prohíbe.

`chunk_copier.se_puede_copiar` comprueba por eso **los datos**: que ningún fragmento traiga un
padre por encima del techo del destino, y que la presencia o ausencia de padre case con la
estrategia del destino en los dos sentidos. Y cuando se niega, dice cuál es el arreglo.

**Las cuentas del prompt no se sostienen, y salen mejor.** Decía «copiar ~27.353 fragmentos por
chatbot y re-embeber ~11.000», sobre la premisa de que Gerencia tenía 102 documentos propios sin
gemelo. Medido: **los 124 documentos de Gerencia tienen gemelo exacto por `content_hash` en
Normativa, ninguno queda fuera**, así que el coste de embeddings de esta operación es **cero**.

**Y el techo se aplica con un `UPDATE`, no re-embebiendo.** `parent_content` se guarda aparte y
no entra en `embedding_text` —que se construye con el texto del hijo más el título y los
encabezados—, así que alinear los datos con la decisión de HIB.L cuesta una sentencia. Se
revierte re-troceando desde `markdown_content`, que sigue completo: se pierde tiempo, no dinero.
Alcance medido antes de tocar nada: **5.172 de 60.859 fragmentos (8,5 %)** arrastran un padre
por encima del techo, y son **125 de los 180 millones** de tokens de padre almacenados para un
corpus de 2,1 millones —la amplificación viene de que cada hijo guarda su padre entero—.

El código y sus 11 tests entraron en el commit `499ec35`, agrupados por error con la corrección
del contrato de HIB.G.

---

### Prompt HIB.O (DATOS + RED/GREEN) — La vigencia de las normas externas se valida antes de abrir

**Modelo sugerido**: **Sonnet** — el mecanismo (REV.6) existe; el trabajo es alimentarlo y
comprobar el efecto.

**Objetivo**: el aviso de vigencia salta si `vigencia_validada_el IS NULL`. Las normas del BOE
consolidado tienen vigencia comprobable en la fuente oficial; si entran sin validar, el
asistente pondrá aviso en casi todas sus respuestas ante funcionarios que saben que la Ley 9/2017
está vigente. **Un aviso que sale siempre deja de informar**: se quema el mecanismo justo en el
piloto donde más importa. Con 312 de 314 fichas en «vigent?», el aviso es correcto en Normativa;
en Gerencia hay 22 documentos donde puede y debe quitarse.

```
# PROMPT HIB.O (DATOS + RED/GREEN) — Que el aviso salga cuando toca
# Deploy: edge

## Que se hace
- Lista de las 22 normas externas con su URL de consolidado oficial (BOE / DOGV) y su fecha de
  ultima modificacion segun la fuente. Quien valida es una persona (Gerencia o Secretaria
  General): el equipo prepara la lista, no firma la validacion.
- Por cada una validada: `estat_vigencia = 'vigent'`, `vigencia_validada_el`,
  `vigencia_validada_per` via la pantalla de REV.6 o su endpoint. Sin tocar `revisat_per`, que
  es otra cosa (el comentario del modelo lo explica).
- Comprobacion: una consulta del lote de Gerencia cuya fuente esperada sea una externa
  validada NO lleva aviso; una cuya fuente sea una norma UJI sin validar SI lo lleva.

## Lo que este prompt NO hace
No valida las normas UJI: eso es de Secretaria General y esta en la lista de lo que se le pide.

## Tests (RED primero)
# should_not_warn_when_the_cited_document_is_validated_and_in_force
# should_still_warn_when_any_cited_document_is_unvalidated

## Criterio de done
- [ ] Las 22 con su URL de consolidado en un fichero de `_local/` (no en el repo: es dato)
- [ ] Las validadas por la persona responsable, con fecha y firma, en la base
- [ ] Proporcion de respuestas del lote de Gerencia con aviso, antes y despues
```

---

### Prompt HIB.P (MEDICIÓN + CONFIG) — Punto de operación provisional de los dos asistentes de Gerencia

**Modelo sugerido**: **Sonnet** — con HIB.E, HIB.J y HIB.M cerrados, la curva ya existe; el
trabajo es elegir el punto y registrarlo como manda el marco.

**Objetivo**: HIB.E produce la curva del agéntico pero **no fija el umbral** —dice que se elige
con el lote de los informadores—. El piloto, sin embargo, **abre con un umbral**, y hoy es 0,50
puesto cuando la puerta no hacía nada. Hace falta un punto de operación provisional para los dos
asistentes, marcado como tal, y registrado donde el marco dice que van los cambios de
configuración (§7).

```
# PROMPT HIB.P (MEDICION + CONFIG) — Con que abre Gerencia
# Deploy: edge (configuracion)

## Que se hace
- RAG de Gerencia: rejilla top_k x umbral en la escala que quede tras HIB.M (RRF o reranker),
  sobre el lote de HIB.G, con las dos columnas. Igual que HIB.J para Normativa.
- Agentico de Gerencia: sobre la curva de HIB.E, elegir el punto.
- Criterio de eleccion escrito ANTES de mirar la rejilla: se prefiere el punto que minimiza
  «contesto y no debia» sujeto a que «callo y habia respuesta» no supere X% (X lo fija el
  usuario; propuesta 15%). Un funcionario que recibe un dato de contratacion equivocado actua
  sobre el; uno que recibe una rendicion pregunta a la Unidad.
- Los dos puntos se registran como cambio de configuracion versionado, con autoria y con la
  cifra, y se marcan «provisional hasta el cierre del piloto».

## Criterio de done
- [ ] Rejilla del RAG y curva del agentico, con las dos columnas
- [ ] Puntos elegidos segun el criterio escrito, registrados
- [ ] `docs/INFORME_CHATBOTS_NORMATIVA_Y_GERENCIA.html` con la configuracion de apertura de los
      cuatro asistentes (dos de Normativa, dos de Gerencia) en una tabla
```

---

### Prompt HIB.R (CONFIG + RED/GREEN) — El umbral a 0,65, que es lo único que el umbral puede comprar barato

**Modelo sugerido**: **Sonnet** — el punto ya está elegido sobre la curva; el trabajo es moverlo
en los tres sitios y no dejar dos números para el mismo mando.

**De dónde sale**: decisión del usuario del 2026-08-27, tomada sobre la curva de las dos columnas
calculada del lote de 48 escenarios de Normativa. La curva se pudo calcular **sin volver a
generar nada**, porque la puerta es `nota >= umbral` y las notas estaban guardadas.

| umbral | declina bien (de 18) | contestables perdidos |
|---|---|---|
| 0,60 (vigente) | 0 | 0 % |
| **0,65** | **2** | **0 %** |
| 0,70 | 4 | 7 % |
| 0,72 | 10 | 17 % |
| 0,75 | 16 | 50 % |

```
# PROMPT HIB.R (CONFIG + RED/GREEN) — El punto que no cuesta nada
# Deploy: edge (configuracion)

## Cambio
- Defecto de columna `HubChatbot.quality_threshold` y `HubOrganizacion.default_quality_threshold`:
  0,60 -> 0,65. **Sin `server_default` y sin migracion**: un defecto de columna solo actua al
  insertar, y los cuatro chatbots que ya existen tienen su umbral puesto a mano o medido.
- `_PLATFORM_DEFAULTS.quality_threshold`: 0,60 -> 0,65. No porque haga falta —la columna gana,
  por la trampa que documento HIB.Q— sino para que no haya dos numeros para el mismo mando.
- Valor VIVO de Normativa UJI: 0,60 -> 0,65, con la cifra que lo justifica en el registro.
- Gerencia NO se toca: su 0,35 esta en la escala vieja y lo elige HIB.P.

## Lo que este prompt NO arregla, y hay que decirlo donde se lea
Los cinco casos de contratacion que el asistente contesta y no deberia puntuan **0,742-0,787**,
por encima de casi cualquier respuesta correcta. **Ningun umbral los alcanza** sin llevarse por
delante la mitad de lo bueno. El umbral no es donde esta el margen.

## Tests (RED primero)
# should_default_the_quality_threshold_to_sixty_five
# should_align_the_organization_default_with_the_chatbot_column
# should_align_the_platform_default_too
# should_not_carry_a_server_default_that_would_touch_existing_rows

## Criterio de done
- [ ] Los tres defectos a 0,65 y el valor vivo de Normativa cambiado
- [ ] El cambio registrado con su cifra y su autoria (§7 del marco)
- [ ] Medido sobre el lote DESPUES del cambio: dos negativos mas y cero contestables perdidos
```

---

### Prompt HIB.S (RED/GREEN + MEDICIÓN) — El contrato de citas comprueba el fundamento, no sólo que se cite

**Modelo sugerido**: **Opus** — es una puerta nueva en el camino de la respuesta, con coste de
latencia y riesgo de rechazar lo bueno; y la decisión de qué hacer cuando el juez duda es de
criterio.

**De dónde sale**: es el mecanismo que quedó en pie después de descartar los otros tres, medidos
el 2026-08-27 sobre el lote de 48 de Normativa. El asistente **contesta 11 de las 18 preguntas
que debería declinar**, y ninguna señal del lado de la recuperación distingue esos 11 de los 30
que sí debía contestar:

- **La nota de calidad no separa.** Los 11 puntúan 0,643-0,787; los 30 correctos, 0,692-0,805.
  Los negativos mal contestados puntúan de mediana **más alto** (0,715) que los correctos más
  bajos.
- **La brecha entre el primero y el segundo tampoco**, y va al revés: 0,020 de mediana en los
  fallos contra 0,010 en los aciertos.
- **Ni el número de fuentes** (3 y 3), **ni la media de las notas** (0,704 contra 0,734).
- **Ni «la mejor evidencia es un documento vetado»**, que se propuso y se midió: el documento
  con `us_assistents='no'` gana al permitido en 2 de 8 negativos y en 1 de 6 contestables. No
  discrimina.

**Y el hallazgo que dice dónde sí está el margen**: la puerta de calidad rechazó **cero de 48**.
Los 7 rechazos correctos los produjo el **contrato de citas** (`fallback_reason='citation'`), con
**precisión perfecta**: 7 aciertos y ni un rechazo indebido sobre 30 contestables. El contrato
funciona; lo que le falta es alcance. Hoy pregunta «¿ha citado?» y los 11 fallos **citan** —citan
normas de la UJI que hablan de contratos para una pregunta de contratos—.

```
# PROMPT HIB.S (RED/GREEN + MEDICION) — De «cito» a «lo que cito lo sostiene»
# Deploy: edge

## Lo que NO es esto, para no confundirlo con lo que ya hay
El **puente lexico bilingue** (RAG.4 / RES.3) no transforma la consulta: la pasa tal cual a
`websearch_to_tsquery` e **indexa el documento bajo las dos formas** —los pares `despesa`/`gasto`
van a `bilingual_terms` y `tsv` es una columna generada sobre `content || ' ' || bilingual_terms`—.
Por eso cambiar un par cuesta un `UPDATE` y no un reembebido. Medido el 2026-08-27: 48.752 de
113.618 fragmentos tienen terminos bilingues, **todos del front-matter del `.md` curado**, porque
`HubLexiconPair` tiene **0 filas**: el circuito de aprobacion de pares nuevos a partir de terminos
reales de usuario existe y nunca se ha usado.

## Cambio
- Una comprobacion mas en `enforce_citation_contract` (o inmediatamente despues, dentro de
  `generate_answer_node`): por cada afirmacion de FUNDAMENTO de la respuesta, se comprueba que
  el fragmento citado la sostenga. Si NINGUNA afirmacion de fundamento se sostiene, la respuesta
  se descarta y habla el fallback, igual que cuando hoy no hay cita valida.
- El instrumento ya existe y esta validado: `_local/golden/precision_de_cita.py`, cuyo juez
  acuerda **24 de 24** con las 24 afirmaciones etiquetadas a mano (Wilson 95 %: 0,86-1,00),
  incluidos los casos duros de esta forma exacta —una afirmacion cierta en el mundo pero ausente
  del fragmento citado, y una cierta en otra fila del mismo anexo—. Lo que este prompt hace es
  llevarlo del banco de evaluacion al camino de la respuesta.

## Las tres decisiones de criterio, y por que asi
1. **El umbral de descarte es «ninguna sostenida», no «todas sostenidas».** Una respuesta larga
   con ocho afirmaciones y siete sostenidas es utilizable; exigir las ocho convertiria la puerta
   en un generador de rendiciones. Se empieza por el extremo conservador y se mueve con datos.
2. **Cuando el juez no contesta o contesta ilegible, la respuesta PASA.** Un fallo del juez es
   un fallo de instrumentacion, y cambiarlo por una rendicion seria cambiarlo por un fallo de
   servicio. Se registra en la traza (HIB.I) para poder contar cuantas veces pasa.
3. **La remision no entra.** HIB.0 legitimo nombrar una norma sin enlazarla; una respuesta que
   remite correctamente a la Ley 9/2017 no puede perder por eso.

## El coste, que hay que medir y no estimar
Una llamada mas por respuesta. Medido en el experimento de granularidad, la latencia la manda la
SALIDA (r=+0,997) y no la entrada (r=-0,109), asi que una llamada de juicio con salida corta
—un JSON de dos campos— deberia costar poco. **Hay que medirlo**, y hay que medirlo sobre el
primer token percibido, no sobre el total: si la comprobacion va DESPUES de generar, el usuario
ya ha visto la respuesta entera cuando se decide descartarla, y eso es peor que esperar.
**Decision de diseno pendiente**: o se comprueba antes de emitir (mas latencia percibida) o se
emite y se retira (el evento `discard` de HIB.B ya existe y el widget ya sabe vaciar la burbuja).

## Convergencia con la reformulacion al vocabulario normativo (pregunta del usuario, 2026-08-27)
`reformular_node` ya normaliza la consulta al vocabulario de las normas con una llamada al
modelo, y esta bien que se pague solo cuando hace falta: normalizar siempre costaria una llamada
en el camino critico de todas las consultas, y el propio comentario del nodo dice que se pagaba
en el 28 % de las de Normativa y el 71 % de las de Gerencia.

**Pero su disparador es la puerta de calidad, y la puerta rechazo CERO de 48.** Los 7 rechazos
fueron del contrato de citas, que actua DESPUES de generar — demasiado tarde para reformular y
volver a buscar. Asi que la normalizacion se ejecuto en ~0 de 48 consultas: esta bien construida
y colgada de un disparador que no dispara.

La comprobacion de fundamento detecta exactamente «lo recuperado no sostiene lo que la respuesta
afirma», que es **la misma señal** que deberia disparar una segunda busqueda con la consulta
normalizada. Un solo mecanismo puede alimentar las dos cosas: **reformular y reintentar antes de
rendirse**, en vez de rendirse directamente.

No se implementa en este prompt —cambia el camino de la respuesta y su latencia dos veces en vez
de una— pero se mide: de los 11 negativos que la puerta nueva descarte, cuantos habrian sido
contestables tras reformular. Si son pocos, reintentar no compensa y se descarta por escrito.

## Tests (RED primero)
# should_discard_the_answer_when_no_grounded_claim_survives
# should_keep_an_answer_with_some_claims_grounded
# should_let_the_answer_through_when_the_judge_fails
# should_not_count_a_remission_as_an_ungrounded_claim
# should_record_the_check_in_the_trace

## MEDIDO el 2026-08-28 — NO SE DESPLIEGA, y por que

Dos tandas de 48 escenarios, con la comprobacion apagada y encendida:

| | apagada | encendida |
|---|---|---|
| negativos declinados | 7/18 | **10/18** |
| respuestas buenas rechazadas | 0/30 | **10/30** |

Caza 3 negativos mas y rechaza **10 de las 30 respuestas correctas**. El criterio escrito antes
de medir era «si pasa de 2 de 30, no se despliega». Son 10: **no se despliega**.

**Y la causa no es un fallo suelto.** De las 33 afirmaciones de los 9 contestables rechazados,
**19 estaban LOCALIZADAS** —el juez vio la ventana correcta del articulo citado— y las rechazo
igualmente; 14 cayeron por la regla de la cifra ausente. En ORI-06 y SGE-01 **todas** las
afirmaciones estaban localizadas y el juez dijo «no» a todas.

Lo que falla es el **grano**: la comprobacion evalua **frases enteras contra UN solo documento
citado**, y las respuestas reales meten varios hechos y varias citas en la misma frase. Una frase
con tres hechos de dos normas distintas no la sostiene ninguna de las dos por separado.

## Lo que haria falta para que funcione, y no es un parche
1. **Descomponer en afirmaciones ATOMICAS**, un hecho cada una, en vez de partir por frases. Es
   la definicion de ALCE y es lo que el instrumento de `_local/golden/precision_de_cita.py` si
   hace —con una llamada al modelo por respuesta— y lo que la version del grafo no hace.
2. **Comprobar cada afirmacion contra TODAS las fuentes que cita**, no contra la primera. Hoy
   `_fuente_de` toma el primer enlace de la frase, y ORI-16 llevaba dos en una.
3. Y volver a medir el acuerdo del juez **sobre afirmaciones atomicas reales**, no sobre las 24
   etiquetadas a mano, que son inequivocas por construccion y donde acordo 24 de 24.

Hasta entonces queda **apagada** y el piloto abre sin ella. La abstencion sigue siendo el hueco:
lo que hoy la produce es el contrato de citas, con 7 de 18 y sin falsos positivos.

## Criterio de done
- [x] Medido sobre los 11 negativos que hoy se contestan: cuantos caza (cifra REAL, no estimada)
- [ ] Medido sobre los 30 contestables: cuantos rechaza indebidamente. Si pasa de 2, no se
      despliega y se revisa la plantilla del juez
- [ ] Latencia del primer token con y sin la comprobacion, sobre la misma muestra
- [ ] Decidido y escrito si comprueba antes de emitir o emite y retira
- [ ] La cifra de precision de cita del lote, con la reserva del juez anotada
```

---

### Prompt HIB.Q (RED/GREEN) — Un chatbot nuevo nace con lo que se ha medido

**Modelo sugerido**: **Sonnet** — alcance cerrado; lo delicado es una trampa de la cascada, ya
localizada.

**De dónde sale**: pregunta del usuario del 2026-08-27 al cerrar HIB.C. Los cambios de HIB.J,
HIB.B, HIB.C y HIB.I son código y los hereda cualquier chatbot; pero tres parámetros son
configuración por chatbot, y ahí un chatbot nuevo hereda el **valor por omisión**, no lo que se
puso a mano en Normativa.

```
# PROMPT HIB.Q (RED/GREEN) — Los defectos, alineados con lo medido
# Deploy: edge (configuracion)

## La trampa que decide como se arregla
`_apply_layer` aplica solo los valores NO NULOS de cada capa, asi que una columna NOT NULL del
chatbot gana SIEMPRE al defecto de plataforma. `retrieval_top_k` es NOT NULL con defecto 8:
tocar solo `_PLATFORM_DEFAULTS` no habria movido nada para ningun chatbot. Hay que mover el
defecto de la COLUMNA. `query_rewriting_enabled` si es nullable, y ahi nulo significa heredar.

## Cambio
- `HubChatbot.retrieval_top_k`: defecto 8 -> 3, y el mismo 3 en `_PLATFORM_DEFAULTS` y en el
  dataclass, para que no haya dos numeros para la misma anchura.
- `query_rewriting_enabled` en la configuracion de plataforma: False -> True. Sin esto, desde
  HIB.C un chatbot nuevo RECIBE el historial y no lo reescribe: llega la fontaneria y no la
  funcion, y no hay ningun error que lo delate.
- **Sin `server_default` y sin migracion**: un defecto de columna solo actua al insertar, asi
  que los chatbots que ya existen no se tocan. Es lo que se quiere.

## Lo que NO cambia, y por que
- `min_retrieval_results` se queda en 2. El 1 de Normativa fue un apano de desarrollo con un
  corpus de un solo documento, no una decision.
- `quality_threshold` ya estaba en 0,6, que es el punto que eligio HIB.J — por casualidad y no
  por diseno, y conviene decirlo.
- `reranker_enabled` ya estaba en False, coherente con lo que midio HIB.A.

## Tests (RED primero)
# should_default_the_width_to_three_documents
# should_default_to_rewriting_the_query
# should_align_the_platform_default_with_the_column
# should_let_a_chatbot_override_the_platform_width
# should_not_change_the_chatbots_that_already_exist

## Criterio de done
- [ ] Los tres valores vivos que siguen en la escala vieja, anotados para HIB.E, HIB.M y HIB.P:
      Gerencia RAG con umbral 0,35 y reranker True, y el agentico con 0,5
```

---

## Orden de ejecución (2026-08-26, segunda revisión — **aprobado por el usuario: HIB.J antes de HIB.B**)

Hay dos dependencias duras que reordenan el bloque: **HIB.J va antes que HIB.B** (la verificación
de HIB.B necesita una puerta que rechace algo) y **HIB.G va antes que cualquier medición** (HIB.E,
HIB.F, HIB.J, HIB.M, HIB.P se ejecutan sobre su lote).

| Paso | Prompt | Por qué aquí |
|---|---|---|
| 1 | **HIB.J** | Apagar el reranker encogió el pool 10× y descalibró umbral y `top_k`; sin esto, B no se puede verificar |
| 2 | **HIB.G** | El lote; todo lo que mide depende de él. Puede empezar en paralelo con J |
| 3 | **HIB.B**, **HIB.C** | Los dos defectos visibles, comunes a los cuatro asistentes |
| 4 | **HIB.H**, **HIB.I** | Instrumentación que hay que tener ANTES de la primera consulta del piloto |
| 5 | **HIB.K** | Rúbrica calibrada; sin ella las métricas de F no tienen suelo |
| 6 | **HIB.F** | Métrica de citas sobre el lote de G |
| — | **Normativa listo para abrir** | |
| 7 | **HIB.L** → **HIB.M** → **HIB.N** | Gerencia: techo del padre, ablación en su corpus, re-troceado. En este orden para no embeber dos veces |
| 8 | **HIB.D** → **HIB.E** | Agéntico: ancla y nota real, sobre el lote de G |
| 9 | **HIB.O**, **HIB.P** | Vigencia de las externas y punto de operación |
| — | **Gerencia listo para abrir** | |

Si hay que abrir Gerencia antes de completar la rama, el mínimo es **L + O + P** con el
asistente en `structural`, declarando en el informe que entra sin padre y con el reranker sin
medir en su corpus. M y N pueden hacerse con el piloto abierto **sólo si se registran como
cambio de configuración y se reporta por tandas** (regla 5 del diseño de ensayos).

## Tres cosas que ya existen y no necesitan prompt

- **Aviso de IA (RIA art. 50, en vigor desde el 2 de agosto de 2026)**: existe en el widget en
  las tres lenguas (`ai_disclaimer` en `ChatWidget.tsx:427`). Al cerrar el bloque, el `.bat`
  comprueba una sola cosa: que se ve **antes** de la primera respuesta, no sólo al pie del hilo.
- **Presupuesto de contexto**: el packer ya corta con criterio y deja `dropped_count`; el padre
  gigante degrada, no rompe. HIB.L decide cuánto se paga, no si funciona.
- **Panel de revisión y escenarios de prueba** (REV.1, RAG.13): existen; HIB.H les añade el
  campo que falta, no los rehace.

## Lo que sale del bloque, y por qué

- **«Darle vectores al agéntico»** (el antiguo HIB.1): se cae, ya los tiene vía `search_knowledge`.
  Lo que quedaba —ordenar el catálogo por puntuación— es menor y no es lo que arregla el 7 de 7.
- **Gerencia a `parent_child`**: ya no sale; es HIB.N, después de HIB.A (cerrado) y de HIB.L.

## Candidatos con prompt propio, para después

- **Cierre de citas**: seguir la remisión cuando la norma citada está en el corpus [12], en vez de
  sólo degradar el enlace. **Aviso**: el informe dice que buena parte de las remisiones son
  resolubles «porque las 22 normas externas están en el corpus», y eso **dejó de ser cierto en
  Normativa UJI** el 2026-08-26, cuando se apagaron con `us_assistents='no'`. En Gerencia siguen.
- **Resumen del documento anexado al fragmento** [5], como alternativa más barata a padre-hijo:
  mitad de desajuste de documento. Es una ablación contra lo ya pagado, no una sustitución. Y
  antes de probarlo hay que comprobar que **no rompe la regla de reclasificación barata**: el
  resumen es texto embebido, así que sólo vale si se genera del contenido y nunca del vocabulario.
- **Versionado temporal de la norma** [14, 15]: con 312 de 314 fichas declarando «vigent?», es
  decisión de Secretaría General antes que de ingeniería.

## Lo que este bloque le pide al lote de los informadores

Sale de la revisión y conviene fijarlo antes de pedírselo, porque condiciona todo lo que se podrá
medir después:

- **Balanceado por lengua.** En BSARD bilingüe la lengua con menos datos pierde **más de 10 puntos
  de exhaustividad** frente a la mayoritaria [3]. Eso predice nuestro problema
  valenciano/castellano; sin balance, no se verá.
- **Con la fuente esperada anotada**, no sólo la respuesta. Sin fuente esperada no hay precisión de
  cita: sólo opinión.
- **Con preguntas que NO deben responderse.** Sin negativos, el eje «contestó y no debía» no se
  puede medir, y es la mitad de la decisión del umbral.
- **Por dominio.** Las 25 actuales son casi todas de estudiantado, matrícula y becas.

---
