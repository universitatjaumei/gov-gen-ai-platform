## Bloque SEC — Endurecimiento de seguridad (Subfase 1.B, PENDIENTE, BLOQUEANTE DE DESPLIEGUE)

> **Contexto**: hallazgos de la auditoría de seguridad (`docs/VALORACION_PROYECTO.md` §4). Se ejecuta **después de ROL** (usa la nomenclatura nueva: rol `admin`, `organizacion_id`) y **antes de Deploy GCP**. Todo `Deploy: cloud|edge|shared` según el router.

---

### Prompt SEC.1 (RED/GREEN) — Login de Admin con verificación de contraseña [A1]

**Modelo sugerido**: **Sonnet** — patrón conocido (bcrypt ya existe para superadmin); alcance cerrado.

**Objetivo**: Cerrar el bypass de autenticación del login de Admin (ex-partner), que hoy emite JWT sin comprobar contraseña. `AdminAccount` (ex-`PartnerAccount`) ni siquiera tiene campo de hash.

```
# PROMPT SEC.1 (RED/GREEN) — Contraseña obligatoria en login de Admin
# Deploy: cloud

## Cambios
- database/models.py: añadir `hashed_password: str` a AdminAccount (ex-PartnerAccount).
- Migración Alembic: add_column nullable + backfill NULL → cuentas sin password quedan
  DESHABILITADAS para login local (deben usar SSO/PAT o que un superadmin fije password).
- routers/auth_router.py::login_admin: verificar con core/security.verify_password
  (mismo patrón que login_superadmin). Rechazar si hashed_password es NULL.
- Endpoint para que superadmin establezca/resetee la contraseña de un Admin (o reutilizar
  el alta con password hasheado). Mensaje y tiempo de respuesta IDÉNTICOS para
  "cuenta inexistente" y "contraseña inválida" (no filtrar existencia).

## Tests (RED primero) — tests/api/test_auth_login.py
# should_reject_admin_login_without_password_field         (regresión del bug A1)
# should_reject_admin_login_with_wrong_password
# should_accept_admin_login_with_correct_password
# should_reject_admin_with_null_hashed_password
# should_return_identical_error_for_unknown_and_wrong_password
```

---

### Prompt SEC.2 (RED/GREEN) — Aislamiento multi-tenant: claim de organización + filtrado + gate de CI [A2]

**Modelo sugerido**: **Opus** — decisión de diseño del modelo de tenencia + refactor transversal de todos los endpoints con datos de organización + test de aislamiento que debe convertirse en gate.

**Objetivo**: Impedir el acceso horizontal entre organizaciones. Hoy el JWT no lleva la organización y los endpoints no filtran: cualquier admin lista/edita/borra chatbots de todos y lee conversaciones (posible PII ciudadana) de otros.

```
# PROMPT SEC.2 (RED/GREEN) — Aislamiento por organización
# Deploy: shared (claim) + edge/cloud (según router)

## Modelo de tenencia (decisión)
- UserInfo (core/auth/models.py) añade `organizacion_ids: list[str]`:
    - superadmin → lista vacía = acceso a TODAS (comodín).
    - admin → ids de las organizaciones que gestiona.
    - user → la organización a la que pertenece (1 elemento).
- El claim se rellena al emitir el JWT (login superadmin/admin, ACS SAML, y PAT:
  PatPrincipal hereda organizacion_ids del owner).

## Capa de filtrado (única, no repetir en cada endpoint)
- core/auth/tenancy.py: `assert_org_access(principal, organizacion_id)` → 403 si no procede
  (superadmin siempre pasa). `scope_query_to_orgs(stmt, principal, model)` → añade
  WHERE organizacion_id IN (...) salvo superadmin.
- Aplicar en: hub_chatbots_router (list/get/update/delete/corpus-stats/regenerate-chunks),
  hub_chat (conversar solo con chatbots de la propia organización),
  hub_feedback (revisar solo interacciones de chatbots propios),
  hub_themes_router (derivar organizacion_id del principal, NO del body del cliente),
  hub_ingestion_router (cierra el TODO de autorización en :91).

## Tests (RED primero) — tests/api/test_tenant_isolation.py  ← GATE DE CI
# should_list_only_own_org_chatbots                        (admin A no ve chatbots de org B)
# should_forbid_get_chatbot_of_other_org                   (403)
# should_forbid_update_delete_chatbot_of_other_org         (403)
# should_forbid_reading_feedback_of_other_org
# should_forbid_chatting_with_chatbot_of_other_org
# should_ignore_client_supplied_org_id_in_themes           (usa el del token)
# should_allow_superadmin_cross_org_access
# should_scope_ingestion_to_own_org

## Criterios de cierre
- [ ] test_tenant_isolation.py añadido al job de CI como gate obligatorio
- [ ] Ningún endpoint de datos de organización hace `session.get(Model, id)` sin pasar por assert_org_access
```

