# Inventario de la retirada del legacy NiceGUI

Este documento existe para que **nada se borre antes de estar cubierto**. Cruza los 187 ficheros
de `client_app/app/ui` y `client_app/app/services` contra lo que hoy existe en el servidor y en el
frontend, y le pone a cada uno una de cuatro etiquetas con su justificación.

> Bloque **NIC**, prompt NIC.1 (2026-09-04). **Este prompt no mueve ni borra nada**: sólo mira.
> Lo que se hace con cada etiqueta lo deciden NIC.2 y NIC.3.

Lo mantiene honesto `server/tests/infra/test_nic1_el_inventario_esta_completo.py`, que compara las
filas contra `git ls-files`: si falta un fichero, si a una fila le falta la etiqueta o si la
justificación está vacía, la suite se pone roja. Lo que un test **no** puede comprobar es que la
etiqueta sea *correcta* —que `anonymizer_page.py` esté de verdad cubierto por
`WorkspaceAnonymizationPanel.tsx` lo decide quien lea las dos cosas—, así que las filas «cubierto»
citan el equivalente concreto para que se pueda contrastar.

---

## 1. Lo primero que hay que saber: contra qué se cruza

El plan del bloque decía cruzar contra `server/app/modules/automation/` y
`frontend/src/automation/`. **Medido hoy, ese destino está prácticamente vacío**:

| Destino que suponía el plan | Ficheros versionados |
|---|---|
| `server/app/modules/automation/` | **5** |
| `frontend/src/automation/` | **0** |

Lo que sí existe, y es donde la funcionalidad de AutomatIA aterrizó de verdad, es el módulo de
**redacción de informes**:

| Destino real | Ficheros versionados |
|---|---|
| `server/app/modules/redaccion/` | **96** |
| `frontend/src/redaccion/` | **53** |
| `server/app/routers/redaccion/` | **10** |

Así que el cruce se hace contra `redaccion/` (más `agents_hub/`, `core/` y el microservicio
`services/script_sandbox/`), y no contra `automation/`. **Es una desviación del prompt y está
aquí escrita**: mantener la letra del plan habría dado «no cubierto» a los 187 ficheros, lo cual
es falso y además inútil.

---

## 2. El recuento

| Etiqueta | Ficheros | Qué significa | Qué se hace con ellos |
|---|---|---|---|
| **cubierto** | 40 | Hay equivalente verificado, citado en la fila | NIC.2 los mueve a `_legacy_nicegui/` |
| **parcial** | 23 | Existe parte, y la fila dice qué falta | **No se tocan.** Salen del bloque y se planifican aparte |
| **no cubierto** | 97 | No hay nada equivalente | **No se tocan.** Ídem |
| **no aplica** | 27 | Era andamiaje de NiceGUI o resto temporal | NIC.2 los borra directamente (Caso B) |
| | **187** | | |

**La lectura que importa: sólo 40 de 187 ficheros están cubiertos, y
97 no tienen nada.** La regla de `CLAUDE.md` dice que `client_app/` debería
contener sólo el agente de ejecución local; el cruce dice que llegar ahí no es una limpieza, es
trabajo de migración que nadie ha hecho todavía.

### Dónde está el bulto de lo no cubierto

Casi todo lo «no cubierto» cae en cuatro familias, y **tres tienen dueño**:

- **El editor de flujos y el sistema de átomos** —galería, asistente, configurador de pasos,
  variables, puentes de tipo, contratos entre átomos, importación y exportación de paquetes—. Lo
  planifica el **bloque FUN**, que está pendiente. Es la familia más grande.
- **La interfaz de configuración de los vigilantes** (carpeta, correo, web), los disparadores y la
  programación. **El agente sí existe** en `client_app/app/modules/watchers/`; lo que no existe es
  su pantalla, que pertenece al frontend. Varias filas están marcadas «**decide NIC.3**» porque
  hay que resolver si el servicio es parte del agente o era interfaz.
- **La interfaz de RPA** y el asistente de Playwright. El ejecutor (`app/core/rpa_executor.py`) se
  queda; su pantalla no está.
- **Conexiones a datos** (SQL, API) como acciones configurables; también FUN.

Y una que no tiene dueño y conviene decidir: **conocimiento local y sincronización cliente↔nube**
(`local_knowledge_service.py`, `sync_manager.py`, `sync_service.py`). `api/v1/edge_sync.py` son
**dos stubs 501**: el mecanismo está planificado y no hecho.

### Dos hallazgos de paso

- **`client_app/app/services/design_sandbox_service.py` no compila.** `ast.parse` da `SyntaxError`,
  así que además de estar cubierto por el sandbox es código muerto que nadie ejecuta.
- **`client_app/app/services/extraction_service.py` tiene 3.494 líneas**, el fichero más grande del
  legacy, y `client_app/app/ui/ui_translations.json` pesa **60 KB**. Los dos están etiquetados
  «parcial» a propósito: hay que leerlos antes de decidir, y no cabe en este prompt.

---

## 3. El inventario, fichero a fichero

Ordenado por ruta. La tercera columna es la justificación: en las filas «cubierto» es el
equivalente concreto; en «parcial», qué falta.

