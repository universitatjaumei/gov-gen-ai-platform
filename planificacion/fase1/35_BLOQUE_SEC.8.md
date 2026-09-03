## Bloque SEC.8 — Endurecimiento pre-deploy, segunda auditoría (Subfase 1.B, PENDIENTE, BLOQUEANTE DE DESPLIEGUE)

> **Contexto**: hallazgos de `docs/AUDITORIA_PRE_DEPLOY.md` (auditoría del 2026-08-10). Segunda
> pasada tras SEC.1–SEC.7: cubre lo que se coló en los routers añadidos **después** de SEC.2
> (IDOR horizontal, porque la capa de tenencia no se aplicó a los routers nuevos) y los
> bloqueantes funcionales que se ven verdes en el navegador pero no sobreviven a Cloud Run.
> Va **antes de Deploy GCP (D.0)**. Nomenclatura ROL nueva (`admin`, `organizacion_id`).

---

### Prompt SEC.8.0 ✅ — Gate del sembrado de desarrollo [CR-1]

**Hecho el 2026-08-10** (commit `56d5ef4`). `seed_multitenancy_defaults()` corría en el `lifespan`
en cualquier `ENVIRONMENT` y sembraba el SuperAdmin `fabra@uji.es`/`admin1234` (credencial pública
en el repo). Ahora retorna sin sembrar fuera de `development`; producción se provisiona con
`python -m server.app.scripts.bootstrap`. Tests: `tests/unit/test_seed_environment_gate.py`.

---

### Prompt SEC.8.1 (RED/GREEN) — Aislamiento multi-tenant en los routers posteriores a SEC.2 [CR-2, AL-1, AL-2, AL-3, ME-3, ME-4]

**Modelo sugerido**: **Opus** — barrido transversal de IDOR horizontal sobre datos personales;
cada endpoint exige resolver el recurso a su organización dueña sin romper el caso superadmin, y
el guardarraíl de CI hay que ampliarlo. Es el prompt más crítico del bloque.

**Objetivo**: SEC.2 aisló los routers que existían entonces; toda la familia añadida después
(test-scenarios, curation, prompt-templates, organizaciones, redacción, tasks, feedback) se quedó
con `_require_admin`/`get_current_user` y **nunca resuelve `chatbot_id`/`site_id`/`organizacion_id`
a su organización**. Como los modelos operacionales cuelgan de `chatbot_id`, hace falta el join a
`HubChatbot` (patrón `_chatbot_autorizado`) o comprobar `organizacion_id` directo.

```
# PROMPT SEC.8.1 (RED/GREEN) — Cerrar el IDOR horizontal de los routers post-SEC.2
# Deploy: edge/cloud según router

## Cambios (aplicar assert_org_access / scope_query_to_orgs, capa ya existente de SEC.2)
- hub_organizaciones_router.py:103-193: list -> scope_query_to_orgs; get/update/delete ->
  assert_org_access sobre la organización objetivo (superadmin pasa).
- hub_test_scenarios_router.py:211-258: resolver chatbot -> assert_org_access antes de
  run_scenario y de list/create/update/delete/set_verdict.
- hub_sites_router.py: create_site NO acepta organizacion_id del cliente (usar el del actor);
  list_sites -> site_repo.list_by_organizacion; patch/delete/trigger_crawl/ingest_page/
  retire_page -> resolver site.organizacion_id + assert_org_access.
- hub_content_quality_router.py:268-293 (analyze_content_gaps, lee conversaciones de ciudadanos)
  y transition_finding/get/export_site_report/analyze_site -> resolver org + assert_org_access.
- hub_prompt_templates_router.py: list exige chatbot_id y lo acota; create/update/delete ->
  resolver el chatbot dueño + assert_org_access.
- api/v1/hub_tasks.py:49-63 export_task: resolver chatbot_id->org + assert_org_access
  (quitar el bypass "o admin"; el superadmin pasa por la capa de tenencia).
- api/v1/hub_feedback.py:53-65 submit_feedback (POST): assert sobre la interacción->chatbot->org
  antes del UPDATE. Añadir rate limit.
- routers/redaccion/manifests_router.py:31-64 y hub_redaccion_router.py:276-344,472-486:
  usar el parámetro _user (hoy sin usar) para comprobar owner/organización.
- routers/redaccion/anonymization_router.py:73-86: el bypass admin no debe cruzar tenants.
- api/v1/ingestion.py user_upload: añadir assert_chatbot_access (ME-3).

## Tests (RED primero) — ampliar tests/api/test_tenant_isolation.py (GATE DE CI)
# should_forbid_run_scenario_on_other_org_chatbot
# should_forbid_delete_other_org_organizacion
# should_list_only_own_org_sites_and_findings
# should_forbid_content_gap_analysis_on_other_org_chatbot
# should_forbid_crud_prompt_template_of_other_org_chatbot
# should_forbid_export_task_of_other_org
# should_forbid_feedback_write_on_other_org_interaction
# should_forbid_reading_manifest_or_workspace_of_other_user
# should_forbid_ingestion_upload_without_chatbot_access

## Criterios de cierre
- [ ] El guardarraíl que prohíbe `session.get(HubChatbot/HubWebSite/...,id)` sin pasar por la
      capa de tenencia se extiende de hub_chatbots_router a TODOS estos routers.
- [ ] test_tenant_isolation.py sigue siendo gate obligatorio de CI y cubre los 9 casos nuevos.
```

