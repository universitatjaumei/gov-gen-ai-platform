# Bloque 9R — Redacción Contract-First

> Documento de decisiones de arquitectura. Autosuficiente: cualquier dev nuevo puede
> entender qué hace el bloque 9R sin leer el plan completo.

---

## Propósito

El bloque 9R implementa el sistema de **redacción asistida por IA** de Gov Gen AI Platform.
Permite generar informes estructurados combinando:

- **extracción determinista** de datos desde Excel/PDF/tablas,
- **asistencia LLM** para secciones narrativas,
- **revisión humana explícita (HITL)** bloque a bloque antes de ensamblar el documento final,
- **trazabilidad completa** mediante `DraftingRunManifest`.

El módulo reemplaza el antiguo `config_hibrida JSON` y los prompts 9.11a–9.11d (superseded).

---

## Decisiones de diseño

### 1. No grafo monolítico
El `DraftingCoreGraph` es el grafo común para todos los tipos de informe. La variación entre
tipos se resuelve mediante `ReportProfile`, no mediante condicionales `if/else` dentro del core.
Cada perfil selecciona su propio conjunto de pipelines de extracción y políticas de revisión.

### 2. Contratos versionados
El antiguo `config_hibrida JSON` desaparece. Se sustituye por `ReportTemplateContract` con
`version_id`, esquema validable (Pydantic) y serialización estable para OpenAPI. Los workspaces
quedan anclados a una `template_version_id` concreta; la migración es una acción explícita del
usuario, nunca automática.

### 3. UI por contrato
El frontend no tiene pantallas hardcoded por tipo de informe. Renderiza `ReportUIContract`
recibido del backend, usando `react-hook-form` + `zodResolver` + tipos generados por Orval.
Está prohibido crear interfaces TypeScript manuales para DTOs de redacción.

### 4. LLM propone, humano aprueba
El asistente LLM genera un `ReportTemplateDraft` → pasa por validador estructural → se muestra
como vista previa editable → requiere aprobación HITL → se persiste como plantilla o workspace
ad hoc. El LLM no puede crear plantillas persistentes sin aprobación humana.

### 5. Extracción determinista primero
Excel y PDF se parsean con código (`pandas`, `pdfplumber`, `camelot`), nunca con LLM como
mecanismo principal. Los scripts generados por IA son una extensión controlada con HITL + AST +
auditoría (refactor de 9.11b). La IA interviene solo cuando el código estructurado no es
suficiente (secciones narrativas, resúmenes, reescrituras).

### 6. Estados de bloque explícitos
Cada bloque tiene un estado en la máquina de estados:

```
draft → missing_input
      → extracted
      → ai_generated → needs_review → approved → locked
                                    → rejected → (retry)
      → failed (con failure_kind + retry_policy)
```

Un bloque IA sin estado `approved` no entra en el documento final. Un bloque requerido sin
datos bloquea el ensamblado. Los bloques `failed` propagan el fallo a sus dependientes según
la topología del grafo.

### 7. RunManifest obligatorio
Ninguna exportación procede sin un `DraftingRunManifest` con todos los campos requeridos:
`workspace_id`, `template_version_id`, `report_profile`, `uploaded_documents`,
`input_validation`, `extracted_blocks`, `ai_blocks`, `model_used`, `prompt_versions`,
`citations`, `warnings`, `user_approvals`, `final_document_hash`.
El manifest se emite incluso si la ejecución falla (para auditoría).

### 8. Edge/Cloud
Los módulos 9R son **edge**: procesan documentos y expedientes del cliente. Los routers
se etiquetan `Deploy: edge` y no importan módulos cloud directamente. La configuración
se lee vía `ConfigProvider`. Ver `CLAUDE.md` §Frontera Edge-Cloud.

---

## Diagrama del DraftingCoreGraph