| Fichero | Etiqueta | Equivalente o razón |
|---|---|---|
| `client_app/app/services/__init__.py` | **no aplica** | Paquete de servicios del cliente. |
| `client_app/app/services/api_connection_service.py` | **no cubierto** | Conexiones a API externas; FUN. |
| `client_app/app/services/api_key_service.py` | **cubierto** | `hub_provider_credentials` con `MetodoDeCredencial` + los PAT de `core/auth/pat/`. |
| `client_app/app/services/asset_finishing_service.py` | **no cubierto** | 787 líneas de «sellado atómico»; FUN. |
| `client_app/app/services/atom_service.py` | **no cubierto** | Gestión de átomos reutilizables; FUN. |
| `client_app/app/services/automatism_export_service.py` | **no cubierto** | 640 líneas de exportación de automatismos; FUN. |
| `client_app/app/services/automatism_import_service.py` | **no cubierto** | 778 líneas de importación; FUN. |
| `client_app/app/services/bridge_creator.py` | **no cubierto** | Creación de puentes de tipo entre átomos; FUN. |
| `client_app/app/services/bridge_generation_service.py` | **no cubierto** | Generación de puentes con IA; FUN. |
| `client_app/app/services/clarification_service.py` | **no cubierto** | 565 líneas de clarificaciones previas a generar; FUN. |
| `client_app/app/services/cleanup_service.py` | **no cubierto** | **Decide NIC.3**: limpieza de ficheros temporales del cliente. |
| `client_app/app/services/coherence_service.py` | **no aplica** | 49 líneas sin docstring, del editor de flujos. |
| `client_app/app/services/config_service.py` | **cubierto** | `core/config.py` (`Settings` por entorno). |
| `client_app/app/services/connection_contract_builders.py` | **no cubierto** | Contratos de conexión; FUN. |
| `client_app/app/services/connection_logger_service.py` | **no cubierto** | Registro de eventos de conexión; FUN. |
| `client_app/app/services/contract_validator_service.py` | **parcial** | `contracts/block_io.py` valida la entrada y salida de un bloque; la validación de contratos **entre átomos** es el bloque FUN. |
| `client_app/app/services/copilot_context_service.py` | **cubierto** | `services/copilot/copilot_service.py`, `docs_retriever.py` y `contexto_del_informe.py`. |
| `client_app/app/services/custom_script_service.py` | **cubierto** | `services/script_proposal_service.py` + `pipelines/admin_script_pipeline.py`. |
| `client_app/app/services/data_contract_service.py` | **parcial** | Ídem: 905 líneas del contrato entre átomos, del que sólo la parte de bloques tiene equivalente. |
| `client_app/app/services/data_flow_analyzer.py` | **no cubierto** | Variables y contexto del editor de flujos; FUN. |
| `client_app/app/services/design_sandbox_service.py` | **cubierto** | Mismo equivalente que el sandbox. **Nota: este fichero no compila hoy** (`SyntaxError`), así que además es código muerto. |
| `client_app/app/services/dev_crypto_service.py` | **cubierto** | `hub_provider_credentials` guarda el nombre del secreto, no el secreto; en producción lo da Secret Manager (D.2). |
| `client_app/app/services/doc_generator_service.py` | **no cubierto** | Generación de documentación de automatismos; FUN. |
| `client_app/app/services/email_body_utils.py` | **no cubierto** | **Decide NIC.3**: limpieza del cuerpo de los correos que recoge el agente. |
| `client_app/app/services/email_scan_service.py` | **no cubierto** | **Decide NIC.3**: recolección pasiva de correos para flujos. |
| `client_app/app/services/enterprise_audit_service.py` | **parcial** | `graph/nodes/audit_log.py` + `hub_actividad_ia` (REG.1) cubren el registro; el informe de auditoría empresarial del legacy, no. |
| `client_app/app/services/event_bus_service.py` | **no cubierto** | **Corregido en NIC.2**: estaba «no aplica», y lo importan `app/modules/watchers/email_watcher.py` y `folder_watcher.py`, que son **el agente que se queda**. «No aplica» significa borrar, así que la etiqueta habría roto lo único que `client_app/` debe conservar. **Decide NIC.3** si el bus es parte del agente. |
| `client_app/app/services/execution_session_service.py` | **parcial** | `hub_workspaces` y `services/workspace_run_service.py` cubren la sesión de un informe; la de un flujo, no. |
| `client_app/app/services/external_script_audit_service.py` | **cubierto** | `services/script_auditor.py`, y expuesto como servicio en `POST /api/v1/verificaciones/codigo` (VAS.3). |
| `client_app/app/services/extraction_service.py` | **parcial** | **3.494 líneas**, el fichero más grande del legacy. `extraction_strategies.py` y los cuatro *pipelines* cubren la extracción determinista; lo demás hay que leerlo antes de decidir. |
| `client_app/app/services/field_import_service.py` | **no cubierto** | Importación masiva de definiciones de campo desde Excel; FUN. |
| `client_app/app/services/file_system_service.py` | **no cubierto** | **Decide NIC.3**: operaciones de ficheros para flujos locales. |
| `client_app/app/services/flow_compatibility_service.py` | **no cubierto** | Compatibilidad entre átomos de un flujo; FUN. |
| `client_app/app/services/flow_diagram_generator.py` | **no cubierto** | Diagramas Mermaid de un flujo; FUN. |
| `client_app/app/services/flow_migration_service.py` | **no cubierto** | Migración de flujos al sistema de átomos; FUN. |
| `client_app/app/services/flow_registry_service.py` | **no cubierto** | Registro de flujos; FUN. |
| `client_app/app/services/flow_validation_service.py` | **no cubierto** | Validación de flujos; FUN. |
| `client_app/app/services/folder_watcher_service.py` | **no cubierto** | **Decide NIC.3**: es la configuración y el ciclo de vida del vigilante, y el vigilante se queda en `client_app/`. |
| `client_app/app/services/health_service.py` | **cubierto** | El endpoint `/health` de `main.py`. |
| `client_app/app/services/import_validation_service.py` | **no cubierto** | Validación de paquetes importados; FUN. |
| `client_app/app/services/knowledge_orchestrator_service.py` | **no cubierto** | Orquestador de conocimiento del lado cliente; sin equivalente. |
| `client_app/app/services/launcher.py` | **no aplica** | Lanzador del proceso NiceGUI (65 líneas). |
| `client_app/app/services/layout_manager.py` | **no cubierto** | **Corregido en NIC.2**: estaba «no aplica», y lo importa `app/core/state.py` —el estado global que ata la interfaz al `RPAExecutor`— más quince páginas que se quedan. **Decide NIC.3** si `state.py` es agente o era interfaz. |
| `client_app/app/services/library_bridge.py` | **no aplica** | Puente de 27 líneas entre dos servicios del legacy. |
| `client_app/app/services/local_knowledge_service.py` | **no cubierto** | Base de conocimiento local del cliente; sin equivalente (el corpus vive en el servidor). |
| `client_app/app/services/mail_watcher_service.py` | **no cubierto** | **Decide NIC.3**: ídem para el de correo (796 líneas). |
| `client_app/app/services/manifest_generator.py` | **no cubierto** | Manifiesto **de paquete de automatismos**, que no es el `RunManifest` de informes: son cosas distintas. |
| `client_app/app/services/manifest_signature_service.py` | **no cubierto** | Firma del manifiesto de paquete; sin equivalente. |
| `client_app/app/services/naming_service.py` | **no cubierto** | Nombres provisionales de átomos y flujos; FUN. |
| `client_app/app/services/pdf_tools_service.py` | **no cubierto** | Lo mismo: `pdfplumber` extrae, pero no manipula PDF. |
| `client_app/app/services/preview_data_service.py` | **no cubierto** | Previsualización de datos en el diseño de flujos; FUN. |
| `client_app/app/services/privacy_guardian.py` | **cubierto** | `services/anonymization/run_context.py` (el mapa no sale del nodo). |
| `client_app/app/services/promotion_service.py` | **no aplica** | 40 líneas de promoción entre entornos del legacy. |
| `client_app/app/services/received_emails_service.py` | **no cubierto** | **Decide NIC.3**: consulta de correos recibidos. |
| `client_app/app/services/report_analyzer_service.py` | **parcial** | `services/estructura_del_informe.py` y `contexto_del_informe.py` cubren el análisis de estructura; el análisis de un informe **ya generado** no tiene equivalente. |
| `client_app/app/services/report_factory.py` | **parcial** | El renderizado sin cabeza está en `services/export_service.py` y `charts/chart_renderer.py`; el de Playwright para HTML completo no se migró. |
| `client_app/app/services/report_mapping_validator.py` | **cubierto** | `contracts/block_io.py` + `graph/nodes/validate_inputs.py`. |
| `client_app/app/services/report_service.py` | **cubierto** | `services/drafting_runner.py` + `graph/core_graph.py`. |
| `client_app/app/services/report_suggestion_service.py` | **cubierto** | `graph/nodes/ai_assist_draft.py` + `services/redactor_de_bloques.py`. |
| `client_app/app/services/resource_listing_service.py` | **no cubierto** | Listado de recursos del editor; FUN. |
| `client_app/app/services/rpa_library_sync.py` | **no cubierto** | **Decide NIC.3**: sincronización de la biblioteca de RPA. |
| `client_app/app/services/sandbox_service.py` | **cubierto** | `services/script_sandbox/` (microservicio) + `core/sandbox_client.py`. |
| `client_app/app/services/sandbox_worker.py` | **cubierto** | `services/script_sandbox/sandbox/` corre el subproceso efímero. |
| `client_app/app/services/scheduler_service.py` | **no cubierto** | **Decide NIC.3**: programación de ejecuciones de flujos en la máquina del cliente. |
| `client_app/app/services/screenshot_guard.py` | **no cubierto** | **Decide NIC.3**: protección de capturas del ejecutor RPA. |
| `client_app/app/services/script_adaptation_service.py` | **parcial** | `services/script_proposal_service.py` genera y adapta propuestas; la adaptación de un script **existente** a otro contrato no tiene equivalente. |
| `client_app/app/services/script_generator_service.py` | **cubierto** | `services/script_proposal_service.py` (generación con IA y propuesta revisable). |
| `client_app/app/services/script_ingestion_service.py` | **parcial** | La ingesta con doble origen (autoservicio/empaquetado) es el bloque FUN; hoy sólo hay la propuesta revisable. |
| `client_app/app/services/script_library_service.py` | **cubierto** | `services/script_proposal_service.py` + `hub_script_proposals`. |
| `client_app/app/services/security_service.py` | **cubierto** | `services/script_auditor.py` (auditoría AST con tres niveles); unificado en `shared/`. |
| `client_app/app/services/sql_connector_service.py` | **no cubierto** | Conector SQL; FUN. |
| `client_app/app/services/step_tester_service.py` | **no aplica** | 45 líneas de prueba de un paso del editor de flujos. |
| `client_app/app/services/support/support_packager.py` | **no aplica** | Empaquetador de información de soporte del legacy. |
| `client_app/app/services/sync_manager.py` | **no cubierto** | Sincronización cliente↔nube. `api/v1/edge_sync.py` son **dos stubs 501**: el mecanismo está planificado, no hecho. |
| `client_app/app/services/sync_service.py` | **no cubierto** | Ídem: la sync API real no existe todavía. |
| `client_app/app/services/temp_check.txt` | **no aplica** | Fichero temporal de 238 bytes dejado por error. |
| `client_app/app/services/trigger_lifecycle_manager.py` | **no cubierto** | **Decide NIC.3**: ciclo de vida de los disparadores del agente. |
| `client_app/app/services/type_coercion_service.py` | **no cubierto** | Coerción de tipos entre átomos; FUN. |
| `client_app/app/services/type_compatibility_service.py` | **no cubierto** | 716 líneas de compatibilidad de tipos entre átomos; FUN. |
| `client_app/app/services/validation_loop.py` | **no cubierto** | Bucle de validación del editor de flujos; FUN. |
| `client_app/app/services/web_watcher_service.py` | **no cubierto** | **Decide NIC.3**: ídem para el web (878 líneas). |
| `client_app/app/services/workflow_scheduler_service.py` | **no cubierto** | **Decide NIC.3**: ídem. |
| `client_app/app/ui/__init__.py` | **no aplica** | Paquete vacío de la interfaz NiceGUI. |
| `client_app/app/ui/anonymizer_page.py` | **cubierto** | `components/WorkspaceAnonymizationPanel.tsx` + `routers/redaccion/anonymization_router.py`. |
| `client_app/app/ui/api_fetch_page.py` | **no cubierto** | Llamada a API como acción; FUN. |
| `client_app/app/ui/archive_file_page.py` | **no cubierto** | Archivado de ficheros como acción; sin equivalente. |
| `client_app/app/ui/asistente_informes_translations.json` | **cubierto** | `frontend/src/shared/i18n/locales/{es,ca,en}/redaccion.json` con i18next. |
| `client_app/app/ui/atoms_page.py` | **no cubierto** | Su propio docstring dice `[LEGACY]`. Administración de acciones; FUN. |
| `client_app/app/ui/atoms_translations.json` | **no cubierto** | Cadenas de la administración de átomos. |
| `client_app/app/ui/audit_page.py` | **parcial** | `graph/nodes/audit_log.py` y el registro de actividad (REG) cubren el rastro; la pantalla de auditoría del legacy, no. |
| `client_app/app/ui/audit_translations.json` | **parcial** | Cadenas de la pantalla de auditoría. |
| `client_app/app/ui/client_admin_page.py` | **no cubierto** | 652 líneas de administración del cliente local; sin equivalente. |
| `client_app/app/ui/components/__init__.py` | **no aplica** | Paquete de componentes NiceGUI. |
| `client_app/app/ui/components/anonymizer_field_row.py` | **cubierto** | `components/TestDataAnonymizerForm.tsx`. |
| `client_app/app/ui/components/atom_gallery.py` | **no cubierto** | Galería de selección de átomos; FUN. |
| `client_app/app/ui/components/atom_wizard.py` | **no cubierto** | Asistente de creación de átomos; FUN. |
| `client_app/app/ui/components/automation_selector.py` | **no cubierto** | Selector de automatismo; FUN. |
| `client_app/app/ui/components/clarification_dialog.py` | **no cubierto** | Diálogo de clarificación previa a generar; FUN. |
| `client_app/app/ui/components/connections_manager.py` | **no cubierto** | Gestión de conexiones; FUN. |
| `client_app/app/ui/components/contract_viewer.py` | **parcial** | `components/ScriptCodePreview.tsx` y `SandboxTestResultViewer.tsx` muestran contratos de script; el visor de contratos entre átomos, no. |
| `client_app/app/ui/components/copilot_chat.py` | **cubierto** | `frontend/src/shared/layout/copilot/CopilotPanel.tsx` + `routers/redaccion/copilot_router.py`. |
| `client_app/app/ui/components/data_source_selector.py` | **no cubierto** | 1.059 líneas de selección de fuentes de datos para el editor de flujos; FUN. |
| `client_app/app/ui/components/database_connection_manager.py` | **no cubierto** | Gestión de conexiones a base de datos; FUN. |
| `client_app/app/ui/components/drawer_hub.py` | **no aplica** | Contenedor del cajón lateral de NiceGUI. |
| `client_app/app/ui/components/dynamic_form.py` | **cubierto** | `components/DynamicFieldRenderer.tsx`, que construye el formulario del `ui_contract`. |
| `client_app/app/ui/components/email_review_panel.py` | **no cubierto** | Revisión de correos recibidos; sin equivalente. |
| `client_app/app/ui/components/escalation_dialog.py` | **no cubierto** | Diálogo de escalado; FUN. |
| `client_app/app/ui/components/extraction_wizard.py` | **parcial** | `DynamicUploadSlots.tsx` cubre subir el fichero; configurar la extracción desde el asistente, no. |
| `client_app/app/ui/components/file_type_selector.py` | **no aplica** | Selector de tipo de fichero de NiceGUI. |
| `client_app/app/ui/components/form_factory.py` | **cubierto** | `components/ReportUIContractRenderer.tsx` + `contracts/ui.py` (SDUI). |
| `client_app/app/ui/components/graphics_wizard.py` | **cubierto** | `services/charts/chart_configuration.py` + `routers/redaccion/charts_router.py`. |
| `client_app/app/ui/components/markdown_editor.py` | **cubierto** | `BlockEditor.tsx` (edición) y `PreviewRenderer.tsx` (vista previa). |
| `client_app/app/ui/components/markdown_viewer.py` | **no cubierto** | Visor de documentación de la página anterior. |
| `client_app/app/ui/components/page_header.py` | **no aplica** | Cabecera de página de NiceGUI (19 líneas). |
| `client_app/app/ui/components/pdf_file_list.py` | **no cubierto** | Lista reordenable de PDF para las herramientas anteriores. |
| `client_app/app/ui/components/privacy_indicator.py` | **cubierto** | El estado de anonimización lo pinta `WorkspaceAnonymizationPanel.tsx` (9 líneas en el legacy). |
| `client_app/app/ui/components/privacy_report.py` | **cubierto** | `WorkspaceAnonymizationPanel.tsx` + el resumen del `RunManifest`. |
| `client_app/app/ui/components/report_block_editor.py` | **cubierto** | `frontend/src/redaccion/components/BlockEditor.tsx` + `blocks/handlers.py`. |
| `client_app/app/ui/components/report_template_selector.py` | **cubierto** | Selección de plantilla dentro de `GenericReportWizard.tsx`. |
| `client_app/app/ui/components/resource_card.py` | **no aplica** | Tarjeta de recurso de NiceGUI. |
| `client_app/app/ui/components/schema_mapper.py` | **no cubierto** | Mapeo de esquemas entre pasos; FUN. |
| `client_app/app/ui/components/screenshot_review.py` | **no cubierto** | Revisión de capturas de RPA; sin equivalente. |
| `client_app/app/ui/components/script_creation_wizard.py` | **cubierto** | `pages/ScriptProposalWizardPage.tsx`. |
| `client_app/app/ui/components/script_wizard.py` | **cubierto** | `pages/ScriptProposalWizardPage.tsx`. |
| `client_app/app/ui/components/side_drawer.py` | **no aplica** | Cajón lateral de NiceGUI; el panel del copiloto en React es `CopilotPanel.tsx`. |
| `client_app/app/ui/components/smart_stepper.py` | **no aplica** | Paginador de pasos de NiceGUI; los asistentes de React llevan el suyo. |
| `client_app/app/ui/components/standard_page_layout.py` | **no aplica** | Plantilla de página de NiceGUI. |
| `client_app/app/ui/components/step_configurator.py` | **no cubierto** | Configurador de pasos del editor de flujos; FUN. |
| `client_app/app/ui/components/step_forms/__init__.py` | **no cubierto** | Paquete de formularios de paso del editor de flujos; FUN. |
| `client_app/app/ui/components/step_forms/api_fetch_form.py` | **no cubierto** | Formulario del paso API; FUN. |
| `client_app/app/ui/components/step_forms/custom_script_form.py` | **no cubierto** | Formulario de paso del editor de flujos; FUN. |
| `client_app/app/ui/components/step_forms/email_send_form.py` | **no cubierto** | Formulario del paso de envío de correo; FUN. |
| `client_app/app/ui/components/step_forms/extraction_form.py` | **parcial** | El paso de extracción del editor de flujos; el motor existe, el editor de flujos es FUN. |
| `client_app/app/ui/components/step_forms/generic_form.py` | **no cubierto** | Formulario de paso del editor de flujos; FUN. |
| `client_app/app/ui/components/step_forms/report_generate_form.py` | **cubierto** | `GenericReportWizard.tsx` + `contracts/inputs.py`. |
| `client_app/app/ui/components/step_panels/__init__.py` | **no cubierto** | Paquete de paneles de paso; FUN. |
| `client_app/app/ui/components/step_panels/copilot_panel.py` | **cubierto** | `CopilotPanel.tsx` + `useCopilotAction.ts`. |
| `client_app/app/ui/components/step_panels/settings_panel.py` | **no cubierto** | Panel de configuración de paso del editor de flujos; FUN. |
| `client_app/app/ui/components/step_panels/variables_panel.py` | **no cubierto** | Panel de configuración de paso del editor de flujos; FUN. |
| `client_app/app/ui/components/unified_resource_card.py` | **no aplica** | Tarjeta de recurso unificada de NiceGUI. |
| `client_app/app/ui/components/universal_selector.py` | **no aplica** | Selector genérico de NiceGUI. |
| `client_app/app/ui/components/variable_editor.py` | **no cubierto** | Editor de variables del flujo; FUN. |
| `client_app/app/ui/components/variable_selector.py` | **no cubierto** | Selector visual de variables del flujo; FUN. |
| `client_app/app/ui/components/wizards/extraction_wizard.py` | **parcial** | Duplicado del anterior; mismo estado. |
| `client_app/app/ui/components/wizards/script_wizard.py` | **cubierto** | Duplicado del anterior en el legacy; mismo equivalente. |
| `client_app/app/ui/connections_page.py` | **no cubierto** | Centro de acceso a tipos de átomos; FUN. |
| `client_app/app/ui/custom_script_page.py` | **cubierto** | `pages/ScriptProposalWizardPage.tsx` + `routers/redaccion/scripts_router.py`. |
| `client_app/app/ui/dashboard_page.py` | **no cubierto** | 1.006 líneas de panel del legacy; el panel de React no tiene equivalente de esto. |
| `client_app/app/ui/dashboard_translations.json` | **no cubierto** | Cadenas del panel del legacy. |
| `client_app/app/ui/docs_page.py` | **no cubierto** | Documentación embebida en la aplicación; hoy la documentación vive en `docs/`. |
| `client_app/app/ui/email_scan_page.py` | **no cubierto** | 1.062 líneas de recolección de correos; sin equivalente. |
| `client_app/app/ui/email_watcher_page.py` | **no cubierto** | Configuración del vigilante de correo; sin interfaz en el frontend. |
| `client_app/app/ui/execution_container.py` | **parcial** | `services/workspace_run_service.py` ejecuta un informe; la página universal de ejecución de scripts y átomos, no. |
| `client_app/app/ui/extraction_page.py` | **parcial** | El motor está en `graph/nodes/deterministic_extraction.py`, `pipelines/pdf_*` y `automation/extraction_strategies.py`; la **interfaz de los tres modos** (2.370 líneas) no tiene equivalente. |
| `client_app/app/ui/extraction_page_refactored.py` | **parcial** | Segunda versión de la anterior en el legacy; mismo estado. |
| `client_app/app/ui/extraction_translations.json` | **parcial** | 16 KB de cadenas; las del motor están en `redaccion.json`, las de la interfaz de tres modos no. |
| `client_app/app/ui/factory_page.py` | **no cubierto** | La fábrica de automatismos; FUN. |
| `client_app/app/ui/flows_page.py` | **no cubierto** | Editor de flujos (950 líneas). El bloque FUN lo planifica; hoy no hay nada. |
| `client_app/app/ui/flows_translations.json` | **no cubierto** | Cadenas del editor de flujos. |
| `client_app/app/ui/focus_manager.py` | **no aplica** | Foco entre elementos de NiceGUI; en React lo gestiona el DOM. |
| `client_app/app/ui/folder_scan_page.py` | **no cubierto** | Escaneo de carpeta como acción; sin equivalente. |
| `client_app/app/ui/folder_watcher_page.py` | **no cubierto** | Configuración del vigilante de carpetas. **El agente sí existe** (`app/modules/watchers/`), su interfaz pertenece al frontend y no está. |
| `client_app/app/ui/graphics_translations.json` | **cubierto** | i18next, en `locales/*/redaccion.json`. |
| `client_app/app/ui/import_export_page.py` | **no cubierto** | Paquetes de automatismos; FUN plantea el doble origen y aún no existe. |
| `client_app/app/ui/layout_state.py` | **no aplica** | Estado de la disposición de NiceGUI. |
| `client_app/app/ui/llm_process_page.py` | **parcial** | `services/llm_spec_service.py` y `graph/nodes/ai_assist_draft.py` cubren el uso del modelo por bloque; la acción «procesador LLM» configurable, no. |
| `client_app/app/ui/llm_process_translations.json` | **parcial** | Cadenas de la página anterior. |
| `client_app/app/ui/logs_page.py` | **parcial** | `hub_workspace_audit_events` y la observabilidad guardan el rastro; **no hay pantalla** que lo muestre. |
| `client_app/app/ui/main_layout.py` | **no aplica** | Armazón de NiceGUI. En React lo dan `App.tsx` y los *layouts* de cada módulo. |
| `client_app/app/ui/navegacion_translations.json` | **cubierto** | La navegación del panel está en `locales/*/admin.json` (clave `nav`). |
| `client_app/app/ui/pdf_tools_atom_page.py` | **no cubierto** | Herramientas PDF (unir, partir, rotar) como acción; no hay equivalente. |
| `client_app/app/ui/pill_logic.py` | **no aplica** | Lógica de las «pastillas» visuales de NiceGUI. |
| `client_app/app/ui/playwright_wizard.py` | **no cubierto** | Asistente de grabación con Playwright; sin equivalente. |
| `client_app/app/ui/report_designer_page.py` | **cubierto** | `frontend/src/redaccion/pages/ReportTemplateBuilderPage.tsx` + `contracts/template.py` (plantillas con versión inmutable). |
| `client_app/app/ui/report_wizard_page.py` | **cubierto** | `frontend/src/redaccion/pages/GenericReportWizard.tsx` + `profiles/generic_report.py`. |
| `client_app/app/ui/rpa_page.py` | **no cubierto** | 816 líneas de la interfaz de RPA. **El ejecutor se queda** (`app/core/rpa_executor.py`); su interfaz pertenece al frontend. |
| `client_app/app/ui/rpa_translations.json` | **no cubierto** | Cadenas de la interfaz de RPA. |
| `client_app/app/ui/scheduler_page.py` | **no cubierto** | Programación de ejecuciones; el APScheduler del servidor programa rastreos, no flujos del cliente. |
| `client_app/app/ui/script_library_page.py` | **cubierto** | `pages/AdminScriptReviewQueuePage.tsx` + tabla `hub_script_proposals`. |
| `client_app/app/ui/smtp_page.py` | **no cubierto** | Configuración SMTP; sin equivalente. |
| `client_app/app/ui/sql_insert_page.py` | **no cubierto** | Inserción SQL como acción; FUN. |
| `client_app/app/ui/sql_query_page.py` | **no cubierto** | Consulta SQL como acción; FUN. |
| `client_app/app/ui/test_form_page.py` | **no aplica** | Página de pruebas de 31 líneas; andamiaje de desarrollo. |
| `client_app/app/ui/triggers_page.py` | **no cubierto** | Disparadores; sin equivalente. |
| `client_app/app/ui/ui_translations.json` | **parcial** | **60 KB**, el mayor del legacy: mezcla cadenas de todo. Las de informes, scripts y anonimización están en i18next; las del editor de flujos y los vigilantes, no. |
| `client_app/app/ui/ui_utils.py` | **no aplica** | 16 líneas de utilidades de NiceGUI. |
| `client_app/app/ui/web_watcher_page.py` | **no cubierto** | Configuración del vigilante web; sin interfaz en el frontend. |

