## Bloque CAL — Deuda de calidad previa al repositorio público (Subfase 1.B, PENDIENTE)

> **Contexto**: hallazgos de las auditorías de calidad backend/frontend (`docs/VALORACION_PROYECTO.md` §3). Cierra violaciones de reglas duras del proyecto (Contract-First, sin código muerto, sin shims) antes de abrir el repo bajo AGPLv3.

---

### Prompt CAL.1 (RED/GREEN) — Retirada de NiceGUI de `server/app/ui/` + Caso B en `client_app/` + código huérfano

**Modelo sugerido**: **Sonnet** — retirada mecánica con verificación por grep (Caso B de CLAUDE.md).

> **Ampliado 2026-07-11** con la limpieza Caso B de `client_app/` identificada en el triaje del
> replanteamiento de Fase 2 (Plan_TDD_Fase2.md §3, Categoría B). Verificado contra git:
> el `.venv/` de client_app NO está trackeado (solo ruido de disco local, fuera de alcance);
> los 5 UI `_legacy` y los artefactos autogenerados SÍ están trackeados.

```
# PROMPT CAL.1 (RED/GREEN) — Retirar NiceGUI del árbol activo del servidor + Caso B client_app

## Análisis previo (solo lectura)
- Confirmar que ningún módulo activo importa `server.app.ui` (grep). Confirmado en auditoría.
- Confirmar que nada importa los 5 UI `_legacy` de client_app ni los artefactos de
  `client_app/app/modules/extraccion/` (grep en client_app/app y client_app/tests).

## Acción — servidor
- Mover server/app/ui/ (22 ficheros NiceGUI: admin_security.py, admin_clients.py,
  partner_security.py, etc.) a _legacy_nicegui/server/app/ui/ (mantener ruta relativa, Caso A)
  O borrar directamente si no hay migración React asociada (Caso B — la mayoría son admin
  NiceGUI ya cubiertos por el panel React). Decidir por fichero.
- Borrar los tests que los mantienen vivos: tests/unit/test_admin_*_ui.py
  (test_admin_clients_ui, test_admin_partners_ui, test_admin_prompts_ui, test_admin_security_ui).
- Borrar el huérfano top-level app/modules/extraccion/ (12 ficheros, sin importadores → Caso B).
- Borrar los scripts ad-hoc en tests/ que no son tests (reproduce_client_id.py, verify_id_logic_standalone.py).

## Acción — client_app (Caso B: borrado directo, sin _legacy_nicegui)
- Borrar los 5 UI legacy explícitos (reemplazados por versiones posteriores):
    client_app/app/ui/_legacy_webhook_page.py
    client_app/app/ui/connections_page_legacy.py
    client_app/app/ui/custom_script_page_legacy.py
    client_app/app/ui/graphics_page_legacy.py
    client_app/app/ui/rpa_page_legacy.py
- Borrar los artefactos autogenerados trackeados (salida de runtime, no código fuente):
    client_app/app/modules/extraccion/.servicios_generados/custom_extractor*.py
    client_app/app/modules/extraccion/servicios/custom_prueba*.py
  Conservar solo el __init__.py si algo vivo importa el paquete; si nada lo importa,
  borrar el directorio completo.
- .gitignore: añadir client_app/app/modules/extraccion/.servicios_generados/ y
  client_app/app/modules/extraccion/servicios/ (evitar que el runtime los re-trackee).
- Si algún test de client_app/tests referenciaba lo borrado, borrarlo también (es test
  de código muerto).

## FUERA DE ALCANCE (no tocar en este prompt)
- Los imports rotos a factories inexistentes (workflow_engine.py:1417/1478,
  clarification_service.py:504, graphics_wizard.py:8): esos ficheros son Categoría C
  pendiente de decisión go/no-go (Plan_TDD_Fase2.md §4); se resuelven con esa decisión.
- El report_factory duplicado (services/ vs modules/factory/): decidir cuál sobra
  pertenece a la misma decisión de Categoría C.
- client_app/.venv/: no está en git; borrado de disco a discreción del usuario.

## Tests / verificación
# should_have_no_nicegui_imports_in_server_app        (grep 'from nicegui' en server/app = 0)
# should_have_no_references_to_server_app_ui           (grep = 0)
# should_collect_pytest_without_removed_ui_tests       (pytest --collect-only sin errores)
# should_have_no_legacy_ui_files_in_client_app         (glob '*_legacy*' en client_app/app/ui = 0)
# should_have_no_generated_extractors_tracked          (git ls-files 'client_app/app/modules/extraccion/**' = 0 o solo __init__.py)
# should_collect_client_app_tests_without_errors       (pytest --collect-only en client_app/tests sin errores)

## Cierre
- [ ] `grep -rn "from nicegui\|server.app.ui\|modules.extraccion" server/` = 0
- [ ] `grep -rn "_legacy_webhook_page\|connections_page_legacy\|custom_script_page_legacy\|graphics_page_legacy\|rpa_page_legacy" client_app/` = 0
- [ ] `git ls-files client_app/app/modules/extraccion` vacío (o solo __init__.py justificado)
- [ ] Suite backend en verde tras la retirada; colección de tests de client_app sin errores
```