```
LoadTemplateNode
  │  Carga ReportTemplateContract (version anclada) + WorkspaceState
  ▼
ValidateInputContractNode
  │  Valida que los inputs del workspace satisfacen InputContract de la plantilla
  ▼
FileNormalizationNode
  │  Normaliza documentos subidos → formatos internos (Markdown, DataFrame, bytes)
  ▼
DeterministicExtractionNode
  │  Ramifica por tipo de bloque:
  │    Excel          → ExcelExtractionPipeline
  │    PDFText        → PDFTextExtractionPipeline
  │    PDFTable       → PDFTableExtractionPipeline
  │    Manual         → ManualInputPipeline
  │    AdminScript    → AdminScriptExtractionPipeline
  ▼
DataQualityCheckNode
  │  Verifica completitud, rango, formato de cada campo extraído
  │  → marca bloques con estado missing_input / extracted
  ▼
MissingDataQuestionNode          [HITL — solicita inputs faltantes al usuario]
  │  Genera preguntas para bloques en missing_input
  │  Espera respuesta antes de continuar
  ▼
AIAssistDraftNode
  │  LLM con contexto de datos validados como contexto
  │  → genera texto para bloques AI_ASSISTED_TEXT / AI_SUMMARY / AI_REWRITE
  │  → estado: ai_generated
  ▼
CitationAndTraceabilityNode
  │  Anota fuente (documento, página, celda) de cada fragmento
  │  → adjunta CitationBlock a cada bloque IA
  ▼
UserReviewGateNode               [HITL — aprueba / rechaza / regenera por bloque]
  │  Bloquea el ensamblado hasta que todos los bloques IA estén approved
  │  Bloques rechazados vuelven a AIAssistDraftNode
  ▼
ApplyUserEditsNode
  │  Incorpora ediciones manuales del usuario sobre bloques aprobados
  ▼
FinalAssemblerNode
  │  Ensambla secciones en orden; solo incluye bloques con estado approved/locked
  │  → genera PreviewPayload compartido con ExportService (1C.4)
  ▼
AuditLogNode
     Emite DraftingRunManifest con todos los campos requeridos
     Persiste en hub_run_manifests
```

---

## Mapa de ejecución — bloque 9R

```
9R.0   (DOC)        Decisiones de arquitectura + nota en el plan          ← ESTE DOC

── Contratos ──
9R.1.1 (RED/GREEN)  ReportTemplateContract + ReportTemplateVersion (Pydantic + OpenAPI)
9R.1.2 (RED/GREEN)  InputContract + BlockContract + ReportUIContract
9R.1.3 (RED/GREEN)  WorkspaceState + BlockState + ReportTemplateDraft (runtime)
9R.1.4 (RED/GREEN)  Migración Alembic: hub_report_templates / hub_workspaces
                                       hub_workspace_blocks / hub_run_manifests

── Perfiles ──
9R.2.1 (RED/GREEN)  ReportProfile registry + GENERIC_REPORT como perfil obligatorio
9R.2.2 (RED/GREEN)  Estructura inicial GENERIC_REPORT (secciones, bloques, inputs)

── Bloques ──
9R.3.1 (RED/GREEN)  Tipos de bloque (STATIC_TEXT, USER_INPUT, DETERMINISTIC_DATA,
                                     TABLE, CHART, AI_ASSISTED_TEXT, AI_SUMMARY,
                                     AI_REWRITE, CITATION_BLOCK, REVIEW_GATE)
9R.3.2 (RED/GREEN)  BlockState machine + reglas de transición + invariantes
9R.3.3 (RED/GREEN)  BlockReference + projection + orden topológico + detección de ciclos

── LLMSpec ──
9R.4.1 (RED/GREEN)  LLMSpecService: lenguaje natural → ReportTemplateDraft
9R.4.2 (RED/GREEN)  Validador estructural + rechazo de drafts con tipos no permitidos
9R.4.3 (RED/GREEN)  Endpoints preview/approve + HITL (admin: plantilla; user: workspace ad hoc)
9R.4.4 (RED/GREEN)  Versionado de plantillas: política de anclaje + endpoints de migración

── Extracción ──
9R.5.1 (RED/GREEN)  Protocolo ExtractionPipeline + contratos (Input/Result/Provenance/Warning)
9R.5.2 (RED/GREEN)  ExcelExtractionPipeline + PDFTextExtractionPipeline
9R.5.3 (RED/GREEN)  PDFTableExtractionPipeline + ManualInputPipeline
9R.5.4 (RED/GREEN)  ExtractionPipelineFactory + AdminScriptExtractionPipeline

── CoreGraph ──
9R.6.1 (RED/GREEN)  LoadTemplate / ValidateInputContract / FileNormalization
9R.6.2 (RED/GREEN)  DeterministicExtraction / DataQualityCheck / MissingDataQuestion
9R.6.3 (RED/GREEN)  AIAssistDraft / CitationAndTraceability
9R.6.4 (RED/GREEN)  UserReviewGate / ApplyUserEdits / FinalAssembler
9R.6.5 (RED/GREEN)  AuditLog + DraftingRunManifest + instrumentación Langfuse
9R.6.6 (RED/GREEN)  Fallback paths + BlockState=failed + política de retry + propagación

── UI (Frontend) ──
9R.7.1 (RED/GREEN)  ReportUIContractRenderer + DynamicUploadSlots + DynamicFieldRenderer
9R.7.2 (RED/GREEN)  BlockEditor + AIBlockReviewPanel + DataQualityPanel + WorkspaceStatusBar
9R.7.3 (RED/GREEN)  ReportTemplateBuilderPage (admin) + GenericReportWizard (user)
9R.7.4 (RED/GREEN)  LLMDraftPreviewPage + flujo de aprobación

── HITL ──
9R.8.1 (RED/GREEN)  HITL endpoints + servicios de transición de bloques
9R.8.2 (RED/GREEN)  Tests E2E de edición/rechazo/regeneración por bloque

── RunManifest ──
9R.9.1 (RED/GREEN)  DraftingRunManifest modelo Pydantic + repo + endpoint
9R.9.2 (RED/GREEN)  Integración con ExportService (1C.4) + final_document_hash

── Vertical Slice ──
9R.10.1 (RED)       Tests de aceptación E2E del slice completo
9R.10.2 (GREEN)     Wire-up integral del slice
```