---

## 4. Lo que NIC.2 midió, y por qué la retirada no se puede hacer por cobertura

**NIC.2 no movió nada.** Iba a mover los 67 ficheros etiquetados «cubierto» y «no aplica», y la
medición previa dijo que no se podía: **48 de los 67 tenían quien los importara**, y los
importadores no eran código muerto.

| Quién importa lo que iba a moverse | Ficheros |
|---|---|
| Nadie, o sólo tests del propio legacy | 32 |
| El agente de ejecución | 5 |
| Código de `client_app/` que se queda | 30 |

El legacy es **una aplicación entrelazada**: las páginas «no cubierto» que se quedan usan
servicios «cubierto», y cinco de ellos los usa el propio agente.

### Tres hallazgos, y el tercero es el que decidió el bloque

**1. Dos etiquetas eran peligrosas.** «No aplica» significa *borrar*, y dos ficheros lo tenían con
código vivo detrás: `event_bus_service.py` lo importan los vigilantes —**el agente**— y
`layout_manager.py` lo importa `app/core/state.py`. Borrarlos habría roto lo único que
`client_app/` debía conservar. La etiqueta salió de leer el propósito del fichero, y **quién lo
importa no se deduce del propósito**.

**2. El bloqueo es transitivo.** La primera pasada calculó «quién importa X» excluyendo a los
propios candidatos, que vale si los 67 se mueven juntos; con 23 bloqueados, un candidato bloqueado
que importa a otro lo retiene igual. Hubo que calcular el cierre **a punto fijo**: de 41 movibles
a 32.

