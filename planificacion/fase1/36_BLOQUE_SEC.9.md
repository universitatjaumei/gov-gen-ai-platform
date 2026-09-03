## Bloque SEC.9 — Endurecimiento pre-deploy, tercera auditoría (Subfase 1.B, PENDIENTE, BLOQUEANTE DE DESPLIEGUE)

> **Contexto**: hallazgos de `docs/VALORACION_PROYECTO.md` (auditoría del 2026-08-24, cursor en
> Deploy/D.0). Tercera pasada tras SEC.1–SEC.7 y SEC.8: cubre lo que se coló en los routers
> añadidos **después** de SEC.8 (bloques REV y MT). Los diez hallazgos de julio están resueltos;
> los nuevos son regresiones introducidas por los bloques posteriores, y **tres de las cuatro
> auditorías los encontraron por separado** (señal fuerte). Va **antes de Deploy GCP (D.0)**.
> Cierra con MT.16 (adelantado de la fase 2 de MT), que es lo único que **demuestra** que el
> esquema de MT fase 1 más estos arreglos aíslan de verdad: sin él el piloto no ejercita el
> aislamiento, porque arranca con una sola organización.
>
> **La lección de método de esta auditoría**: los cuatro agujeros vivos están precisamente donde
> el gate de CI no mira. El gate recorre una lista fija de routers que no incluye ninguno de los
> añadidos en REV ni MT. SEC.9.5 convierte ese gate en un recorrido del árbol (patrón
> `tablas_sin_ambito()`), que es lo que evita la próxima regresión de esta clase.

---

### Prompt SEC.9.1 (RED/GREEN) — `library_router` sin autenticación + oráculo de firma [CRÍTICO]

**Modelo sugerido**: **Opus** — es el hallazgo más grave del bloque; hay que decidir el modelo de
identidad del endpoint (derivar tenencia del token, no de cabeceras) sin romper el consumo del
Thin Client de Fase 2, y cerrar un oráculo de firma RSA que hoy está abierto.

**Objetivo**: `server/app/routers/library_router.py` (montado en `/api/v1/library/*`) no tiene
**ninguna** dependencia de identidad. `GET /manifest` y `GET /download/{item_id}` deciden la
visibilidad por las cabeceras `X-Client-Id`/`X-Partner-Id`/`X-Client-Groups` que pone el propio
cliente; `POST /push` publica una automatización arbitraria **y el servidor la firma** con la
clave privada de plataforma; `POST /sign_manifest` es un oráculo de firma RSA-SHA256 abierto con
`partner_id` tomado del cuerpo. Verificado directamente en la auditoría.

```
# PROMPT SEC.9.1 (RED/GREEN) — library_router: identidad del token, no de cabeceras
# Deploy: cloud (Módulo: plataforma)

## Cambios
- library_router.py:21: el APIRouter lleva dependencies=[Depends(require_module("plataforma")),
  Depends(require_admin)]. La tenencia (client_id/partner_id/organizacion) se DERIVA del token,
  nunca de X-Client-Id/X-Partner-Id/X-Client-Groups (retirar esas cabeceras del contrato).
- POST /push (:113) y POST /sign_manifest (:171): restringir a superadmin. sign_manifest no
  acepta partner_id del cuerpo: se deriva del actor.
- Convertir el check de módulo de test_plat5_frontera_de_modulos.py de docstring a
  dependencies reales (ver SEC.9.5): el test declaraba este router como 'plataforma' pero solo
  comprobaba el docstring, y pasaba en verde sobre un router abierto.

## Tests (RED primero) — tests/api/test_library_router_auth.py + gate de SEC.9.5
# should_reject_manifest_without_authentication
# should_ignore_client_supplied_tenant_headers
# should_forbid_download_of_other_org_automation
# should_forbid_push_for_non_superadmin
# should_forbid_sign_manifest_for_non_superadmin
# should_derive_partner_id_from_actor_not_body

## Criterios de cierre
- [ ] Ningún endpoint de library_router responde sin credencial.
- [ ] El gate de aislamiento (SEC.9.5) incluye library_router.
```

---

### Prompt SEC.9.2 (RED/GREEN) — `hub_llm_configs_router`: la clave del proveedor en claro + MT.2 sin tenencia [ALTO]

**Modelo sugerido**: **Opus** — combina fuga de credencial con la aplicación de la capa de
tenencia sobre MT.2; el patrón «el cuerpo propone, el token dispone» de `hub_themes_router` es la
referencia a replicar.