---

### Prompt SEC.2.1 (RED/GREEN) — Modo de acceso por chatbot + identidad delegada

**Modelo sugerido**: **Opus** — decide el modelo de visibilidad (enum + grupos SAML), refactoriza los tres caminos de conversación tras un único helper, y fija un contrato criptográfico de identidad delegada con riesgo de escalada si se diseña mal.

**Objetivo**: Hoy `HubChatbot` solo tiene `is_active`; no existe forma de expresar "este chatbot es solo para personal autenticado" ni "solo para el grupo Gerencia". SEC.2 aísla **entre** organizaciones, pero **dentro** de una organización todos los chatbots quedan igual de accesibles. Además, el piloto con Open WebUI exige que el backend sepa **qué persona** pregunta cuando la petición llega por un cliente de confianza que porta un PAT de servicio: sin eso, la cuota por usuario de SEC.4 es inaplicable.

**Origen**: revisión de planificación 2026-07-27 (chatbots de gestión para personal + límite de uso). El usuario eligió la **opción (a)**: propagación de identidad por cabecera firmada, no un PAT por usuario (que no escala a cientos de personas ni sobrevive a las bajas).

**Dependencias**: requiere SEC.2 cerrado (`assert_org_access`, claim `organizacion_ids`). El endpoint del widget llega en **D.1**; aquí el helper se testea a nivel unitario con `via='widget_api_key'` y D.1 lo consume — este prompt **no** queda bloqueado por D.1.

