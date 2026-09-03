## Bloque OWUI — ❌ DESCARTADO (2026-08-11)

> ## No ejecutar. El bloque se descarta entero; lo que sigue queda como registro.
>
> **Decisión del usuario, tras la conversación de arquitectura del 2026-08-11.** Cuatro
> razones, y la cuarta es la que inclina:
>
> 1. **Se pierde la identidad institucional.** No es un detalle estético: SEC.8.6 y el
>    hallazgo #3 de MAN.2 acaban de construir el sistema de temas —tabla `hub_themes`,
>    cascada plataforma→organización→chatbot, resolución en el widget— precisamente para
>    que el chat público se vea de la institución. Poner OWUI delante tira ese trabajo.
> 2. **Actualizar OWUI cuesta.** Es una aplicación de terceros con su propio ciclo de
>    versiones, y cada salto hay que probarlo contra el adaptador.
> 3. **Consume recursos de la VM.** Con el despliegue en una sola máquina
>    (`docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §2), OWUI y su base propia compiten por
>    la memoria que se acaba de medir en EXT.3.
> 4. **El público al que servía ya está servido de otra forma.** OWUI aportaba una UX de
>    chat rica —historial, adjuntos, cambio de modelo— que tiene sentido para **personal
>    interno**, no para el ciudadano. Para la superficie pública nunca fue la respuesta, y
>    el propio nombre del bloque lo admitía: «carcasa **desechable**».
>
> **Qué se pierde, dicho sin adornos**: el historial de conversaciones y una UX de chat más
> rica para quien use el asistente como herramienta de trabajo. Es real. La alternativa es
> añadirlo al frontend propio cuando haga falta, conservando identidad y una pieza menos que
> mantener.
>
> **Y el adaptador compatible-OpenAI también se aparca.** Tiene valor *independiente* de
> OWUI —permite que cualquier herramienta hable con el asistente— pero solo si aparece un
> consumidor concreto que lo pida. Sin él es código especulativo, que es lo que proscribe la
> norma de «sin código muerto especulativo» de `CLAUDE.md`. Si mañana alguien lo necesita, se
> hace entonces: es pequeño y el andamiaje (scope `chat:completions`, PAT, identidad
> delegada) ya está puesto desde SEC.2.1.
>
> `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md` se conserva: su análisis de qué NO usar de OWUI
> sigue siendo válido si algún día se reabre.

---

> **Contexto original (2026-07-24)**: derivado de `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md`. Open WebUI se adopta como carcasa de chat **desechable e intercambiable** para la capa conversacional; el backend sigue siendo la fuente de verdad. Regla de acoplamiento: **OWUI llama HACIA el backend (API compatible-OpenAI); la gobernanza NUNCA vive en OWUI.** No aplica a expedientes (Fase 3) ni a informes formales, que mantienen interfaz propia.
>
> **Posición en el orden de ejecución** (acordada 2026-07-24): **tras Deploy GCP**, como spike/comparación para el piloto de septiembre. El frontend React de chat ya existe y es la línea de comparación; este bloque levanta la carcasa OWUI sobre el MISMO backend desplegado. (La decisión §9 contempla adelantarlo si se quisiera descartar trabajo de chat-UI en CAL; el orden acordado aquí es post-deploy.)
>
> **Estado**: relación de prompts (1ª pasada, 2026-07-24). Pendiente 2ª pasada de detalle verbatim cuando llegue su turno.

### Propósito del bloque

1. Exponer una **superficie compatible-OpenAI** (`/v1/models`, `/v1/chat/completions`) sobre el grafo de chat existente, sin reimplementar RAG ni gobernanza.
2. Preservar el **contrato de citas (P6)** y la **anonimización (P7)** en el trayecto del backend, nunca en la carcasa.
3. Entregar un **Pipe delgado** de Open WebUI (transporte + presentación) y la guía de despliegue edge (P8).
4. Habilitar la **comparación UX** React vs OWUI sobre idéntico backend (insumo de la decisión de carcasa).

### Decisiones de diseño

- **El adaptador es traducción de protocolo, no lógica.** Reusa el mismo grafo que `hub_chat.py` (CoreGraph tras RAG.2); si duplica retrieval, generación o filtrado, está mal.
- **Un chatbot = un "model" de OpenAI.** `/v1/models` lista los chatbots visibles al PAT; el campo `model` de la petición resuelve a `chatbot_id`.
- **Auth máquina por PAT** con scope nuevo `chat:completions` (servir a usuarios finales), distinto de `chat:test` (superficie de prueba admin). La autorización usuario↔org↔chatbot del Bloque SEC sigue aplicando.
- **La gobernanza no se toca ni se reimplementa**: P6/P7/P9 se heredan del grafo. Ni el adaptador ni el Pipe pueden añadir ni saltarse controles.
- **Deploy: edge** para el adaptador; el Pipe vive en OWUI (edge). OWUI y su BD son dato operacional edge (P8), no sincronizado al cloud.

### Mapa de ejecución

| # | Prompt | Título | Depende de | Modelo sugerido |
|---|--------|--------|------------|-----------------|
| 1 | OWUI.1 | Superficie compatible-OpenAI (`/v1/models` + `/v1/chat/completions`) sobre el grafo | RAG.2 (grafo consolidado), AUTH ✅ | **Opus** |
| 2 | OWUI.2 | Citas (P6) y anonimización (P7) en la respuesta compatible-OpenAI | OWUI.1 | **Opus** |
| 3 | OWUI.3 | Pipe delgado de OWUI + despliegue edge + validación e2e de gobernanza | OWUI.2 | Sonnet |

### Reglas duras del bloque

- Prohibido reimplementar retrieval/generación/anonimización en el adaptador o el Pipe: se reusa el grafo (grep de ausencia de llamadas directas a `retriever`/`model_factory`/estrategias en el adaptador).
- Sin scope muerto: `chat:completions` se consume en OWUI.1 o no se añade.
- El adaptador debe producir gobernanza **idéntica** a `hub_chat` para la misma entrada (test de equivalencia, OWUI.2).
- Todo router nuevo etiquetado `Deploy: edge` y registrado en `_register_edge`.

### Prompts del bloque (relación — 1ª pasada 2026-07-24)

---

### Prompt OWUI.1 (RED/GREEN) — Superficie compatible-OpenAI sobre el grafo

**Modelo sugerido**: **Opus** — traducción de protocolo SSE↔OpenAI con decisiones de mapeo (chunks de streaming, historial, model→chatbot).

```
# PROMPT OWUI.1 (RED/GREEN) — /v1/models + /v1/chat/completions compatible-OpenAI
# Deploy: edge

## Router nuevo (server/app/api/v1/openai_compat.py) — prefix /v1, Deploy: edge
- GET /v1/models: lista los chatbots visibles al PAT como objetos OpenAI
  {id: <chatbot_id o slug>, object: "model", owned_by: <organizacion>}.
- POST /v1/chat/completions: acepta {model, messages:[{role,content}], stream: bool}
  (tolerar e ignorar temperature/max_tokens/etc.).
  - Resolver model -> chatbot_id (404 si no visible al PAT).
  - Tomar el último mensaje 'user' como message; pasar el historial previo tal cual
    (insumo de RAG.10 query rewriting — NO recortar aquí).
  - Invocar EL MISMO grafo que hub_chat.py (CoreGraph tras RAG.2). Prohibido instanciar
    retriever/model_factory/estrategias directamente.

## Streaming (stream=true) — SSE compatible-OpenAI
- Traducir eventos internos -> chunks OpenAI:
  token{delta} -> {object:"chat.completion.chunk", choices:[{delta:{content}}]}.
  done -> chunk final finish_reason "stop" + linea [DONE].
  status -> se omite. error -> chunk de error OpenAI.
- Reusar _SSE_HEADERS de hub_chat.

## No-streaming (stream=false)
- Acumular tokens -> {object:"chat.completion", choices:[{message:{role:"assistant",content}}],
  usage?} (usage best-effort si el grafo lo expone; si no, omitir).

## Auth (server/app/core/auth/pat/scopes.py)
- Añadir CHAT_COMPLETIONS = "chat:completions" a ALL_SCOPES + techo de rol
  (superadmin/admin, mismo criterio que CHAT_TEST). Endpoint con require_scopes("chat:completions").
- Reusar get_current_user; la autorización usuario<->org<->chatbot del Bloque SEC aplica igual
  que en hub_chat (extraer helper compartido, no duplicar reglas).

## Actor efectivo y guardas (ampliación 2026-07-27)

El Pipe de OWUI usa **un PAT de servicio**: sin resolver el actor, todo el consumo del piloto
se cargaría a un único sujeto y la cuota por usuario sería inútil. El adaptador **no** implementa
nada de esto: consume los helpers de SEC.2.1/SEC.4/SEC.4.1.

- `actor = resolve_effective_actor(request, principal)` (SEC.2.1) al principio del handler.
  El PAT del Pipe debe portar `chat:onbehalf` además de `chat:completions`.
- Guardas, en el mismo orden que hub_chat y el widget:
    assert_chatbot_access(actor, chatbot, via='session')
    assert_chatbot_available(session, chatbot, now)
    assert_within_quota(session, actor, chatbot, via='session')
- `GET /v1/models` lista **solo los chatbots que `assert_chatbot_access` permite al actor
  efectivo** — no "todos los del PAT". Así el usuario de OWUI ve exactamente lo que puede
  usar y **OWUI no decide nada**: no se usan sus Groups para autorizar.
- Traducción de errores al formato OpenAI (si no, OWUI muestra un fallo opaco):
    429 QUOTA_EXCEEDED    -> {"error":{"type":"rate_limit_exceeded","message":<qué cuota, cuánto queda>}}
    403 CHATBOT_UNAVAILABLE -> {"error":{"type":"invalid_request_error","message":<unavailable_message>}}
    403 ACCESS_MODE_FORBIDDEN / 401 ACTOR_TOKEN_INVALID -> error OpenAI equivalente, sin filtrar
    detalles internos de tenencia.
  En streaming, el error se emite como chunk de error + `[DONE]`, no cortando la conexión.
- El `usage` de la respuesta no-streaming se rellena con los tokens reales de SEC.4 cuando el
  proveedor los expone (deja de ser "best-effort" en ese caso).

## Registro
- main.py: _register_edge; docstring "Deploy: edge".

## Tests (RED primero) — tests/modules/agents_hub/integration/test_openai_compat.py
# should_list_visible_chatbots_as_openai_models
# should_map_model_field_to_chatbot_id
# should_404_when_model_not_visible_to_pat
# should_stream_openai_chunks_with_content_deltas
# should_end_stream_with_stop_and_done_sentinel
# should_return_chat_completion_object_when_not_streaming
# should_require_chat_completions_scope
# should_invoke_same_graph_as_hub_chat            (spy: sin acceso directo a retriever)
# should_pass_history_messages_through
# --- ampliación 2026-07-27 ---
# should_list_only_chatbots_allowed_by_access_mode        (authenticated/restricted respetados)
# should_hide_public_anon_only_chatbots_from_models_list_when_actor_lacks_org
# should_charge_usage_to_delegated_actor_not_pat_owner
# should_translate_quota_429_to_openai_rate_limit_error
# should_translate_unavailable_403_to_openai_invalid_request
# should_emit_error_chunk_and_done_when_failing_mid_stream
# should_not_leak_tenancy_details_in_error_messages

## Criterio de done
- [ ] Un cliente OpenAI genérico (SDK openai apuntado al backend) obtiene respuesta en stream
- [ ] Scope chat:completions consumido; sin scope muerto
- [ ] grep: el adaptador no importa VectorRetrievalStrategy/model_factory directamente
- [ ] grep: el adaptador no reimplementa acceso, disponibilidad ni cuota — solo llama a los helpers
- [ ] Dos usuarios distintos vía el mismo PAT consumen cuotas distintas (verificado en test)
```

---

### Prompt OWUI.2 (RED/GREEN) — Citas (P6) y anonimización (P7) en la respuesta compatible-OpenAI

**Modelo sugerido**: **Opus** — el punto donde la gobernanza cruza a la carcasa; decisiones de contrato.

```
# PROMPT OWUI.2 (RED/GREEN) — sources->citations + preservación de anonimización
# Deploy: edge

## Citas (P6) — mapeo del contrato interno a la respuesta OpenAI
- El 'done' interno lleva sources[]. Emitirlas en un formato consumible por el Pipe:
  campo custom en el chunk final (p.ej. choices[].delta.sources) y/o al estilo OWUI.
  Documentar EXACTAMENTE el formato que el Pipe de OWUI.3 espera.
- Enforce del contrato de disponibilidad: si el grafo devuelve respuesta SIN fuentes
  verificables -> respuesta de indisponibilidad (la que ya produce el grafo), NUNCA texto
  libre. El adaptador no puede saltarse este control.

## Anonimización (P7) — se ejecuta en el grafo, no en el adaptador ni en el Pipe
- El adaptador pasa por el MISMO trayecto que hub_chat (RunAnonymizationContext / hooks
  pre/post-LLM, Fase 13) según lo aplique el grafo. No se anonimiza en el adaptador.
- No exponer mapas de reversión en la respuesta ni en trazas enviadas al cloud (P8).

## Test de equivalencia de gobernanza (clave del bloque)
- Para una misma entrada, el adaptador y hub_chat producen: mismas sources, mismo
  comportamiento de indisponibilidad y misma anonimización del texto que llega al LLM.

## Tests (RED primero) — test_openai_compat_governance.py
# should_expose_sources_in_openai_response
# should_return_unavailability_when_no_verifiable_sources
# should_not_emit_free_text_without_sources
# should_apply_same_anonymization_path_as_hub_chat
# should_not_leak_reversal_map_in_response_or_cloud_trace
# should_match_hub_chat_governance_for_same_input   (equivalencia)

## Criterio de done
- [ ] Respuesta sin fuentes -> indisponibilidad, verificado por el cliente OpenAI
- [ ] Entrada con PII -> el LLM recibe texto anonimizado (igual que hub_chat)
- [ ] Formato de citas documentado para OWUI.3
```

---

### Prompt OWUI.3 (RED/GREEN) — Pipe delgado + despliegue edge + validación e2e

**Modelo sugerido**: **Sonnet** — Pipe de transporte + guía de despliegue + checklist e2e.

```
# PROMPT OWUI.3 — Pipe delgado de Open WebUI + despliegue edge + validación
# Deploy: edge (OWUI vive en el edge)

## Pipe/Function de OWUI (owui/pipe_govhub.py, versionado en este repo)
- Function tipo "pipe" que llama a POST {BACKEND}/v1/chat/completions con el PAT
  (scopes chat:completions + chat:onbehalf), en streaming, y mapea el formato de citas de
  OWUI.2 al mecanismo de citas/sources de Open WebUI.
- SIN lógica de gobernanza: solo transporte y presentación. Prohibido anonimizar, filtrar o
  decidir disponibilidad en el Pipe (grep de ausencia).
- Config del Pipe: BACKEND_URL, PAT (secreto), ACTOR_SIGNING_SECRET (secreto), timeout. Nada más.

## Identidad delegada (ampliación 2026-07-27 — decisión (a) del usuario)
- El Pipe construye la cabecera `X-GovGenAI-Actor` a partir del contexto `__user__` que le
  entrega OWUI (id, email, y grupos si están disponibles) y la firma con
  `ACTOR_SIGNING_SECRET` (HS256, `exp` <= 300 s, `aud` = "govgenai-backend").
- **Esto no es gobernanza, es identificación de transporte**: el Pipe declara *quién*
  pregunta; el backend decide *qué puede hacer* (SEC.2.1) y *cuánto le queda* (SEC.4). El
  Pipe no consulta cuotas ni interpreta el 429: solo lo muestra.
- Alternativa descartada: un PAT por usuario. No escala a cientos de personas ni sobrevive a
  las bajas, y multiplicaría los secretos a rotar.
- Si el Pipe no firma la cabecera (o el PAT no tiene `chat:onbehalf`), el backend carga todo
  el consumo al dueño del PAT: **el despliegue queda funcional pero sin cuota por persona**.
  Debe verificarse explícitamente en el checklist, no asumirse.

## Despliegue (docs/OWUI_INTEGRATION.md)
- OWUI dentro del perímetro edge; su BD (conversaciones/ficheros) es dato operacional edge (P8),
  no sincronizado al cloud. Versión de OWUI fijada y probada antes de actualizar.
- SSO SAML compartido para humanos (AUTH); PAT solo para el Pipe.
- Cómo dar de alta un chatbot como "model" en OWUI.
- **Sección obligatoria "Lo que NO se usa de Open WebUI, y por qué"** (si no se escribe,
  alguien lo intentará dentro de seis meses):
    - **Groups/RBAC de OWUI para autorizar chatbots** -> NO. La autorización es gobernanza y
      vive en `assert_chatbot_access` (SEC.2.1). OWUI solo muestra lo que `/v1/models`
      devuelve. Además su modelo de permisos es aditivo y sin "deny", así que no puede
      expresar `restricted` fail-closed.
    - **LiteLLM de sidecar para cuotas por usuario** -> NO. Duplicaría `model_factory`,
      añadiría una pieza más al edge y sacaría el control de gasto del perímetro auditado.
      Las cuotas viven en SEC.4.
    - **Plugins de token-tracking de terceros dentro de OWUI** -> NO. Es la Opción B ya
      descartada en `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md` §3: pone gobernanza dentro del
      ciclo de releases de un tercero.
    - Contexto: las cuotas por usuario **no existen de forma nativa en OWUI** (peticiones
      abiertas upstream), de ahí que la tentación de resolverlas allí sea real.

## Validación e2e (checklist; el Pipe corre fuera de la suite pytest)
- [ ] Citas visibles en la UI de OWUI, resolubles a su fuente (P6).
- [ ] Entrada con PII: en trazas, el LLM recibió texto anonimizado (P7).
- [ ] Sin PII ni mapas de reversión en trazas enviadas al cloud (P8).
- [ ] Respuesta sin fuentes -> indisponibilidad también en OWUI.
- [ ] Comparación UX React vs OWUI sobre el mismo backend (notas para la decisión de carcasa).
- [ ] **Un chatbot en modo `authenticated` de otra organización NO aparece en el selector de
      modelos de OWUI** (el filtrado de `/v1/models` funciona de verdad).
- [ ] **Dos usuarios distintos de OWUI consumen cuotas distintas** con el mismo PAT del Pipe:
      agotar la cuota del usuario A no afecta al usuario B (verifica la cadena completa
      Pipe -> cabecera firmada -> resolve_effective_actor -> HubUsageCounter).
- [ ] Al agotar la cuota, OWUI muestra un mensaje legible de límite alcanzado, no un fallo opaco.
- [ ] Un chatbot caducado (`valid_until` pasado) muestra en OWUI el `unavailable_message` del admin.

## Tests (RED primero) — lo testeable del lado backend/formato
# should_document_citation_format_consumed_by_pipe
# should_reject_pipe_config_without_pat
# should_reject_pipe_config_without_actor_signing_secret
# should_sign_actor_header_from_owui_user_context
# should_not_contain_governance_logic_in_pipe        (grep: sin anonimización/cuota/filtrado)

## Criterio de done
- [ ] Pipe funcional contra el backend desplegado; citas visibles en OWUI
- [ ] docs/OWUI_INTEGRATION.md con la guía de despliegue edge y la sección "Lo que NO se usa"
- [ ] Checklist e2e de gobernanza superado y anotado
- [ ] Cuota por persona verificada end-to-end (no solo por PAT)
```

### Continuación tras el bloque OWUI

Con la carcasa OWUI validada sobre el backend desplegado, la decisión de qué carcasa(s) sirve cada caso de uso se toma con datos del piloto (ver `docs/DECISION_OPENWEBUI_CARCASA_CHAT.md` §9). Expedientes (Fase 3) e informes formales mantienen interfaz propia.

---