---

### Prompt CAL.2 (RED/GREEN) — Migrar la capa API manual del frontend a Orval (cierra CF.4)

**Modelo sugerido**: **Opus** — refactor transversal que toca la página más grande (DocumentsPage) y alinea con el contrato; riesgo de regresión alto.

```
# PROMPT CAL.2 (RED/GREEN) — Eliminar shared/api/*.ts hechos a mano

## Objetivo
- Retirar los 5 módulos con fetch crudo + tipos hardcodeados + API_BASE a localhost:
  shared/api/{ingestion,clients,feedback,llmConfigs,promptTemplates}.ts (cierra el
  literal '// TODO CF.4' de ingestion.ts).

## Acción
- Sustituir cada llamada por el hook Orval generado (useX de shared/api/generated) y los
  tipos de generated/model (IngestionJob, HubDocument, etc. → tipos del contrato).
- Pasar todo por el customInstance (interceptor de auth) en lugar de headers duplicados.
- El streaming SSE del chat del widget queda EXENTO (Orval no cubre SSE); ese fetch se
  mantiene pero centralizando la construcción de Authorization.
- Borrar los 5 ficheros y actualizar los imports (DocumentsPage.tsx:16 y demás consumidores).

## Tests Vitest (RED primero)
# should_use_generated_hook_not_manual_fetch_in_documents_page
# should_not_import_from_shared_api_manual_modules       (los 5 ficheros ya no existen)
# should_send_auth_via_custom_instance
# should_type_ingestion_job_from_generated_model

## Cierre
- [ ] `grep -rn "shared/api/(ingestion|clients|feedback|llmConfigs|promptTemplates)" frontend/src` = 0
- [ ] `grep -rn "localhost:8000" frontend/src` = 0 (fuera de config de dev)
- [ ] tsc --noEmit + vitest en verde
```

---

### Prompt CAL.3 (RED/GREEN) — Descomponer DocumentsPage

**Modelo sugerido**: **Sonnet** — refactor de composición sin cambio de comportamiento.

```
# PROMPT CAL.3 (RED/GREEN) — Partir DocumentsPage.tsx (1019 líneas)

## Acción
- Extraer subcomponentes con responsabilidad única: <UploadDropzone>, <SourcesPanel>
  (sitios/spider), <DocumentsTable>, <IngestionJobsPanel>, <RechunkControls>.
  DocumentsPage queda como orquestador (<300 líneas).
- Sin cambio de comportamiento; los datos siguen viniendo de hooks Orval (CAL.2).

## Tests Vitest (RED primero → mantener verdes tras el split)
# should_render_upload_dropzone_component
# should_render_sources_panel_component
# should_render_documents_table_component
# should_render_jobs_panel_component
# should_keep_existing_documents_page_behaviour     (tests actuales siguen pasando)
```

---

### Prompt CAL.4 (RED/GREEN) — i18n: completar `ca/admin.json` + retirar strings hardcodeados

**Modelo sugerido**: **Sonnet** — alcance cerrado, verificable por conteo de claves.

```
# PROMPT CAL.4 (RED/GREEN) — Cobertura i18n del panel admin

## Acción
- Completar shared/i18n/locales/ca/admin.json a paridad con es/en (hoy ~34 vs ~130 líneas).
- Extraer a claves i18n los literales en español de LLMConfigsPage (~22), ChatbotsPage (~12)
  y las constantes con etiquetas de DocumentsPage (INTERVAL_OPTIONS, LANGUAGE_OPTIONS,
  RETRIEVAL_LABELS, SPIDER_TYPES → usar t() en render, no strings fijos en el array).
- Asociar labels a inputs (htmlFor/id) donde falten (relacionado con a11y de Fase 20).

## Tests Vitest (RED primero)
# should_have_key_parity_across_es_ca_en_admin_namespace
# should_not_render_hardcoded_spanish_in_llmconfigs_page
# should_render_interval_options_via_i18n
# should_associate_labels_with_inputs
```

