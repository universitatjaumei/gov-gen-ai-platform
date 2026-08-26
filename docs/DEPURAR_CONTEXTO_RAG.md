# Depurar el contexto del chatbot con el modo bypass

Cuando una respuesta sale mal, la pregunta casi siempre es la misma: **¿qué contexto recibió
el modelo?**. Antes de RAG.11 solo había dos formas de contestarla —leer trazas en Langfuse o
reproducir la consulta a mano contra la base de datos— y las dos cuestan más que el problema.

El modo bypass ejecuta el pipeline **entero** (detección de idioma → reescritura de consulta →
recuperación → gate de calidad → empaquetado del contexto) y **se detiene justo antes de
invocar al modelo**, devolviendo lo que se iba a enviar. Cero tokens de LLM.

## Cómo se pide

```bash
curl -s -X POST http://localhost:8000/api/v1/hub/chat/<CHATBOT_ID> \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"message": "quant cobro de dieta per anar a Madrid?", "debug_bypass": true}' | jq
```

La respuesta es **JSON, no SSE**: no se genera texto, así que no hay nada que transmitir en
trozos, y quien depura quiere el objeto entero de una vez.

## Quién puede pedirlo

| Principal | Condición |
|---|---|
| Sesión humana (JWT) | rol `admin` o `superadmin` |
| Token de máquina (PAT) | debe portar el scope `chat:debug` |
| Widget público / rol `user` | **403 siempre** |

Un PAT **no hereda** el permiso de quien lo emitió: lo lleva explícito o no lo lleva. Es el
sentido de acotar un token de máquina, y por eso el gate no es un `require_scopes` a secas —
ese deja pasar cualquier sesión JWT, incluida la del widget.

El bypass enseña el system prompt completo y la configuración resuelta del chatbot, que es
más de lo que concede poder charlar con él; de ahí que `chat:debug` sea un scope aparte de
`chat:test`.

## Qué devuelve

```jsonc
{
  "system_prompt": "…",                  // el prompt de sistema tal cual, ya compuesto
  "messages": [                          // lo que se iba a mandar, en orden
    {"role": "system",  "content": "…"},
    {"role": "user",    "content": "…"}
  ],
  "packed_context": {
    "evidencias": [ {"document_id": "…", "title": "…", "url": "…", "excerpt": "…", "score": 0.9} ],
    "dropped_count": 0,                  // evidencias que NO cupieron en el presupuesto
    "total_tokens": 72,
    "context_token_budget": 128000
  },
  "sources": [ … ],                      // las mismas evidencias, en el shape del evento done
  "rewritten_query": null,               // la consulta con la que se BUSCÓ, si hubo reescritura
  "resolved_config": { … },              // instantánea de la cascada Plataforma→Org→Chatbot
  "quality_gate": {"score": 0.011, "passed": false}
}
```

## Cómo leerlo

**Empieza por `quality_gate` y `packed_context`.** Entre los dos explican la mayoría de las
respuestas malas:

- `passed: false` → en una consulta normal esto habría ido al **fallback**, y el usuario
  habría visto «no puedo responder» en vez de una respuesta. El `score` es la media de las
  puntuaciones de la evidencia recuperada, así que un valor bajo es un problema de
  *recuperación*, no de redacción.
- `dropped_count > 0` → el presupuesto de contexto recortó evidencia. Si lo que falta en la
  respuesta está entre lo descartado, el problema es el presupuesto o el orden, no el modelo.
- `evidencias` vacío o con documentos que no vienen a cuento → el problema está en el
  retriever: mira `resolved_config.min_retrieval_score`, `retrieval_mode` y `reranker_enabled`.

**`rewritten_query` distingue tres situaciones** que se confunden con facilidad: `null`
significa que **no hubo reescritura** —o está apagada, o era el primer turno, o el reescritor
falló y se buscó con el mensaje original—; un valor distinto significa que se buscó con **eso**
y no con lo que el usuario escribió. Si la recuperación no tiene sentido, comprueba primero
con qué se buscó de verdad.

**`resolved_config` es la mitad de las explicaciones.** La configuración efectiva sale de tres
capas (Plataforma → Organización → Chatbot) y un `NULL` en la capa de abajo significa
«heredar». Ver el resultado resuelto evita el rato clásico de mirar el chatbot, no encontrar
el valor y suponer el de plataforma.

## El gate informa, no desvía

En bypass, una puntuación por debajo del umbral **no manda al fallback**: se anota en
`quality_gate.passed` y el pipeline sigue hasta construir el prompt. Es deliberado — si
desviara, el caso que más interesa depurar (puntuación baja) sería justo el único que no
enseña ningún prompt.

## Lo que el bypass NO hace

- **No persiste `HubInteraction`.** Es inspección, no conversación: contarla ensuciaría las
  métricas de uso con consultas de depuración.
- **No llama al modelo**, ni «solo para una cosa». Hay un test con un espía que cuenta
  invocaciones y exige cero; en cuanto llamara, dejaría de ser gratis y dejaría de ser
  inspección.
- **No evita el resto de guardas.** Si el corpus está embebido con otro modelo, el bypass
  devuelve el mismo `409` que una consulta normal (RAG.9): depurar no es motivo para leer un
  espacio vectorial que no es el del corpus.

## De dónde sale la nota del gate (RES.1, 2026-08-25)

**Es la puntuación del MEJOR fragmento recuperado, no la media de todos.** La pregunta que hace el
filtro es «¿tengo al menos una fuente buena?».

