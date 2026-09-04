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
| `client_app/app/services/event_bus_service.py` | **no aplica** | Bus de eventos en proceso de NiceGUI; el servidor usa HTTP y WebSocket. |
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
| `client_app/app/services/layout_manager.py` | **no aplica** | Disposición de la interfaz NiceGUI vista desde los servicios; no es el mismo fichero que el de `app/ui`. |
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