**3. `client_app/` ya no arranca, y no por NIC.2.** Hay **28 imports activos hacia diez ficheros
que bloques anteriores llevaron a la cuarentena** sin reapuntar a quien los importaba. Y no son
periféricos: **`workflow_engine.py`, el motor por el que ejecutan los dos vigilantes, importa en
sus líneas 1478 y 1604 dos módulos que no existen** en `client_app/`
(`modules/factory/graphics_factory.py` y `modules/privacy/anonymizer.py`).

---

## 5. La decisión: retirada completa, con la referencia fuera del repositorio

El hallazgo 3 cambia la pregunta. No se trataba de conservar un agente que funciona mientras se
migra lo demás: **el agente no arranca hoy**, y no hay nada en producción que dependa de
`client_app/` —no aparece en `docker-compose`, ni en el `Dockerfile`, ni en CI—.

**Decisión del usuario (2026-09-04): se retiran `client_app/` y `_legacy_nicegui/` completos.** El
razonamiento es que el repositorio se va a abrir, y 500 ficheros de una aplicación que no compila
no se pueden distinguir de código vivo por quien llegue de fuera.

La referencia se conserva en **tres** sitios, y ninguno dentro del repositorio abierto:

1. **El historial de git de este repositorio.** Borrar del árbol de trabajo no borra del
   historial: los ficheros siguen ahí con su contexto y sus mensajes de commit. Es la mejor de las
   tres, porque viaja con el repositorio y no se puede perder.
