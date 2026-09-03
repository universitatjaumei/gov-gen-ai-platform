## Bloque RHR — Revisión humana de las respuestas del asistente interno (PENDIENTE)

> **Contexto**: Gerencia quiere un asistente **para funcionarios, con identificación**, y poder
> **revisar las respuestas** para valorar si son adecuadas o si conviene reformular las FAQ.
> Se evaluó adoptar Open WebUI para esto y **se descartó** (ver bloque OWUI): OWUI es una
> interfaz de chat y no aporta nada de la revisión, que es la parte que se pide; además
> duplicaría el registro de conversaciones y debilitaría la cadena de identidad justo en un
> sistema cuyo propósito es auditar quién preguntó qué.
>
> **Lo que ya existe y NO hay que construir** (comprobado en el código el 2026-08-11):
>
> | Necesidad | Dónde está |
> |---|---|
> | Asistente restringido a funcionarios identificados | `access_mode: restricted` + `allowed_saml_groups` (SEC.2.1) sobre el SSO SAML del bloque AUTH. **Es configuración, no desarrollo** |
> | Cada pregunta y respuesta registrada | `HubInteraction` (pregunta, respuesta, quién, `fallback_reason`) |
> | Pantalla de revisión con exportación | `ReportsPage.tsx` sobre `GET /hub/feedback/{chatbot_id}/review`, con estrellas, gráfico y CSV |
> | Bucle de la respuesta mala al contenido | Detector de huecos (RAG.14): agrupa las conversaciones que salieron mal en huecos de corpus |
>
> **Lo que falta es lo que planifica este bloque.**

---

### Prompt RHR.1 (RED/GREEN) — El veredicto de quien revisa, sobre conversaciones reales

**Modelo sugerido**: **Sonnet** — el patrón ya existe en el proyecto y se replica; sin
decisiones de diseño abiertas.

**Objetivo**: hoy `feedback_score`/`feedback_text` de `HubInteraction` es la valoración del
**usuario final**. No hay forma de que Gerencia diga «esta respuesta no es adecuada» y quede
constancia de quién lo dijo. El patrón existe literalmente en el proyecto —`HubTestRun` tiene
`verdict` (good/bad/mixed), `verdict_note` y `verdict_by` desde RAG.13—, pero solo sobre
escenarios de prueba, no sobre lo que se le respondió a una persona de verdad.

```
# PROMPT RHR.1 (RED/GREEN) — Que revisar deje rastro, y no sea leer un CSV
# Deploy: edge

## Modelo (operational_models.HubInteraction)
- `review_verdict`: 'good' | 'bad' | 'mixed', nullable. Nullable = **sin revisar**, que es
  el estado por defecto y el que alimenta la cola.
- `review_note`: texto, nullable — por qué. Sin esto el veredicto no sirve para reformular
  nada: «mal» no dice qué había que cambiar.
- `review_by`, `review_at`.
- Migración Alembic. Mismos nombres y valores que `HubTestRun` **a propósito**: dos
  vocabularios distintos para la misma idea acabarían divergiendo.

## Endpoint
- `PATCH /hub/feedback/interactions/{interaction_id}/review` con el veredicto y la nota.
- Guarda de tenencia como el resto (SEC.8.1): se resuelve la interacción -> chatbot ->
  organización, y **el revisor tiene que ser de ella**. Estas conversaciones llevan
  preguntas de personas identificadas.
- `GET /hub/feedback/{chatbot_id}/review` gana filtros: `review_status`
  (pending|reviewed|all) y `verdict`. Por defecto **pending**: la cola de revisión es lo que
  falta por mirar, no todo el historial.

## Frontend (ReportsPage)
- Botones de veredicto y campo de nota por fila; el estado se ve sin abrir nada.
- Filtro por estado y por veredicto. Contador de pendientes.
- i18n es/ca/en, sin cadenas sueltas.
- La exportación a CSV incluye las columnas nuevas: es lo que Gerencia se lleva a una
  reunión.

## Tests (RED primero)
# should_default_to_unreviewed
# should_record_who_reviewed_and_when
# should_require_a_note_when_the_verdict_is_bad     (un «mal» sin motivo no reformula nada)
# should_list_only_pending_interactions_by_default
# should_forbid_reviewing_an_interaction_of_another_organization   (va al gate de SEC.8.1)
# should_export_the_verdict_columns_to_csv          (Vitest)
# should_show_the_pending_count                     (Vitest)
```

---

### Prompt RHR.2 (CONDICIONAL) — Hilos de conversación persistentes

**Modelo sugerido**: **Opus** — toca el contrato del chat, el modelo de datos y el frontend a
la vez, y hay que decidir qué es una conversación sin romper la contabilidad por turno de
SEC.4.

> **⚠️ NO EJECUTAR TODAVÍA. Prompt con disparador.**
>
> Hoy no hay hilo: `HubInteraction` no tiene identificador de conversación y el endpoint de
> chat **recibe el historial del cliente** (`history`, máximo 50 turnos). O sea que el estado
> vive en el navegador y no se puede retomar mañana.
>
> **Esto es lo único que OWUI habría dado hecho**, y por eso el bloque OWUI no se descartó a
> la ligera. Pero es también el trabajo caro, y no sabemos si hace falta.
>
> **Disparador**: ejecutar solo si el piloto del asistente interno muestra que los
> funcionarios lo piden — es decir, si aparece la queja de «he perdido lo que pregunté ayer».
> Si lo que hacen es preguntar y obtener una respuesta con su fuente, esto no hace falta y
> construirlo sería añadir superficie por si acaso.
>
> **Pregunta que decide, y es para Gerencia**: ¿imaginan «pregunto y obtengo una respuesta
> con su fuente» o **un espacio de trabajo conversacional** —hilos largos, adjuntos, prompts
> guardados, compartir conversaciones entre compañeros—? Si es lo segundo, hay que
> reconsiderar OWUI, porque sería reconstruir un producto entero.

```
# PROMPT RHR.2 (CONDICIONAL) — Una conversación, no una ristra de turnos sueltos
# Deploy: edge

## Lo que hay que decidir antes de escribir código
- Qué es una conversación: `HubConversation` propia, o un `conversation_id` en
  `HubInteraction`. Lo segundo es menos tabla y suficiente para retomar; lo primero permite
  título, archivado y compartir. **Decidir con el caso real, no antes.**
- Qué pasa con el historial que hoy manda el cliente: si el servidor lo reconstruye, el
  contrato del endpoint cambia y hay que mirar el widget público, que no tiene sesión.
- **La contabilidad de SEC.4 se cuenta por turno y por actor**: un hilo no puede convertirse
  en la unidad de cuota sin rehacer eso.

## Y lo que NO cambia
- La revisión de RHR.1 sigue siendo por interacción: Gerencia valora respuestas, no hilos.
- Un chatbot `public_anon` no gana historial por esto: no hay a quién atribuirlo.
```

---