---

### Prompt SEC.8.2 (RED/GREEN) — Endurecimiento de subidas [AL-7, ME-5]

**Modelo sugerido**: **Sonnet** — patrón conocido (`validate_upload` + clave `uuid4` ya existen en
los endpoints buenos); alcance cerrado.

```
# PROMPT SEC.8.2 (RED/GREEN) — Todas las subidas por validate_upload, sin nombres del cliente
# Deploy: edge

## Cambios
- workspaces_router.py:336-339: NO interpolar file.filename en la ruta de storage. Usar
  os.path.basename o una clave uuid4 (como hub_ingestion_router.py:329-350). Llamar a
  validate_upload (tamaño + tipo) antes de storage.put.
- scripts_router.py:267-305 (describe_test_data, preview_pdf_spans): validate_upload; no guardar
  binario arbitrario como .pdf sin comprobar contenido.
- Barrido: cualquier otro endpoint con UploadFile que llame a storage.put/file.read() sin
  validate_upload.

## Tests (RED primero) — tests/api/redaccion/test_upload_hardening.py
# should_reject_path_traversal_in_workspace_input_filename
# should_reject_oversized_upload_on_workspace_input
# should_validate_content_type_on_preview_pdf
# should_store_under_uuid_key_not_client_filename

## Cierre
- [ ] grep de UploadFile en routers -> todos pasan por validate_upload
```

---

### Prompt SEC.8.3 (RED/GREEN) — Sandbox: gate de producción + auditor AST [AL-4, AL-5]

**Modelo sugerido**: **Sonnet** — gate de config + reglas AST adicionales; el enforcement Docker
ya existe.

```
# PROMPT SEC.8.3 (RED/GREEN) — SANDBOX_MODE=local prohibido en producción + auditor endurecido
# Deploy: edge

## Cambios
- core/config.py get_settings(): si ENVIRONMENT == 'production' y sandbox_mode == 'local'
  -> RuntimeError explícito. (TESTING=1 sigue permitiendo 'local'.)
- script_auditor.py / service script_sandbox auditor: bloquear también
  __builtins__[...] (Subscript), traversal de dunders (__class__/__bases__/__subclasses__),
  y getattr con nombre construido.

## Tests (RED primero)
# tests/core/test_sandbox_prod_gate.py::should_reject_local_sandbox_in_production
# tests/.../test_script_auditor.py::should_block_builtins_subscript_eval
# ...::should_block_dunder_traversal
# ...::should_block_getattr_escape

## Cierre
- [ ] docker-compose.prod.yml: añadir pids_limit al servicio script-sandbox (ME-7)
```