2. `C:\Users\fabra\Documents\AutomatIA` — la aplicación NiceGUI completa y verificada.
3. El *bundle* de GenGov.

**Y este inventario es el mapa.** Su tabla de la §3 dice, fichero a fichero, qué tiene equivalente
y dónde, y qué no lo tiene: es lo que hay que leer el día que se desarrolle el agente local, antes
de ir a buscar el código a ninguna de las tres referencias.

### La quinta etiqueta que se consideró y se descartó

La medición sugería añadir una etiqueta —«cubierto en el servidor, pero el agente necesita el
suyo»— para los servicios que el agente duplica legítimamente: el agente corre en la máquina del
cliente y que el servidor tenga un sandbox no le sirve.

**Se descartó**, y la razón es el hallazgo 3: la etiqueta habría servido para justificar conservar
código que no compila. Con la retirada completa, lo que queda escrito es que **el agente local es
trabajo pendiente sin código en el repositorio**, que es la verdad.

---

## 6. Lo que la retirada arrastró, y lo que dejó para NIC.4

`git rm -r client_app _legacy_nicegui` llevó el repositorio de **2105 a 1531 ficheros
versionados**: 574 menos. Pero un directorio no se va solo — se va con lo que apuntaba a él, y eso
hubo que medirlo.

### 6.1 Ocho ficheros más, porque el paso de colección de CI se puso rojo