**Objetivo**: `HubProviderOut.api_key` (`hub_llm_configs_router.py:44`) devuelve la clave del
proveedor en claro en `GET /providers`, accesible por cualquier `admin`. Y MT.2 dejó los endpoints
sin tenencia: `list_llm_configs` sin `scope_query_to_orgs`, `create` acepta `organizacion_id` del
cuerpo sin validarlo, `update`/`delete`/`test` por id sin `assert_org_access`.

```
# PROMPT SEC.9.2 (RED/GREEN) — llm-configs: enmascarar api_key + aplicar tenencia MT.2
# Deploy: cloud (Módulo: plataforma)

## Cambios
- Quitar api_key de HubProviderOut (:39-46). GET /providers no devuelve el secreto.
- list_llm_configs (:229): scope_query_to_orgs sobre HubLLMConfig.
- create_llm_config (:285): validar organizacion_id del cuerpo contra el token (assert_org_access);
  organizacion_id=None (config de plataforma que heredan todas) reservado al superadmin.
- update/delete/test (:311,:340,:363): resolver la fila -> assert_org_access antes de operar.

## Tests (RED primero) — tests/modules/agents_hub/.../test_llm_configs_isolation.py
# should_not_return_provider_api_key
# should_list_only_own_org_llm_configs
# should_forbid_create_llm_config_for_other_org
# should_reserve_platform_llm_config_for_superadmin
# should_forbid_update_delete_test_of_other_org_config

## Cierre
- [ ] El router importa tenancy y aparece en el gate de SEC.9.5.
```

---

### Prompt SEC.9.3 (RED/GREEN) — `hub_activity_prompts_router`: el escritor ignora la organización (MT.6 a medias) [ALTO]

**Modelo sugerido**: **Opus** — cross-tenant write + inyección de prompt al LLM; MT.6 dejó el
lector correcto y el escritor no.

**Objetivo**: MT.6 dio a `hub_activity_prompts` la dimensión de organización (`(activity,
organizacion_id)` con `NULLS NOT DISTINCT`) y el lector (`config_provider.py`) la respeta, pero
`_fila()` (`hub_activity_prompts_router.py:126`) consulta solo por `activity`. Un `admin` de
cualquier organización puede leer, **sobrescribir o borrar** el prompt de plataforma que heredan
todas, y no hay forma por API de crear un override *de organización*.

```
# PROMPT SEC.9.3 (RED/GREEN) — activity-prompts: escritor consciente de la organización
# Deploy: cloud (Módulo: plataforma)

## Cambios
- _fila() y GET/PUT/DELETE (:126-201): resolver por (activity, organizacion_id del actor).
  El admin opera sobre la fila de SU organización; el superadmin sobre la de plataforma (None).
- Añadir require_module a nivel de router (hoy es solo _require_admin por rol).
- Corregir el docstring de hub_prompts_catalog_router.py:11 ("activity único global", falso
  desde MT.6).

## Tests (RED primero) — tests/api/test_activity_prompts_isolation.py
# should_not_read_platform_prompt_as_org_override
# should_forbid_overwriting_the_platform_activity_prompt_from_an_org_admin
# should_forbid_deleting_another_orgs_activity_prompt
# should_create_org_scoped_override_for_the_actor_org

## Cierre
- [ ] El router aparece en el gate de SEC.9.5.
```

---

### Prompt SEC.9.4 (DECISIÓN + RED/GREEN) — Credencial literal de proveedor sin cifrar en reposo [MEDIO-ALTO]

**Modelo sugerido**: **Sonnet** — patrón conocido; la parte de criterio (cifrar vs restringir el
método) es acotada y con recomendación clara.

**Objetivo**: `hub_provider_credentials.api_key` se guarda en `String(255)` en **texto plano**
cuando `metodo='clave'` (`config_models.py:183-185`). No se expone por HTTP (no hay router para la
tabla), así que el riesgo es un volcado de BD o la sincronización cloud→edge. Hoy es teórico (0
filas); sube a real con la primera credencial del piloto.

**Las dos opciones protegen contra cosas distintas, y conviene tenerlo escrito:**

- **Cifrar en reposo** cubre que alguien lea la BD **sin pasar por la aplicación**: volcado, copia,
  réplica, el payload de la sincronización cloud→edge, o un bug que devuelva la fila tal cual (que
  es el hallazgo de SEC.9.2). **No** cubre el compromiso a nivel de aplicación: la app descifra, así
  que `ENCRYPTION_KEY` vive en el entorno del mismo proceso — el secreto se mueve de «dentro de la
  BD» a «en el entorno del proceso que lee la BD», que es donde ya estaba con los otros dos
  métodos. Y trae peso permanente: rotar obliga a recifrar todas las filas, perder la clave es
  perder todas las credenciales, la copia solo es restaurable con la clave (dos cosas que proteger
  en vez de una), el edge necesita la clave también, y aparece un fallo nuevo —«no puedo
  descifrar»— que se ve como una caída.