Hasta el 2026-08-25 era la media, y eso tenía una consecuencia que nadie decidió: cada fragmento
flojo que entraba bajaba la nota, así que **`retrieval_top_k` —un mando de amplitud— decidía de
rebote cuántas preguntas se contestan**. Medido sobre las dos baterías reales: con la media, 18 de
25 y 2 de 7; con el mejor, 20 y 4, y **con cualquier anchura**. El caso que lo retrata es `SGE-01`,
con un fragmento de 0,637 y un umbral de 0,50: se rendía porque los tres de detrás bajaban la media
a 0,371.

Dos cosas que conviene tener presentes al depurar:

- **`quality_threshold` cambió de significado.** Un valor puesto antes de esa fecha se eligió con el
  otro criterio, así que con el mismo número el filtro es ahora **más permisivo**.
- **`quality_source` dice qué fragmento fijó la nota** (título y puntuación), y sale en la traza.
  Con la media no había nada que señalar; con el mejor sí, y sin ese dato una respuesta rechazada
  era un número sin explicación.

Lo que **no** cambió: la penalización por número de resultados
(`len(items) < min_retrieval_results` ⇒ nota × 0,5) mide otra cosa y sigue igual. Y
`min_retrieval_score` actúa sobre la similitud coseno en la consulta SQL, que es **otra escala**: no
acota la puntuación del reranker que el gate compara.

## La nota volvió a medir algo (HIB.J, 2026-08-26)

RES.1 arregló *qué fragmento* fija la nota. HIB.J arregló *qué número* es esa nota, que sin
reranker no medía nada.

**El defecto, medido.** Al apagar el reranker en HIB.A, la nota pasó a ser la fusión RRF
normalizada por su techo teórico. Sobre las 25 consultas del lote valía **exactamente 0,7 en las
25**: un solo valor distinto. Y 0,7 es `vector_weight`. El motivo no es un número escrito a mano:
el ganador de la fusión es siempre el fragmento de rango 1 de la rama vectorial, que aporta
`vector_weight · 1/(k+1)`, y al dividir por `RRF_MAX_SCORE = 1/(k+1)` queda `vector_weight`. El
techo teórico exige que **el mismo fragmento** salga por vector y por léxico, y con troceado fino
no ocurre nunca.

Una puerta que lee una constante no es una puerta: con umbral ≤ 0,7 pasaba todo, con umbral > 0,7
no pasaba nada. Es el mismo defecto que el `score = 1.0` fijo del modo agéntico, por otra vía.

**El arreglo.** La nota es ahora la **similitud coseno** del mejor fragmento del documento
(`SearchResult.relevance`, que `hybrid_search` conserva en vez de perderla al sobrescribir
`score`). La **ordenación** sigue siendo la fusión RRF, que es lo que combina léxico y vector.
Con reranker la nota sigue siendo la del reranker. Efecto colateral bienvenido: con y sin
reranker el umbral significa lo mismo, así que desaparece la asimetría que HIB.A tuvo que
declarar como trampa al comparar.

**El segundo defecto, también medido.** El pool de candidatos era
`pool_size(top_k) if reranker else top_k`, así que apagar el reranker lo encogió de 30 fragmentos
a 3 —dos cambios en una línea—. Como después se agrupa por documento, `top_k = 3` dejaba de
significar tres documentos. Ahora el pool es `candidate_k` (nulo = `pool_size(top_k)`) y no
depende del reranker, y `top_k` se aplica **tras agrupar**, en documentos.

| Con `top_k = 3` | Antes | Después |
|---|---|---|
| Valores distintos de la nota (25 consultas) | **1** | **25** |
| Documentos por consulta | 1 doc ×6, 2 ×13, 3 ×6 | 2 doc ×1, 3 ×24 |
| Consultas con un solo documento | **6 de 25** | **0** |

**Punto de operación provisional** (Normativa UJI): `retrieval_top_k = 3`, `candidate_k` nulo
(⇒ 30), `quality_threshold` **0,40 → 0,60**.

La curva completa, sobre las notas medidas: umbrales de 0,40 a 0,68 no callan ninguna; 0,70 calla
3; 0,72 calla 4; 0,74 calla 7; 0,76 calla 17; 0,80 calla las 25. Las notas van de 0,6917 a 0,7854.

**Por qué 0,60 y por qué es provisional.** Las 25 del lote son preguntas reales de informadores y
**todas tienen respuesta en el corpus** —lo comprobó el bloque RES por SQL—, así que en este lote
cada silencio es un fallo y la medición no puede elegir el umbral: cualquier valor por encima de
0,68 sólo añade silencios falsos. El 0,60 se elige porque queda por debajo del mínimo observado
con margen (no depende de que ese mínimo sea representativo) y porque deja la puerta **capaz** de
actuar si algún día llega evidencia con relevancia realmente baja, cosa que en este lote no pasa.
En la escala nueva, el 0,40 anterior es un umbral que no podría actuar ni con evidencia mala.

**Sobre el lote no cambia nada**: ninguna de las 25 cae por debajo de 0,60. El cambio tiene efecto
potencial fuera del lote, y eso es lo único que se afirma. El punto definitivo se elige con el
lote de HIB.G, que tendrá negativos, y con el piloto.

Instrumental: `_local/golden/rejilla_hibj.py` → `_local/golden/rejilla_hibj.json`.