---

### Prompt SEC.8.4 (RED/GREEN) — Cabeceras, entorno y SAML [ME-1, ME-2, ME-6]

**Modelo sugerido**: **Sonnet** — cambios localizados en config y en la lectura de proxy/SAML.

```
# PROMPT SEC.8.4 (RED/GREEN) — X-Forwarded-For, JWT placeholder, hardening SAML
# Deploy: shared

## Cambios
- core/rate_limit.py:89-92: no tomar el primer valor de X-Forwarded-For (controlable por el
  cliente). Usar el número de proxies de confianza (config) y tomar la IP en esa posición, o
  request.client.host detrás de un proxy que reescriba XFF. Documentar el supuesto de Cloud Run.
- core/config.py: en producción, rechazar JWT_SECRET_KEY placeholder ('change-me-in-production')
  y longitud < N.
- core/auth/saml/settings.py:85,51-57: validate_cert=True en parse_remote (o metadata XML inline
  firmada); wantAssertionsSigned=True.

## Tests (RED primero)
# tests/core/test_rate_limit_xff.py::should_not_trust_leftmost_forwarded_for
# tests/core/test_config_prod.py::should_reject_placeholder_jwt_secret_in_production
# tests/core/auth/test_saml_settings.py::should_require_signed_assertions
```

---

### Prompt SEC.8.5 (RED/GREEN) — El widget no embebe un Bearer privilegiado [AL-6]

**Modelo sugerido**: **Opus** — decide el modelo de credencial de sitio / token anónimo acotado y
lo cablea en el endpoint público; riesgo de escalada si se diseña mal. **Coordina con D.1** (el
endpoint del widget), que ya prevé `via='widget_api_key'`.

```
# PROMPT SEC.8.5 (RED/GREEN) — Credencial de sitio de bajo privilegio para el widget
# Deploy: edge (endpoint) + shared (emisión de la credencial)

## Cambios
- Cablear widget_api_key (chatbot_access.py:34,68-72, hoy sin llamante VIA_WIDGET) o emitir un
  token anónimo acotado a un chatbot public_anon, en lugar de embeber un JWT/PAT de sesión.
- frontend/src/widget: consumir la credencial de sitio; retirar el Bearer privilegiado del HTML.
- El endpoint público sigue pasando por las tres guardas (acceso/disponibilidad/cuota) de D.1.

## Tests (RED primero)
# should_reject_widget_credential_on_authenticated_chatbot
# should_scope_widget_credential_to_single_public_anon_chatbot
# should_not_expose_session_bearer_in_widget_bundle
```

---

### Prompt SEC.8.6 (RED/GREEN) — Temas persistentes fuera del disco local [B1]

**Modelo sugerido**: **Sonnet** — mover almacenamiento a tabla; los endpoints y el widget ya
consumen el servicio.

```
# PROMPT SEC.8.6 (RED/GREEN) — Los temas viven en BD, no en data/themes
# Deploy: cloud (la config de temas se sincroniza cloud->edge)

## Objetivo
- hub_themes_router.py:124-183,352 guarda los temas como JSON en Path("data/themes") (efímero en
  Cloud Run, no compartido entre instancias). Tumba el arreglo del widget con tema de MAN.2 #3.

## Cambios
- Modelo HubTheme en HubConfigBase (id, organizacion_id/plataforma, slug, config JSON, nivel de
  la cascada). Migración Alembic + backfill de los temas de data/themes si los hay.
- _save_theme/_load_theme/delete/apply_theme_to_chatbot/get_theme_for_chatbot -> BD.
- Conservar la validación de slug (regex ^[a-z0-9-]{1,64}$) y la censura pública de SEC.5.

## Tests (RED primero)
# should_persist_theme_across_restarts (no depende de disco local)
# should_resolve_theme_for_chatbot_from_db
# should_keep_slug_validation_and_public_scoping
```

---

### Prompt SEC.8.7 (RED/GREEN) — Limpieza de los tests legacy de la raíz `tests/` [B3]