- **Restringir el método** deja en la BD un *puntero* y nunca un secreto: volcados, copias,
  réplicas y la sincronización dejan de ser sensibles **por construcción**. Sin gestión de claves,
  sin recifrado, sin modo de fallo nuevo, y si alguien reintroduce el bug de devolver la fila no
  filtra nada. Es lo que ya dicen las reglas del proyecto (`CONTRIBUTING.md` §6: secretos por
  variable de entorno, Secret Manager en producción) y encaja con el destino GCP. **Su coste es el
  autoservicio**: dar de alta una credencial deja de ser un formulario y pasa a exigir que alguien
  añada el secreto y haga existir la variable. Nota: **ADC no puede dar credenciales por
  organización** (un proceso, una identidad — el módulo ya lo documenta), así que lo
  multiorganización descansa entero en nombres de variable de entorno.

**Decisión recomendada: restringir ahora, `SecretProvider` en MT.10.** Hoy hay **cero filas**, así
que no hay datos que migrar; el piloto es una organización con un proveedor, así que la fricción es
una variable puesta una vez; y evita inventar gestión de claves con el despliegue encima. Cifrar
sería pagar peso operativo permanente por un modelo de amenaza que el piloto no tiene, y **no
ahorraría hacer la abstracción después**. Riesgo a vigilar, dicho sin adornos: si llegan varias
organizaciones antes de MT.10, la fricción puede empujar a compartir una credencial entre
organizaciones, que es peor que las dos opciones. Eso es el argumento para **programar** MT.10, no
para dejar esto así para siempre.

```
# PROMPT SEC.9.4 (RED/GREEN) — la BD guarda un puntero, no un secreto
# Deploy: shared

## Rama elegida (recomendada): RESTRINGIR el método.
- Retirar 'clave' del CheckConstraint de hub_provider_credentials; quedan 'secret_env' (nombre de
  variable) y 'entorno_de_ejecucion' (ADC). Migración Alembic (0 filas hoy: sin backfill).
- El error de configuración tiene que DECIR qué falta: qué variable se esperaba y para qué
  organización (hoy `falta` ya lleva ese texto en credenciales_llm.py — conservarlo).
- Dejar por escrito en el prompt la opción descartada (cifrar) y POR QUÉ, para que no se
  reabra sin argumento nuevo.

## Alternativa si el usuario prefiere conservar el autoservicio del panel antes del piloto:
# cifrar en reposo (api_key_encrypted, cifrar al escribir, descifrar solo al construir el cliente,
# nunca loguear el valor) — asumiendo la gestión de clave descrita arriba.

## Tests (RED primero)
# should_reject_metodo_clave_in_the_check_constraint
# should_never_store_a_provider_secret_in_the_database
# should_explain_which_env_var_is_missing_and_for_which_organisation

## Cierre
- [ ] Ninguna columna de hub_provider_credentials puede contener un secreto.
- [ ] MT.10 anotado como el sitio del `SecretProvider` (autoservicio sin secreto en la BD).
```

---

### Prompt SEC.9.5 (RED/GREEN) — El gate de aislamiento recorre el árbol de routers, no una lista [ALTO — meta-fix]

**Modelo sugerido**: **Opus** — es el prompt que impide la próxima regresión de esta clase; hay
que decidir la lista de exenciones legítimas (login, widget, edge_sync) sin dejar agujeros.

**Objetivo**: el paso «Access control gate» de `ci.yml` y el guardarraíl estático de
`test_tenant_isolation.py` son **listas fijas de routers** que no incluyen ninguno de los añadidos
en REV ni MT, y `if not ruta.is_file(): continue` se salta en silencio los que no encuentra. Es
por eso que SEC.9.1–SEC.9.3 existen. El patrón bueno ya está en el proyecto: `tablas_sin_ambito()`
recorre el registro de modelos.

```
# PROMPT SEC.9.5 (RED/GREEN) — inventario de routers por recorrido, con exenciones explícitas
# Deploy: n/a (guardarraíl de CI)

## Cambios
- Un test que recorre app/routers/ + app/api/v1/ y, para cada router registrado en main.py,
  exige que declare su módulo por dependencies REALES (no por docstring) y que sus endpoints de
  estado pasen por la capa de tenencia, salvo una lista de EXENCIONES explícita y comentada
  (auth/saml login, widget público, edge_sync stub).
- Ampliar el paso "Access control gate" de ci.yml (:161-170) para que ejecute ese test y falle
  el deploy si un router nuevo no está acotado ni exento.
- Retirar el check por docstring de test_plat5 (lo sustituye este).

## Tests (RED primero) — tests/api/test_router_inventory_is_walked.py
# should_walk_registered_routers_not_a_fixed_list
# should_fail_when_a_new_router_lacks_tenancy_and_is_not_exempted
# should_require_real_dependencies_not_docstring

## Cierre
- [ ] Añadir un router nuevo sin acotar pone rojo el gate automáticamente.
- [ ] library, llm-configs, activity-prompts, llm-drafts entran en cobertura.
```