```
# PROMPT SEC.2.1 (RED/GREEN) — Autorización por chatbot e identidad delegada
# Deploy: edge (enforcement en el chat) + shared (modelo y helpers de auth)

## PARTE 1 — Modo de acceso por chatbot

### Modelo (agents_hub/database/config_models.py, HubChatbot)
- `access_mode: Mapped[str]` String(20) NOT NULL default 'authenticated'
  + CheckConstraint access_mode IN ('public_anon','authenticated','restricted')
    - public_anon    -> conversable sin sesión, solo por el endpoint widget con API key (D.1)
    - authenticated  -> exige JWT o PAT + pertenencia a la organización (SEC.2)
    - restricted     -> lo anterior + rol en allowed_roles O grupo en allowed_saml_groups
- `allowed_roles: Mapped[list[str]]` ARRAY(String) default list
- `allowed_saml_groups: Mapped[list[str]]` ARRAY(String) default list
- Decisión documentada: **no se crea tabla de grants**. El atributo de grupo ya llega en el
  ACS SAML (bloque AUTH) y dos ARRAY cubren el caso del piloto. Si más adelante hace falta
  granularidad por usuario individual, se añade tabla entonces; estos campos quedan como
  atajo. No sobreingeniería ahora.
- Migración Alembic **fail-closed**: todos los chatbots existentes -> 'authenticated'.
  NO usar 'public_anon' como valor de migración: hoy no existe endpoint anónimo (llega en
  D.1) y abrirlo por migración expondría el corpus sin que nadie lo haya decidido.

### Helper único (core/auth/chatbot_access.py)
- `assert_chatbot_access(actor: EffectiveActor | None, chatbot: HubChatbot, *, via: str) -> None`
  - `via` ∈ {'session','widget_api_key'} — por dónde entró la petición.
  - public_anon + via='widget_api_key' -> pasa sin actor.
  - public_anon + via='session'        -> pasa (un chatbot abierto también es usable logueado).
  - authenticated|restricted + via='widget_api_key' -> 403 ACCESS_MODE_FORBIDDEN.
  - authenticated -> exige actor + assert_org_access(actor, chatbot.organizacion_id).
  - restricted    -> lo anterior + (actor.role in allowed_roles OR
                     intersección no vacía entre actor.saml_groups y allowed_saml_groups).
                     Ambas listas vacías en modo restricted => solo superadmin (fail-closed).
  - superadmin siempre pasa (comodín, coherente con SEC.2).
- `UserInfo` añade `saml_groups: list[str]` (se rellena en el ACS SAML; vacío en login local).

### La organización de un usuario SAML (añadido el 2026-08-02, desde SEC.2)

**Problema que deja abierto SEC.2**: `HubSsoUser` no tiene organización, así que un usuario
provisionado por SSO se queda con el claim vacío y, por la regla de SEC.2, **sin acceso a
ningún recurso de organización**. Es fail-closed y no rompe nada vivo —el SSO real contra el
IdP sigue en la lista de pruebas manuales—, pero capa el login SSO. Se cierra aquí porque
este prompt ya toca `UserInfo` y ya toca el ACS.

**La decisión, y es la mitad importante del encargo: la organización sale de la
configuración del IdP, NUNCA de la aserción.**

- `HubSsoUser` gana `organizacion_id`, que se rellena **al aprovisionar en el ACS** tomándolo
  de la configuración del proveedor de identidad, no de un atributo de la respuesta SAML ni
  del dominio del correo.
- Es el mismo razonamiento anti-escalada que la Parte 2 de este prompt aplica a la cabecera
  delegada: si el dato viniera de fuera, quien controla el IdP podría declarar a qué
  organización pertenece cada persona que entra. Un IdP institucional pertenece a **una**
  institución, y esa relación la fija quien despliega.
- Migración fail-closed, como la de `access_mode`: los `HubSsoUser` existentes se quedan sin
  organización hasta que alguien la asigne. Ninguno hereda una por defecto.

Tests que añade a `tests/core/auth/test_saml_identity.py`:

```
# should_take_the_organizacion_from_the_idp_configuration
# should_ignore_an_organizacion_claimed_in_the_assertion    <- anti-escalada, el que importa
# should_leave_existing_sso_users_without_organizacion_after_migration
```
- Consumidores obligatorios: `hub_chat`, adaptador compatible-OpenAI (OWUI.1) y endpoint
  widget (D.1). **Ningún endpoint construye la decisión a mano** (grep de cierre).

### Router admin (hub_chatbots_router)
- `access_mode`, `allowed_roles`, `allowed_saml_groups` en ChatbotRead/Create/Update.
- Cambiar access_mode solo admin/superadmin (ya cubierto por require_admin).

## PARTE 2 — Identidad delegada (actor firmado)

Motivo: el Pipe de Open WebUI usa **un PAT de servicio**. Sin esto el backend solo ve al
dueño del PAT, y la cuota por usuario de SEC.4 no puede existir.

### Contrato (core/auth/delegated_actor.py)
- Cabecera `X-GovGenAI-Actor`: JWT compacto firmado por el cliente de confianza.
  HS256 con `DELEGATED_ACTOR_SECRET` (secreto compartido; RS256 se deja para cuando haya
  más de un cliente delegante — decisión documentada, no implementar ahora).
  Claims: `sub` (id estable del usuario en el cliente), `email`, `groups: list[str]`,
  `iat`, `exp` (ventana corta, <= 300 s), `aud` = "govgenai-backend".
- Nuevo scope `chat:onbehalf` en core/auth/pat/scopes.py (+ techo de rol superadmin/admin).
  **Sin el scope la cabecera se ignora por completo**: no es error, simplemente el actor
  efectivo es el dueño del PAT. Así un PAT robado sin ese scope no puede suplantar a nadie.
- `resolve_effective_actor(request, principal) -> EffectiveActor`
  con `EffectiveActor(subject_id, email, role, organizacion_ids, saml_groups, delegated: bool)`.
  - PAT con scope `chat:onbehalf` + cabecera válida -> actor delegado.
    **`organizacion_ids` se heredan del PAT, NUNCA de la cabecera** (si vinieran de la
    cabecera, el cliente delegante podría escalar de organización). `saml_groups` sí
    vienen de la cabecera (es lo que el IdP del cliente sabe y el backend no).
  - Firma inválida, expirada, `aud` incorrecto -> 401 ACTOR_TOKEN_INVALID.
  - Sesión humana JWT -> actor = el propio usuario, `delegated=False`.
- `assert_chatbot_access` y la cuota de SEC.4 consumen **el actor efectivo**, no el principal.
  Este es el punto de costura: SEC.4 se escribe sobre `resolve_effective_actor` desde el
  principio, para que OWUI.1 no tenga que retrofitear la cuota por usuario.

## Tests (RED primero)

# tests/api/test_chatbot_access_mode.py
# should_allow_anon_widget_only_when_public_anon
# should_403_widget_key_on_authenticated_chatbot
# should_403_authenticated_user_of_other_org              (se apoya en SEC.2)
# should_allow_restricted_when_role_in_allowed_roles
# should_allow_restricted_when_saml_group_matches
# should_403_restricted_when_no_role_or_group_matches
# should_403_restricted_when_lists_empty_and_not_superadmin
# should_allow_superadmin_regardless_of_access_mode
# should_default_existing_chatbots_to_authenticated_after_migration

# tests/core/auth/test_delegated_actor.py
# should_resolve_actor_from_signed_header_when_scope_present
# should_ignore_actor_header_when_pat_lacks_onbehalf_scope
# should_401_on_invalid_signature
# should_401_on_expired_actor_token
# should_401_on_wrong_audience
# should_inherit_organizacion_ids_from_pat_not_from_header    <- anti-escalada, clave
# should_use_session_user_as_actor_for_human_jwt

## Criterios de cierre
- [ ] Migración aplicada (`alembic upgrade head` + `alembic current`); chatbots existentes en 'authenticated'
- [ ] grep: hub_chat, adaptador OpenAI y endpoint widget pasan TODOS por assert_chatbot_access
- [ ] grep: ningún endpoint decide el acceso a mano
- [ ] `DELEGATED_ACTOR_SECRET` añadido a `.env.example` y generado en `scripts/generate_env.sh` (11.1)
- [ ] OpenAPI reexportado + Orval regenerado
- [ ] Frontera edge/cloud respetada: los tres campos nuevos son configuración (HubConfigBase), sin contadores
```