CI tenía un paso, `Collect root tests`, que hacía `pytest tests --collect-only` sobre el árbol de
la raíz **sin ejecutarlo** (NIC.4 lo reapuntó; ver §7.3). Existe porque ese árbol acumuló durante meses doce rojos y dos errores de
colección sin que ningún check se enterara, y colectar es barato y caza exactamente lo que la
retirada provoca: un import a un módulo que ya no existe. Se puso rojo al primer intento:

```
ERROR tests/unit/test_report_analyzer_service.py
E   ModuleNotFoundError: No module named 'client_app'
```

Retirados (Caso B — su sujeto ya no existe):

| Fichero | Qué era |
|---|---|
| `tests/unit/test_local_models.py` | los modelos SQLModel de la BD local del cliente |
| `tests/unit/test_multiasiento_licenses.py` | licencias multiasiento contra la huella de máquina |
| `tests/unit/test_report_analyzer_service.py` | el analizador de informes del NiceGUI |
| `tests/manual/debug_etl_service.py` | guion de depuración del ETL a mano |
| `scripts/refactor_imports.py` | reescritura puntual de imports de `client_app` |
| `scripts/validate_dev_env.py` | validaba el entorno del NiceGUI, incluido su `translations.json` |
| `scripts/verify_integration.py` | comprobaba que `client_app`, `server` y `shared` se importaban |