**Modelo sugerido**: **Sonnet** — retirada mecánica verificada por grep/colección (Caso B).

```
# PROMPT SEC.8.7 — Cero rojos al colectar desde la raíz del repo
# Deploy: n/a (higiene)

## Contexto
- 14 tests rotos en el árbol raíz tests/ (no server/tests): 12 fallan por importar rutas que
  CUR.1 movió a modules/curation (test_spiders_especializados.py, test_spider_generic.py) y 2
  errores de colección importan partner_billing_service/partner_scripts_service inexistentes.
- Los spiders quedaron SIN test en la suite canónica (server/tests): hay que darles cobertura ahí.

## Cambios
- Mover/rescribir los tests de spiders a server/tests/modules/curation apuntando a las rutas
  nuevas (modules/curation/spider_factory, spiders/*).
- Borrar tests/unit/test_partner_billing.py y test_partner_scripts_service.py (código eliminado).
- Barrido de la raíz tests/ por más imports a módulos inexistentes.

## Cierre
- [ ] pytest --collect-only DESDE LA RAÍZ del repo sin errores
- [ ] Los spiders tienen test en server/tests (el que corre en CI)
- [ ] grep -rn "ingestion.spider_factory\|ingestion.spiders\|partner_billing_service\|partner_scripts_service" tests/ = 0
```

---

### Prompt SEC.8.8 (DECISIÓN + RED/GREEN) — El crawler de curación: cablear o acotar alcance [B2]

**Modelo sugerido**: **Sonnet** (implementación) — pero antes una **decisión de criterio** del
usuario sobre el alcance del v1.

**Objetivo**: `main.py:94-99` construye el job de curación con `_NullCrawler()` y `detectors=[]`,
y no existe mecanismo real de inyección (`SpiderFactory`/`SiteCrawler` sin llamante de producción)
→ `POST /hub/sites/{id}/crawl` siempre acaba en `"no spider configured"`. Dos caminos:

```
# PROMPT SEC.8.8 — Curación web: cablear el crawler real O acotar el v1
# Deploy: edge

## Decisión tomada (usuario, 2026-08-10): camino (A), cablear.
# El rastreo es la ENTRADA del flujo de curación —descubrir, auditar, seleccionar,
# publicar—, así que desactivarlo no dejaba "una funcionalidad menos": vaciaba la
# herramienta que CUR.2 acababa de construir. Cablearlo NO contradice
# DECISION_CURACION_SEPARADA: el rastreo llena la bandeja del curador y la publicación al
# corpus sigue siendo un botón por candidata. No hay ingesta automática.
#
# Decisión hermana: UNA sola aplicación, ejecución aparte. Curación y asistente comparten
# auth, tenencia, organizaciones, almacenamiento y corpus; partirlos en dos servicios
# duplicaría todo eso y chocaría con la regla de un codebase para ambos modos de
# despliegue. Lo que se separa es el PROCESO que rastrea, no el producto.

## Tests (RED primero)
# should_select_the_spider_declared_by_the_site
# should_fall_back_to_the_generic_spider
# should_report_an_error_for_an_unknown_site
# should_report_an_error_for_an_unknown_spider_type   (no cae al genérico: rastrear el DOGV
#                                                      con el spider equivocado produce
#                                                      páginas basura que revisar a mano)
# should_not_keep_a_null_crawler_in_main              (guardarraíl anti-recaída)
```

> **Pendiente que SEC.8.8 deja abierto y va al bloque Deploy (D.x): el ejecutor de trabajos.**
> El rastreo se encola hoy con `BackgroundTasks`, o sea **dentro del proceso web**. En Cloud
> Run la instancia escala a cero cuando termina de atender peticiones, así que un rastreo
> largo muere a media ejecución sin dejar rastro —responde 202 y no acaba nunca—. En local,
> en Docker y en un edge con contenedor persistente funciona tal cual, que es lo que hace
> falta para probar la curación antes del despliegue. El paso a un ejecutor duradero (Cloud
> Run Jobs / Cloud Tasks) se planifica como prompt propio de Deploy.

---