---

### Prompt SEC.3 (RED/GREEN) — CORS por entorno [A4]

**Modelo sugerido**: **Sonnet** — config declarativa.

```
# PROMPT SEC.3 (RED/GREEN) — CORS restringido por entorno
# Deploy: shared

## Cambios
- core/config.py: `CORS_ALLOWED_ORIGINS: list[str]` (CSV en env), `ENVIRONMENT`.
- main.py: sustituir allow_origins=["*"] por la lista configurada. En producción, lista
  cerrada (dominios del panel + dominios de widget de organizaciones). methods/headers
  acotados a los realmente usados. allow_credentials sigue False.
- Widget embebible: los orígenes de widget se validan aparte (API key por chatbot, D.1);
  no se abre CORS global por ellos.

## Tests (RED primero) — tests/api/test_cors.py
# should_reject_disallowed_origin_in_production_config
# should_allow_configured_origin
# should_default_to_no_wildcard_when_env_is_production
```

---

### Prompt SEC.4 (RED/GREEN) — Rate limiting + contabilidad de tokens + cuotas multi-sujeto [A5]

**Modelo sugerido**: **Sonnet** — el limiter es patrón conocido y la cascada de cuotas se copia del patrón ya existente en `config_resolver.py`. Añade una migración, pero sin decisiones de diseño abiertas.

**Objetivo**: Limitar login (fuerza bruta) y consumo de LLM (coste). Para un chatbot público es control de gasto; para los chatbots de gestión del piloto, control de consumo **por persona**.

**Ampliado el 2026-07-27** (revisión de planificación con Open WebUI): la cuota pasa de *solo por chatbot/día* a **multi-sujeto en cascada**, y se añade la **contabilidad real de tokens** — que no existía en ningún prompt y sin la cual no hay cuota posible, solo conteo de peticiones.

**Dependencias**: SEC.2.1 (el sujeto "usuario" es el **actor efectivo**, no el dueño del PAT).