Y en `tests/conftest.py` se fueron las fixtures `test_client_db` y `db_session`, que construían la
BD SQLite del cliente a partir de `client_app.app.database.db.client_engine`.

### 6.2 Cuatro guardarraíles que afirmaban la cuarentena

Este es el hallazgo con enseñanza. Cuatro ficheros de `server/tests/infra/` la daban por presente,
y **no fallan igual**:

| Guardarraíl | Qué le pasó |
|---|---|
| `test_nic1_el_inventario_esta_completo.py` | **retirado entero** |
| `test_la_documentacion_de_automatia_esta_en_cuarentena.py` | 1 test invertido de 17 parámetros, 3 sobreviven; renombrado a `..._se_retiro.py` |
| `test_el_lanzador_de_nicegui_esta_en_cuarentena.py` | 1 test invertido, 4 sobreviven; renombrado a `..._se_retiro.py` |
| `test_nicegui_retirado.py` | 1 test invertido, 1 retirado por vacío, 4 sobreviven |

**Los que se ponen rojos son los inofensivos.** «`_legacy_nicegui/main.py` existe» y «los
diecisiete documentos siguen en la cuarentena» pasaron a falsos y lo dijeron, así que se
invirtieron: ahora vigilan que la cuarentena **no vuelva**.

**El peligroso es el que se pone verde.** El de NIC.1 cruzaba `git ls-files client_app/app/ui` y
`app/services` contra la tabla de la §3: con el directorio retirado, `git ls-files` devuelve la
lista vacía y sus cuatro tests de cruce —«toda ruta tiene fila», «toda fila tiene etiqueta»,
«ninguna justificación vacía»— iteran sobre nada y **pasan sin comprobar nada**. Igual
`test_should_have_no_legacy_ui_files_in_client_app`, cuya primera línea era un `return` sobre un
directorio inexistente. Un guardarraíl verde se lee como «comprobado», así que se retiran los dos,
y un test de NIC.3 impide que el de NIC.1 vuelva.

De lo que hacía NIC.1 sobrevive lo que no depende de que los ficheros existan: que el inventario
conserve su tabla, que los diecisiete documentos no **vuelvan** a `docs/`, y que ningún fichero
activo los enlace. Ese era el daño real: quien abría uno de aquellos documentos técnicos se
llevaba la arquitectura de otro producto, con la de este al lado.

(Y una anécdota que vale como comprobación, porque pasó **dos veces seguidas**: la primera versión
de este párrafo nombraba uno de los diecisiete y el guardarraíl superviviente se puso rojo; la
segunda, al explicar por qué, nombró otro. Busca los nombres de fichero a secas y no rutas
completas —un enlace relativo desde `docs/` se escribe sin prefijo de directorio—, así que **no
distingue el enlace de la mención**. Se reformuló el párrafo las dos veces en vez de afinar el
test: relajar un guardarraíl para que pase tu propia prosa es la forma más barata de quedarse sin
guardarraíl.)

### 6.3 Lo que NIC.3 no toca, y NIC.4 tiene que decidir

**Cinco ficheros de `tests/unit/` pedían `db_session`** —licencias, partners, escalado de scripts,
semillas— y esa fixture ya no existe. No se les inventó un sustituto: **ya estaban en rojo antes de
esta retirada**, porque importan `server.app.services.ai_brain`, que tampoco existe. Son la punta
del mundo SQLModel *Brain/partner/licencia* que vino de AutomatIA y que convive con los modelos
vivos sin que nada los use.

Es exactamente lo que NIC.4 mide: el entorno legacy de la raíz —`nicegui==3.4.1` en el
`pyproject.toml`, las 35 filas de `tests/`, `translations.json` con su `i18n.py`, `arranque.bat`—.
Aquí se retira lo que la retirada rompe **en colección**, que es lo que CI comprueba, y no más: un
prompt que se lleva por delante el alcance del siguiente deja de ser reversible, que es lo único
que hace tolerable un bloque largo.

