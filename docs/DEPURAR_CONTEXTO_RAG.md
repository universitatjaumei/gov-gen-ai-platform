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