---

### Prompt SEC.9.6 (RED/GREEN) — Controles declarados y no aplicados + endpoints con guarda incompleta [MEDIO]

**Modelo sugerido**: **Sonnet** — conjunto de arreglos localizados de patrón conocido (NUEVO-5 a
NUEVO-9 de la auditoría).

**Objetivo**: cerrar los medios de la auditoría que hoy están declarados y no se aplican, o con la
guarda a medias.

```
# PROMPT SEC.9.6 (RED/GREEN) — cerrar los NUEVO-5..9
# Deploy: edge/cloud/shared según endpoint

## Cambios
- NUEVO-5: llm_drafts_router.py:163 (POST /redaccion/llm-drafts/sample) -> read_within_limit +
  validate_upload (es el único UploadFile fuera de SEC.6/SEC.8.2).
- NUEVO-6: hub_chat.py:310,:515 pasar ip= a assert_within_quota/contabilizar_interaccion, para
  que anon_ip_daily_token_quota deje de ser código muerto; límite por IP para el anónimo del
  widget además del cubo por chatbot (hoy un visitante deja el widget sin servicio para el resto).
- NUEVO-7: core/config.py añadir TESTING al gate de producción del sandbox (o ignorar TESTING en
  producción); subprocess.Popen del sandbox local con env= acotado, no os.environ heredado.
- NUEVO-8: hub_agents_router.py usar workspace_id (hoy exporta una interacción cualquiera);
  quitar los tres _user sin usar de hub_redaccion_router.py (:606,:729,:754) y comprobar
  owner/organización; workspaces_router.py con require_module("informes");
  hub_organizaciones_router.py validar partner_id del cuerpo contra el token.
- NUEVO-9: docker-compose.prod.yml quitar los defaults de secreto (:-govgenai_dev, :-minioadmin_dev)
  del servicio app; el fichero de producción no lleva ni un :- en un secreto.

## Tests (RED primero)
# should_limit_upload_size_on_llm_drafts_sample
# should_enforce_anon_ip_quota_on_widget_chat
# should_reject_testing_bypass_of_sandbox_prod_gate
# should_export_the_requested_workspace_only_for_its_owner
# should_require_informes_module_on_workspaces_router
# should_not_accept_partner_id_from_body_on_create_organizacion

## Cierre
- [ ] grep de UploadFile sin validate_upload = 0.
- [ ] docker-compose.prod.yml sin defaults en secretos.
```

---

### Prompt SEC.9.7 (RED/GREEN) — MT.16: aislamiento de punta a punta con dos organizaciones [ALTO — adelantado de MT fase 2]

**Modelo sugerido**: **Opus** — es el prompt que demuestra que todo lo anterior sirvió; escenario
de dos organizaciones completo, con datos reales, sobre HTTP.

**Objetivo**: adelantar MT.16 (planificado en la fase 2 de MT) porque es lo único que valida que
el esquema de MT fase 1 más SEC.9 aíslan de verdad. El piloto arranca con una sola organización,
así que sin este test el aislamiento no se ejercita en producción.

```
# PROMPT SEC.9.7 (RED/GREEN) — dos organizaciones, ninguna ve nada de la otra
# Deploy: n/a (test de integración, gate de CI)

## Cambios
- Escenario con DOS organizaciones (A y B), cada una con su administrador, su corpus, su juego de
  modelos y proveedores, sus plantillas de informe y sus prompts de actividad.
- Recorrido por HTTP (TestClient) que comprueba, para CADA superficie acotada, que el admin de A
  recibe 403/lista vacía sobre los recursos de B: chatbots, sitios, hallazgos, plantillas,
  llm-configs, activity-prompts, library, workspaces, feedback, tasks.
- Verificar que el superadmin sí ve ambas (permiso correcto) y que el actor anónimo del widget de
  A no alcanza nada de B.

## Tests (RED primero) — tests/api/test_mt16_aislamiento_dos_organizaciones.py
# should_isolate_every_scoped_surface_between_two_orgs
# should_let_superadmin_see_both_orgs
# should_not_let_widget_of_org_a_reach_org_b

## Cierre
- [ ] El test corre en el "Access control gate" de ci.yml (bloquea el deploy).
- [ ] Cubre las superficies cerradas en SEC.9.1–SEC.9.3 y SEC.9.6.
```

---