---

## 7. NIC.4 — el entorno que sólo existía para sostener el NiceGUI

El prompt nombraba cuatro piezas y pedía **medir antes de tocar**. Dos no eran lo que suponía, y
por eso la regla vale más que la lista.

| Pieza | Qué dijo la medición |
|---|---|
| `pyproject.toml` de la raíz + `uv.lock` (1,6 MB) | **Huérfano.** Retirado |
| `tests/` de la raíz (32 ficheros) | **No era un bloque.** 16 migrados, 16 retirados |
| `translations.json` (158 KB) + `core/i18n.py` | **Huérfano.** Retirado |
| `arranque.bat` | **Ya estaba limpio.** No se toca |

### 7.1 El `pyproject.toml` de la raíz no lo usaba ningún workflow

Se llamaba `automatia` y se describía como «aplicación NiceGUI legada». Declaraba **sesenta
dependencias** empezando por `nicegui==3.4.1`. Y no lo instalaba nada de lo que decide si el
proyecto funciona: CI y `deploy.yml` corren `uv sync` con `working-directory: server`, el
`Dockerfile` copia `server/pyproject.toml`, y hasta el paso que colectaba la suite de la raíz
invocaba `uv run --project server`. Lo único que aportaba era su `[tool.pytest.ini_options]` — con
un `--cov=app` que apuntaba a un directorio `app/` que en la raíz no existe— y hacer que `uv sync`
sin `--project` resolviera algo.

Los proyectos uv son ahora cuatro: `server/`, `shared/`, `mcp_server/` y `services/script_sandbox/`.
El `.venv` de la raíz sobrevive en el disco sin estar versionado; se puede borrar.

### 7.2 El árbol de tests de la raíz: la pregunta que decidió el reparto

Medido por directorio, antes de mover nada:

| Directorio | Pasan | Rojos |
|---|---|---|
| `tests/redaccion` (12 ficheros) | 117 | 12 |
| `tests/public_graphs` (3) | 9 | 13 |
| `tests/modules` (1) | 5 | 0 |
| `tests/unit` (6) | 0 | 31 errores |
| `tests/security`, `tests/integration` | — | vacíos, sólo `__init__.py` |

Retirarlos juntos habría perdido 131 aserciones que pasan; migrarlos juntos habría traído seis
ficheros que no compilan. **La pregunta que lo decidió fue si duplicaban lo que CI ya ejecuta**, y
se contestó con AST sobre los nombres de test: **cero de los 128 de `tests/redaccion` y cero de los
22 de `tests/public_graphs` coinciden con ninguno de los 3.630 de `server/tests/`**. No eran
duplicados. Era cobertura que CI nunca ejecutó, sólo colectó.

Los 16 vivos se **funden** con las carpetas que ya existían —`server/tests/modules/redaccion/`,
`server/tests/public_graphs/`, `server/tests/modules/agents_hub/unit/`— y no en una segunda
`redaccion/` al lado: dos directorios con el mismo nombre garantizan que la mitad de las búsquedas
mire en el que no toca. Se comprobó antes que no hubiera colisión de nombre de fichero.

`tests/unit/` se retira: es el mundo SQLModel *Brain/partner/licencia* que vino de AutomatIA, y sus
31 errores son `server.app.services.ai_brain`, que no existe.

### 7.3 Los 25 rojos, y la regla que evitó decidir caso a caso

Veinticinco tests de código vivo llevaban en rojo **sin que ningún check lo dijera**. Repararlos de
uno en uno invita a escribir lo que haga falta para que pasen, así que se aplicó una regla:

* **Rojo por un símbolo renombrado o una guarda añadida → se repara.** Conserva la intención del
  test. Fueron `HubClient`→`HubOrganizacion`, `client_id`→`organizacion_id` y el `owner_kind`
  «organization»→«organizacion» de ROL.1.
* **Rojo por afirmar un valor que un bloque posterior cambió a propósito → se escribe el de hoy,
  con quién lo eligió y por qué.** Nunca el número a secas: un default de columna que cambia sin
  que nadie lo decida es una regresión silenciosa, y esto es lo único que la vigila.
  `quality_threshold` 0,65 (HIB.R), `min_retrieval_score` 0,0 (RAG.5), `reranker_enabled` `False`
  (RAG.6, confirmado midiendo en HIB.A).
* **Sujeto desaparecido sin sucesor → se retira la aserción.** `FieldDefinition` era el
  especificador de campos de la extracción asistida del NiceGUI; el `OutputField` de hoy tiene otra
  forma porque describe otra cosa.

**Cuatro de los rojos eran el doble del propio test, no el producto**, y son el aviso que conviene
recordar: dos endpoints devolvían 409 porque `MagicMock().archived_at` no es `None` y el router
había ganado la comprobación de plantilla retirada; uno devolvía **500** —justo lo que ese test
existe para prohibir— porque parcheaba `model_validate` para devolver `None` y SEG.5 añadió después
`bloques_sin_seccion(spec.sections, ...)`; y el `AsyncMock` pelado del ConfigResolver hacía que
`scalars()` devolviera una corrutina. Es el modo de fallo de los mocks sin `spec=`.

**Y uno pasaba en verde por la razón equivocada.**
`test_only_admin_can_create_global_template_contract` esperaba un `ValidationError` y lo obtenía
por el literal `organization` inválido, no por la regla de `is_global`: habría pasado igual si la
regla no existiera. Ahora comprueba que el rechazo sea el suyo.

### 7.4 El paso de CI que se quedó sin sujeto, y el agujero que habría movido

Borrar `Collect root tests` sin más era la opción cómoda y la equivocada: el paso existía porque CI
corre con `working-directory: server` y no ve nada más, y **`shared/tests` y `mcp_server/tests`
seguían igual de fuera**. Ahora ese paso los **ejecuta** —14 segundos entre los dos—, y la razón de
ejecutar en vez de colectar la dio la propia medición: los dos rojos que `shared/tests` escondía
importaban `FieldDefinition` **dentro** de la función, así que un `--collect-only` los habría
dejado pasar. Quedan en 142 y 89 tests verdes.