```
# PROMPT SEC.4 (RED/GREEN) — Rate limiting, contabilidad de tokens y cuotas
# Deploy: shared (limiter) + edge (contadores y cuotas: son datos operacionales de cliente)

## PARTE 1 — Rate limiting (sin cambios respecto al plan original)
- Añadir slowapi (o limiter propio sobre Redis/memoria). Config por env
  (RATE_LIMIT_LOGIN, RATE_LIMIT_CHAT). Clave: IP para login/widget anónimo; actor efectivo
  para el resto.
- Aplicar a: /auth/*/login (bajo, p.ej. 10/min/IP con backoff),
  /hub/chat (por chatbot + por IP), ingestión (por organización).

## PARTE 2 — Contabilidad de tokens (prerrequisito de toda cuota)

### HubInteraction (operational_models.py) — campos nuevos + migración
- `prompt_tokens: Mapped[int | None]`
- `completion_tokens: Mapped[int | None]`
- `cost_estimated: Mapped[float | None]`   (según precio del HubLLMConfig usado)
- Nullable: las interacciones históricas no tienen el dato y no se inventa.

### Captura del uso real
- Leer el usage del proveedor en el trayecto del grafo (callback/`response_metadata` de
  LangChain). Si el proveedor no lo expone, estimar con el tokenizer y **marcarlo** en
  `interaction_metadata.usage_source = 'provider'|'estimated'` — una cuota que se apoya en
  una estimación silenciosa es una cuota que no se puede defender ante el usuario.
- La escritura del usage va en el MISMO commit que la HubInteraction (hoy en
  `api/v1/hub_chat.py`, tras RAG.2 en el CoreGraph). No un segundo write.

### Contador operacional (operational_models.py) — modelo nuevo
- `HubUsageCounter(HubOperationalBase)`:
    subject_type: 'user'|'chatbot'|'organizacion'|'ip'
    subject_id: String(255)
    window_key: String(20)     -- '2026-07-27' (día), '2026-07' (mes), 'total' (acumulado)
    tokens: int, cost: float, updated_at
    UniqueConstraint(subject_type, subject_id, window_key)
- UPSERT atómico (`ON CONFLICT ... DO UPDATE`), no read-modify-write: el chat es concurrente.
- **Vive en HubOperationalBase, nunca en el chatbot**: es dato de consumo del cliente final,
  no configuración, y no se sincroniza al cloud (P8). Un contador en HubChatbot rompería la
  frontera edge/cloud.
- Este contador lo reutiliza SEC.4.1 con `window_key='total'`.

## PARTE 3 — Cuotas en cascada

### Campos de configuración (cascada plataforma -> organización -> chatbot, patrón config_resolver.py)
- En HubOrganizacion: `default_user_daily_token_quota`, `default_user_monthly_token_quota`,
  `monthly_token_quota` (de la organización entera), `default_chatbot_daily_token_quota`
- En HubChatbot: `user_daily_token_quota`, `chatbot_daily_token_quota`,
  `anon_ip_daily_token_quota` (para el widget)
- `None` en cualquier nivel = heredar; `0` = sin límite explícito. Distinguir los dos casos
  (que `0` no signifique "bloqueado") es requisito de test.

### Enforcement (un único punto)
- `core/quotas.py`: `assert_within_quota(session, actor, chatbot, via) -> None`
  Evalúa en orden y devuelve **413/429 en el primer sujeto agotado**, con
  `Retry-After` y un cuerpo que diga QUÉ cuota se agotó
  (`{"code":"QUOTA_EXCEEDED","subject":"user","window":"day","limit":N,"used":M}`).
  Sujetos: usuario/día -> usuario/mes -> chatbot/día -> organización/mes -> IP/día (anónimo).
- Llamado desde `hub_chat`, el adaptador OpenAI (OWUI.1) y el endpoint widget (D.1).
  Mismo criterio que `assert_chatbot_access`: la regla vive en un sitio.
- Se comprueba **antes** de invocar el LLM y se contabiliza **después**. Se acepta el
  desbordamiento de una petición (no se pre-reserva presupuesto): decisión documentada,
  reservar exigiría estimar el coste antes de generar.

### Endpoint de consulta (para que el usuario sepa cuánto le queda)
- `GET /api/v1/hub/usage/me` -> cuotas y consumo del actor efectivo. Deploy: edge.
  Sin esto, un 429 es indistinguible de un fallo.

## Tests (RED primero) — tests/api/test_rate_limit.py + tests/api/test_quotas.py
# should_429_after_login_attempts_exceed_limit
# should_reset_login_limit_after_window
# should_not_limit_below_threshold
# should_scope_limit_per_ip_for_anonymous_widget
# should_persist_prompt_and_completion_tokens_on_interaction
# should_mark_usage_source_when_estimated
# should_upsert_usage_counter_atomically_under_concurrency
# should_429_chat_when_chatbot_daily_quota_exceeded
# should_429_chat_when_user_daily_token_quota_exceeded
# should_429_chat_when_user_monthly_token_quota_exceeded
# should_429_when_organizacion_monthly_quota_exceeded
# should_cascade_quota_from_org_default_to_chatbot
# should_treat_zero_as_unlimited_and_none_as_inherit
# should_report_which_subject_exhausted_the_quota
# should_charge_quota_to_delegated_actor_not_pat_owner      <- integra SEC.2.1
# should_return_remaining_quota_on_usage_me

## Criterios de cierre
- [ ] Migración aplicada (`alembic upgrade head` + `alembic current`)
- [ ] grep: los tres caminos de conversación pasan por assert_within_quota
- [ ] Contadores en HubOperationalBase; ningún contador en tablas de HubConfigBase
- [ ] OpenAPI reexportado + Orval regenerado (usage/me)
```