---

### Prompt CAL.5 (RED/GREEN) — Code-splitting (lazy routes) + retirada de shims

**Modelo sugerido**: **Sonnet** — cambio de build + limpieza puntual.

```
# PROMPT CAL.5 (RED/GREEN) — Bundle y shims

## Frontend
- App.tsx: convertir los imports estáticos de páginas en React.lazy + <Suspense> por ruta
  → romper el chunk monolítico (~927 KB). Verificar chunks por ruta en el build.

## Backend
- Eliminar los shims prohibidos por CLAUDE.md: `init_db = init_server_db` (db.py:31-32) y
  el "Legacy alias" de seeds.py:174-176. Actualizar los llamantes al nombre real.

## Tests
# (frontend) should_lazy_load_route_chunks               (assert de dynamic import)
# (frontend) should_not_bundle_all_pages_in_single_chunk (inspección del manifest de build)
# (backend)  should_import_init_server_db_directly        (grep 'init_db' = 0 fuera de la definición)
# (backend)  should_have_no_legacy_aliases_in_seeds
```

---

### Prompt CAL.4.1 (RED/GREEN) — Las 41 claves de la pantalla de documentos

**Modelo sugerido**: **Sonnet** — alcance cerrado y verificable por conteo de claves.

**Por qué existe**: CAL.4 dejó `es`/`ca`/`en` en paridad y el test en verde, pero la paridad es
de claves **del diccionario**. La pantalla de documentos casi no tiene: sus etiquetas viven como
*default* dentro del `t('clave', 'texto')`, y el default sólo actúa cuando la clave **falta**. El
resultado es que con `i18nextLng=ca` la navegación sale en catalán y el cuerpo de esa pantalla se
queda en castellano. Medido el 2026-08-03 con el árbol de CAL.5.

```
# PROMPT CAL.4.1 (RED/GREEN) — Subir al diccionario las claves que sólo viven como default

## Contexto medido (no hay que volver a contarlo)
- 41 claves del namespace `admin` se usan como t('hub.x', 'texto') y NO están en
  es/ca/en admin.json. Reparto por fichero:
    admin/documents/DocumentsTable.tsx      12
    admin/documents/IngestionJobsPanel.tsx   7
    admin/documents/RechunkControls.tsx      7
    admin/pages/DocumentsPage.tsx            5
    admin/documents/RetrievalBanner.tsx      4
    admin/documents/UploadDropzone.tsx       4
    admin/documents/DocumentBadges.tsx       2
- El texto castellano actual es el que ya está en el segundo argumento de t():
  se sube tal cual a es/admin.json y se traduce a ca/en.

## Acción
- Subir las 41 claves a es/ca/en admin.json conservando el texto castellano actual.
- Dejar el t() con un solo argumento donde la clave ya exista: un default que nunca se
  usa es texto muerto que se desincroniza del diccionario sin que nadie lo note.
- OJO con las cadenas fijas que aún no pasan por t() en esos ficheros: los estados de
  JobStatusBadge ('Completado', 'Procesando', 'Error', 'En cola') están escritos a pelo
  en el switch. Entran también.

## Tests Vitest (RED primero)
# should_not_keep_admin_keys_only_as_inline_default
#   Barre src/ buscando t('hub.x', '...') y falla si la clave no está en es/admin.json.
#   Es el guardarrail que faltaba: el de paridad NO puede cazar esto por construcción,
#   porque lo que no está en el diccionario no se compara con nada.
# should_render_documents_screen_in_catalan
#   Render de DocumentsPage con el doble de i18n resolviendo contra ca/admin.json;
#   assert sobre texto catalán, no sobre la clave.

## Cierre
- [ ] Paridad es/ca/en sigue verde y sube a ~259 claves
- [ ] `i18nextLng=ca` en el navegador: la pantalla de documentos, entera en catalán
- [ ] vitest + tsc --noEmit en verde (la suite en serie: ver la nota de falsos rojos)
```

---