---

## Reglas duras

1. **No existe `config_hibrida JSON` libre.** Cualquier dato de configuración va en un
   `ReportTemplateContract` versionado.
2. **Los routers HTTP devuelven modelos Pydantic específicos.** Nunca devolver modelos ORM
   directamente.
3. **El frontend usa exclusivamente tipos generados por Orval.** Está prohibido crear
   interfaces TypeScript manuales para DTOs de redacción.
4. **El LLM no puede crear plantillas persistentes sin aprobación HITL.** Solo genera
   `ReportTemplateDraft`.
5. **Ningún bloque IA entra al documento final sin estado `approved`.** El `UserReviewGateNode`
   bloquea el ensamblado.
6. **Toda ejecución del agente emite `DraftingRunManifest`**, incluso si falla. La exportación
   a DOCX/ODT (1C.4) requiere manifest válido.
7. **Módulos 9R son edge.** Routers etiquetados `Deploy: edge`; no importan módulos cloud.
8. **TDD obligatorio.** RED antes que GREEN; ningún PR del bloque se acepta sin tests del
   nuevo contrato o comportamiento.

---

## Versionado de plantillas y migración de workspaces

### Política de anclaje (no negociable)

Un `HubWorkspace` queda anclado a su `template_version_id` para siempre:

- **Publicar vN+1 NO migra automáticamente** los workspaces existentes.
- El propietario del workspace recibe un aviso ("Plantilla actualizada — versión vN+1 disponible") en `WorkspaceStatusBar` (9R.7.2) consultando `GET /api/v1/hub/redaccion/workspaces/{id}/template-update-notice`.
- La migración es un **acto explícito**: `POST /api/v1/hub/redaccion/workspaces/{id}/migrate`.

### Qué hace la migración