---

### Prompt SEC.4.1 (RED/GREEN) — Ventana de vigencia y presupuesto acumulado por chatbot

**Modelo sugerido**: **Sonnet** — campos de configuración, una guarda y estado derivado en la UI admin. Sin decisiones abiertas: el contador ya lo aporta SEC.4.

**Objetivo**: Un chatbot público de campaña (plazo de matrícula, convocatoria, periodo de alegaciones) debe poder **caducar solo** y tener **techo de gasto total**, no solo diario. Hoy la única palanca es que un humano se acuerde de poner `is_active = false`.

**Origen**: revisión de planificación 2026-07-27 — "límite de uso temporal para chatbots públicos".

**Dependencias**: SEC.4 (`HubUsageCounter`, `assert_within_quota`).

```
# PROMPT SEC.4.1 (RED/GREEN) — Vigencia temporal y presupuesto total
# Deploy: edge (enforcement) + shared (campos de configuración)

## Campos de configuración (HubChatbot — HubConfigBase, sin contadores)
- `valid_from: Mapped[datetime | None]`   DateTime(timezone=True), nullable
- `valid_until: Mapped[datetime | None]`  DateTime(timezone=True), nullable
- `total_token_budget: Mapped[int | None]` nullable (None = sin techo acumulado)
- `unavailable_message: Mapped[str]` Text, default "" — texto que ve el ciudadano cuando el
  chatbot no está disponible. Vacío -> mensaje genérico i18n del frontend.
- Migración Alembic. Los chatbots existentes quedan con los cuatro campos nulos/vacíos =
  comportamiento actual sin cambios.

## Estado derivado, NO almacenado (decisión de diseño)
- **No se añade `closed_reason` ni se voltea `is_active`.** El estado se calcula:
    expired          <- valid_until  < now
    not_yet_open     <- valid_from   > now
    budget_exhausted <- HubUsageCounter(chatbot, 'total').tokens >= total_token_budget
    available        <- resto
- Razones: (1) un flag persistido se queda obsoleto y obliga a un job que lo refresque;
  (2) el consumo acumulado es dato **operacional** y `HubChatbot` es config que se
  sincroniza cloud->edge — guardar ahí el contador rompería la frontera (P8);
  (3) `is_active` sigue significando lo que significa hoy (el admin lo apagó a mano),
  sin mezclar dos conceptos en un booleano.

## Enforcement (core/chatbot_availability.py)
- `assert_chatbot_available(session, chatbot, now) -> None`
  -> 403 `{"code":"CHATBOT_UNAVAILABLE","reason":"expired|not_yet_open|budget_exhausted",
           "message": chatbot.unavailable_message or None}`
- Se invoca en los tres caminos de conversación, **inmediatamente después de
  `assert_chatbot_access` y antes de `assert_within_quota`** (primero "¿puedes hablar con
  este bot?", luego "¿está abierto?", luego "¿te queda cuota?").
- El 403 NO es un error genérico: lleva el motivo y el mensaje del admin, para que el
  ciudadano lea "el plazo de matrícula terminó el 30 de septiembre" y no "Forbidden".

## Superficie admin
- Los cuatro campos en ChatbotRead/Create/Update + campo **de solo lectura**
  `availability: {state, reason, tokens_used, total_token_budget}` en ChatbotRead,
  calculado en el servidor (Contract-First: el frontend no recalcula el estado).
- `frontend/src/admin`: badge de estado en la lista de chatbots (Disponible / Caducado /
  Presupuesto agotado / Pendiente de apertura) iterando el contrato, más los campos en el
  formulario. i18n es/ca/en.
- **Aviso al admin**: se limita a que el estado sea visible en el panel y en la API. NO se
  implementa email ni webhook: no existe infraestructura de notificaciones en el proyecto y
  crearla aquí sería una feature no pedida. Si el piloto la exige, se planifica aparte.

## Tests (RED primero) — tests/api/test_chatbot_availability.py
# should_403_when_valid_until_in_the_past
# should_403_when_valid_from_in_the_future
# should_allow_when_now_inside_window
# should_allow_when_window_fields_are_null            (comportamiento actual preservado)
# should_403_when_total_token_budget_exhausted
# should_use_total_window_counter_not_daily
# should_return_admin_unavailable_message_in_403_body
# should_expose_derived_availability_in_chatbot_read
# should_not_persist_availability_state_in_db          (grep: sin closed_reason)
# should_check_availability_after_access_and_before_quota   (orden de las guardas)

## Criterios de cierre
- [ ] Migración aplicada (`alembic upgrade head` + `alembic current`)
- [ ] Los tres caminos de conversación invocan la guarda en el orden documentado
- [ ] `availability` es de solo lectura y se calcula en el servidor
- [ ] Verificado en navegador: badge de caducado visible en la lista de chatbots
- [ ] OpenAPI reexportado + Orval regenerado
```