1. Detecta `breaking_changes` entre la versión actual y la versión objetivo (nuevos `required_slots` no presentes en el workspace actual).
2. Si hay `breaking_changes` → `409 Conflict` con `compatibility_errors: [{slot_id, reason}]`. El usuario debe rellenar los nuevos slots manualmente tras crear el workspace.
3. Si es compatible → crea un workspace nuevo:
   - `template_version_id = target_version_id`
   - `inputs_json` copiado verbatim del workspace original
   - `parent_workspace_id = original_workspace.id` (trazabilidad de auditoría)
   - **No se copian** outputs de bloques ni registros de aprobación (el nuevo workspace empieza desde cero).
4. Archiva el workspace original: `status = "archived"`, `archived_reason = "migrated_to_{new_id}"`.
5. El workspace original sigue siendo accesible para auditoría; su `run_manifest_id` no se toca.

### Columnas añadidas a `hub_workspaces` (migración n5c6d7e8f9a0)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `parent_workspace_id` | UUID FK nullable | Apunta al workspace original tras una migración |
| `archived_reason` | String(500) nullable | Razón del archivado (ej. `"migrated_to_{new_id}"`) |

El campo `status` ya admite `"archived"` a nivel de app (tipo `String(30)`, sin enum DB).

### Servicio

```
server/app/modules/redaccion/services/template_migration_service.py

TemplateMigrationService.detect_new_version(workspace_id) -> NewVersionNotice | None
TemplateMigrationService.migrate_workspace(workspace_id, target_version_id, user_id) -> HubWorkspace

NewVersionNotice:
  current_version_id: UUID
  latest_version_id: UUID
  changes_summary: str
  breaking_changes: list[BreakingChange]  # [] si no hay cambios disruptivos

CompatibilityConflictError  → capturada por el router → 409
WorkspaceOwnershipError     → capturada por el router → 403
```

### Endpoints (Deploy: edge)

```
GET  /api/v1/hub/redaccion/workspaces/{id}/template-update-notice
     → 200 NewVersionNotice | 204 si ya alineado

POST /api/v1/hub/redaccion/workspaces/{id}/migrate
     Body: { target_version_id: UUID }
     → 201 { new_workspace_id: UUID }
     → 409 { compatibility_errors: [{slot_id, reason}] }
     → 403 si el llamante no es el owner
```

---

## Glosario

| Término | Definición |
|---------|------------|
| **ReportProfile** | Identificador del tipo de informe (`GENERIC_REPORT`, futuro `ACTA_REUNION`, etc.). Determina qué secciones, bloques y pipelines de extracción están disponibles. |
| **ReportTemplateContract** | Contrato serializable (Pydantic + OpenAPI) que describe la estructura de un tipo de informe: secciones, bloques, inputs requeridos, políticas de IA y exportación. Versionado e inmutable una vez publicado. |
| **BlockContract** | Especificación de un bloque individual dentro de una plantilla: tipo, inputs aceptados, reglas de validación, política de revisión. |
| **ReportUIContract** | Subconjunto del contrato dirigido al frontend. Describe qué componentes renderizar, en qué orden, con qué validaciones. El frontend lo consume via Orval; nunca lo hardcodea. |
| **BlockState** | Estado de un bloque dentro de un workspace activo: `draft → missing_input / extracted → ai_generated → needs_review → approved / rejected → locked`. Estado adicional: `failed` (con `failure_kind`). |
| **DraftingRunManifest** | Registro completo e inmutable de una ejecución del agente de redacción: documentos subidos, resultados de extracción, bloques IA generados, modelo/versiones de prompt usados, citas, advertencias, aprobaciones del usuario, hash del documento final. |
| **ReportTemplateDraft** | Propuesta temporal generada por `LLMSpecService` a partir de lenguaje natural. No es persistente; requiere validación estructural + aprobación HITL antes de convertirse en `ReportTemplateContract`. |
| **ExtractionPipeline** | Protocolo que encapsula la lógica de extracción de datos desde un tipo de fuente (Excel, PDFText, PDFTable, Manual, AdminScript). Devuelve `ExtractionResult` con datos, provenance y warnings. |
| **NewVersionNotice** | DTO devuelto por `TemplateMigrationService.detect_new_version()`. Informa al propietario de que hay una versión más reciente disponible e indica si hay `breaking_changes` en el `InputContract`. |