---

### Prompt SEC.5 (RED/GREEN) — Temas: auth en GET + validación anti path-traversal [M2]

**Modelo sugerido**: **Sonnet** — alcance puntual.

```
# PROMPT SEC.5 (RED/GREEN) — Endurecer hub_themes_router
# Deploy: cloud

## Cambios (routers/hub_themes_router.py)
- Validar theme_id como UUID (o slug estricto ^[a-z0-9-]+$) antes de construir rutas.
- Resolver la ruta con (THEMES_DIR / f"{theme_id}.json").resolve() y comprobar que queda
  bajo THEMES_DIR.resolve(); si no → 400. Aplica a GET, PUT, DELETE (unlink).
- Exigir autenticación también en GET /hub/themes/{theme_id} (hoy es público) y aplicar
  assert_org_access (SEC.2) si el tema es de una organización.

## Tests (RED primero) — tests/api/test_themes_security.py
# should_reject_theme_id_with_path_traversal          ('../', '%2F', absolute)
# should_reject_non_uuid_theme_id
# should_require_auth_on_get_theme
# should_not_read_files_outside_themes_dir
```

---

### Prompt SEC.6 (RED/GREEN) — Validación de subidas: tipo real (magic bytes) + límite de tamaño [M4]

**Modelo sugerido**: **Sonnet** — alcance cerrado. Comparte la validación con el futuro Bloque ING.

```
# PROMPT SEC.6 (RED/GREEN) — Validación robusta de uploads
# Deploy: edge

## Cambios (api/v1/ingestion.py y cualquier endpoint de upload)
- core/uploads.py: `validate_upload(file, *, allowed_ext, allowed_magic, max_bytes)`:
    - comprobar extensión + magic bytes (no confiar en content_type, que es spoofeable);
    - hacer streaming a un buffer temporal con corte al superar max_bytes → 413;
    - devolver el buffer validado (no `await file.read()` completo en memoria).
- MAX_UPLOAD_MB por env. Cuota por organización/chatbot (nº o tamaño acumulado) → 429/413.
- Reutilizable por el Bloque ING (validación compartida por extensión+magic).

## Tests (RED primero) — tests/api/test_upload_validation.py
# should_reject_pdf_content_type_with_non_pdf_magic_bytes
# should_reject_upload_exceeding_max_size            (413, sin cargar todo en memoria)
# should_accept_valid_pdf
# should_reject_disallowed_extension
```

---

### Prompt SEC.7 (RED/GREEN) — Docs off en producción + cabeceras de seguridad [M5]

**Modelo sugerido**: **Sonnet** — config + middleware.

```
# PROMPT SEC.7 (RED/GREEN) — Superficie mínima + headers
# Deploy: shared

## Cambios (main.py)
- Si ENVIRONMENT == 'production': FastAPI(docs_url=None, redoc_url=None, openapi_url=None).
  En dev/staging quedan disponibles.
- Middleware de cabeceras de seguridad: X-Content-Type-Options: nosniff, X-Frame-Options:
  DENY (o CSP frame-ancestors para el widget), Referrer-Policy, HSTS (solo prod/https),
  y CSP básica para el panel.

## Tests (RED primero) — tests/api/test_security_headers.py
# should_disable_docs_in_production
# should_expose_docs_in_development
# should_set_nosniff_and_frame_options_headers
# should_set_hsts_only_in_production
```

---
