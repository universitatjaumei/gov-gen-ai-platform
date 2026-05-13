# Estado del Proyecto — Gov Gen AI Platform

> Actualizado automáticamente al final de cada prompt de desarrollo.
> Fuente de verdad para saber en qué paso está cada plan activo.

---

## Planes activos

### Plan_Contrato_OpenAPI.md — Alineación Backend/Frontend con OpenAPI + Orval

| Bloque | Último completado | Siguiente | Estado |
|--------|-------------------|-----------|--------|
| CF.1 — Exportación OpenAPI | CF.1.2 ✅ | — | ✅ Completo |
| CF.2 — Orval + generación | CF.2.3 ✅ | — | ✅ Completo |
| CF.3 — Compilación TypeScript | CF.3.3 ✅ | — | ✅ Completo |
| CF.4 — Formulario piloto Chatbot | CF.4.4 ✅ | — | ✅ Completo |
| CF.5 — CI | CF.5.2 ✅ | — | ✅ Completo |

**Cursor actual: 9B.6 (RED) — Protocolos de estrategias actualizados para RetrievalPipeline (Plan_TDD_Fase1.md)**

---

### Plan_TDD_Fase1.md — Hub Informativo, Personalización y Redacción (MVP)

| Bloque | Último completado | Siguiente | Estado |
|--------|-------------------|-----------|--------|
| Fase 0 — Infraestructura | — | — | ✅ Eliminada (heredada) |
| Subfase 1.A — Chatbots Públicos (9B) | 9B.14 ✅ | — | ✅ Completo |
| Subfase 1.A → 1.C — Redacción Contract-First (9R) | 9R.6.6 ✅ | 9R.7.1 | ⏳ En curso — 9 prompts restantes |
| Subfase 1.B — Identidad y Despliegue (Fase 10 + Fase Deploy GCP) | — | 10.1 | ⏳ Pendiente — Fase 10 (temas/plantillas) + D.1-D.5 |
| Subfase 1.C — Infraestructura de Diseño y Exportación Avanzada | — | 1C.0 | ⏳ Pendiente — 6 prompts (1C.0, 1C.1, 1C.2, 1C.3, 1C.4, 1C.5) |

**Cursor actual: 9R.7.1 — UI: Renderer base + slots dinámicos**

> Nota: el bloque **9R** (Redacción Contract-First) se incorporó el 2026-05-11 a partir de `Rediseño_informes.md`.
> Sustituye los antiguos prompts 9.11a–9.11d. Es paralelo a 9B y bloquea la subfase 1.C (1C.4 requiere `DraftingRunManifest` de 9R.9).

---

### Plan_TDD_Fase2.md y Plan_TDD_Fase3.md

| Plan | Estado |
|------|--------|
| Fase 2 — Migración NiceGUI + Agente local | ⏳ No iniciada — plan listo para ejecutar |
| Fase 3 — Gestor de Expedientes | ⏳ No iniciada |

**Subfase 2.B — Estado del plan para el extractor PDF (9.12b / 9.13)**

Plan enriquecido el 2026-05-11 con el análisis de `Migración_extracción_pdf.txt`:

| Prompt | Descripción | Estado |
|--------|-------------|--------|
| 9.12b.0 | Auditoría funcional legacy (`legacy_extraction_spec.md`) | ⏳ Pendiente |
| 9.12b | Refactor backend PDF extractor a Docling | ⏳ Pendiente |
| 9.13 | UI React del extractor PDF (Focus Mode + wizard) | ⏳ Pendiente — bloqueado por 9.12b |

Secuencia de implementación: 12 pasos atómicos documentados en **Guía 9C.1** del plan.
Prompts verbatim para el agente: `Migración_extracción_pdf.txt` §5.

> **Prerequisito de Fase 2**: Subfase 1.A completada ✅ (9B.14 verde, 2026-05-11).

---

## Historial reciente

| Fecha | Prompt | Descripción |
|-------|--------|-------------|
| 2026-05-05 | CF.1 completo | Infraestructura contractual: export_openapi.py + openapi.json |
| 2026-05-05 | CF.2 completo | Orval instalado, orval.config.ts, carpeta generated/ |
| 2026-05-05 | CF.3 completo | Compilación TypeScript limpia con tipos generados |
| 2026-05-10 | — | Configuración de permisos Claude Code + regla de estado |
| 2026-05-10 | CF.4.2 | Refactor ChatbotsPage: Orval hooks + zodResolver + mapApiErrorsToFormErrors |
| 2026-05-10 | CF.4.3 | Extraer mapApiErrorsToFormErrors a shared/utils/formErrors.ts + tests + test (e) verde |
| 2026-05-10 | CF.4.4 | Eliminar chatbots.ts: migrar todas las llamadas fetch de 4 páginas a hooks Orval; 96/97 tests verdes |
| 2026-05-11 | CF.5.1 | Añadir job "contract" al CI: exportar OpenAPI → Orval → tsc --noEmit → vitest run |
| 2026-05-11 | CF.5.2 | Prueba de fuego del contrato: name→display_name genera 17 errores TS2339; corregidos 5 errores preexistentes (customInstance firma, _ContractCheck, kind cast, comparación 'vector', variable sin usar) |
| 2026-05-11 | 9R (planificación) | Incorporado el bloque 9R Redacción Contract-First en Plan_TDD_Fase1.md (29 prompts atómicos TDD: contratos, GENERIC_REPORT, bloques, LLMSpecService, ExtractionPipelineFactory, DraftingCoreGraph, UI por contrato, HITL, RunManifest, vertical slice MVP). 9.11a–9.11d marcados superseded. |
| 2026-05-11 | 9B.4 | Contrato de evidencias: EvidenceItem + RetrievalResult + RetrievalPipeline Protocol + GraphDeps. 12 tests verdes en tests/public_graphs/test_retrieval_contract.py. |
| 2026-05-11 | 9B.5 | RetrievalPipelineFactory + 3 pipelines (RagVectorPipeline, MdLongContextPipeline, MdAgentSelectorPipeline stub). 29 tests verdes en tests/public_graphs/. |
| 2026-05-11 | 9B.6 | protocols.py: RetrievalOutput + RetrievalStrategy Protocol + PipelineRetrievalStrategy. 5 tests verdes en test_retrieval_strategy_protocols.py. |
| 2026-05-11 | 9B.7 | MergeStrategy/TemplateStrategy/LanguagePolicy en protocols.py + core/core_graph.py (CoreGraph + CoreGraphState). 3 tests verdes en test_core_graph.py. |
| 2026-05-11 | 9B.8 | profiles/public_kb_rich.py: SingleSourceRetrievalStrategy + PassthroughMergeStrategy + GenericAnswerTemplateStrategy + DefaultLanguagePolicy. 3 tests verdes en test_public_kb_rich.py. |
| 2026-05-11 | 9B.9 | profiles/public_portal_router.py: PortalRouterRetrievalStrategy (selección stub → primer hijo, carga config efectiva, usa retrieval_mode del hijo). 2 tests verdes en test_public_portal_router.py. |
| 2026-05-11 | 9B.10 | 7 tests RED en test_uji_aggregator.py + stub public_portal_aggregator.py. Fallan por comportamiento (stub vacío), no por imports. Contrato: 2 buckets por fuente, merge condicional, secciones template, warning traducción. |
| 2026-05-11 | 9B.11 | UjiDualSourceRetrievalStrategy + UjiMergeStrategy + UjiAnswerTemplateStrategy implementados. 7 tests verdes en test_uji_aggregator.py. |
| 2026-05-11 | 9B.12 | PreferLanguagePolicy + StrictLanguagePolicy + NeutralLanguagePolicy en protocols.py. CoreGraph extiende estado con translation_warning + llama filter_items/should_warn_translation en merge_node. DefaultLanguagePolicy hereda PreferLanguagePolicy. 59 tests verdes (10 nuevos en test_language_policy.py). |
| 2026-05-11 | 9B.13 | GraphFactory en core/graph_factory.py: resuelve config → selecciona perfil en registry → crea CoreGraph. Registro de los 3 perfiles (PUBLIC_KB_RICH, PUBLIC_PORTAL_AGGREGATOR, PUBLIC_PORTAL_ROUTER) con stubs. 62 tests verdes (3 nuevos en test_graph_factory.py). |
| 2026-05-11 | 9B.14 | docs/GRAPH_PROFILES.md (guía CoreGraph, perfiles, retrieval_mode, cómo extender). test_profile_contract.py: 12 tests parametrizados (3 perfiles × compile+non-null + 3 perfiles × 3 modos smoke). test_pipeline_contract_suite.py: 6 tests parametrizados (3 pipelines × 2 contratos). 80 tests verdes en total. Subfase 9B completada. |
| 2026-05-11 | (planificación Fase 2) | Plan_TDD_Fase2.md enriquecido con análisis de migración PDF: nuevo prompt 9.12b.0 (auditoría funcional legacy + spec), Guía 9C.1 (tabla de 12 pasos atómicos con artefactos verificables), riesgos explícitos en 9.12b, firmas de `prompts.py`, `ExtractionPhase` state machine en 9.13, tabla de niveles de automatización, tests de `useExtractionRun` ampliados de 3 a 8 + 8 tests nuevos de componentes wizard. |
| 2026-05-11 | (config) | CLAUDE.md: regla de retirada legacy actualizada a dos pasos — Caso A (NiceGUI en migración activa) → mover a `_legacy_nicegui/` al cerrar el prompt GREEN, borrar al cerrar el prompt de verificación de subfase; Caso B (código huérfano) → borrar directamente. |
| 2026-05-12 | (planificación 1.C) | Plan_TDD_Fase1.md: añadidos 3 prompts en Subfase 1.C — 1C.1 (Autosave con concurrencia optimista), 1C.2 (Editor accesible: shortcuts + focus trap + WCAG 2.2 AA), 1C.3 (Preview imprimible + anexo de auditoría compartido con ExportService). PROJECT_STATE.md: corregido nombre de Subfase 1.C ("Privacidad y Exportación" → "Infraestructura de Diseño y Exportación Avanzada"). |
| 2026-05-12 | (planificación 9R + 1.B) | Plan_TDD_Fase1.md: añadidos 3 prompts en bloque 9R — 9R.3.3 (BlockReference + projection + orden topológico + detección de ciclos), 9R.4.4 (versionado de plantillas: política de anclaje y endpoints de migración de workspaces), 9R.6.6 (BlockState=failed + BlockExecutor con retry + propagación de fallos por topología). 9R.6.5 ampliado con instrumentación Langfuse (span raíz + spans por nodo + atributos de modelo/tokens). PROJECT_STATE.md: restaurada Fase 10 (Plantillas y Temas) dentro de Subfase 1.B. |
| 2026-05-12 | 9R.0 | docs/REDACCION_CONTRACT_FIRST.md: propósito del bloque, 8 decisiones de diseño, diagrama DraftingCoreGraph, mapa de ejecución 9R.0→9R.10, reglas duras, glosario. CLAUDE.md: párrafo modules/redaccion/ como edge. Esqueleto de carpetas server/app/modules/redaccion/{contracts,profiles,pipelines,graph,services}/ + frontend/src/redaccion/. |
| 2026-05-12 | 9R.1.1 | ReportTemplateContract + ReportTemplateVersion + ReportTemplateSpec + SectionContract + stubs BlockContract/InputContract/ReportUIContract. AIBlockPolicy/ReviewPolicy/ExportPolicy enums. frozen=True en Version. Validador global→platform. 10 tests verdes en tests/redaccion/test_report_template_contract.py. |
| 2026-05-12 | 9R.1.2 | blocks.py: BlockContract discriminated union (10 tipos, discriminator=kind). inputs.py: InputSlot + InputContract. ui.py: UISection + UIDropzoneDescriptor + UIFieldDescriptor + ReportUIContract. template.py refactorizado para importar de los nuevos módulos. 31 tests verdes en total (21 nuevos). |
| 2026-05-12 | 9R.1.3 | runtime.py: BlockStatus/WorkspaceStatus Literal + _VALID_TRANSITIONS + InvalidBlockTransitionError + Citation + ApprovalRecord + InputArtifact + ExtractionWarning + BlockState.validate_transition + WorkspaceState. drafts.py: ReportTemplateDraft + DraftValidationError + ReportTemplateDraftValidationResult. 44 tests verdes en total (13 nuevos). |
| 2026-05-12 | 9R.1.4 | ORM models: HubReportTemplate + HubReportTemplateVersion + HubWorkspace + HubWorkspaceBlock (UNIQUE workspace_id+block_id) + HubRunManifest. Repos: ReportTemplateRepo + ReportTemplateVersionRepo (append-only) + WorkspaceRepo + WorkspaceBlockRepo + RunManifestRepo. Migración m4b5c6d7e8f9 aplicada (BD local). 53 tests verdes en total (9 nuevos). |
| 2026-05-12 | 9R.2.1+2.2 | profiles/registry.py: ReportProfile Protocol + ReportProfileRegistry (register/get/list). profiles/generic_report.py: GenericReportProfile con default_spec() de 9 secciones, 15 bloques, InputContract Excel/PDF/text, AIBlockPolicy.REQUIRED_REVIEW. profiles/__init__.py: auto-register GENERIC_REPORT. ReportProfileId actualizado a Literal de 5 valores. 68 tests verdes en total (15 nuevos). |
| 2026-05-12 | 9R.3.1+3.2 | blocks/handlers.py: 10 handlers (StaticText, UserInput, DeterministicData, Table, Chart, AIAssistedText, AISummary, AIRewrite, Citation, ReviewGate) con uses_ai/requires_approval/validate/execute/to_manifest. services/block_state_machine.py: BlockTransitionEvent enum + BlockTransitionAuditEvent + BlockStateMachine.transition() + check_assembly_readiness(). 82 tests verdes en total (14 nuevos). |
| 2026-05-12 | 9R.3.3 | contracts/block_io.py: BlockReference (block_id, projection, field_path). blocks.py: depends_on → list[BlockReference]. runtime.py: block_outputs añadido a WorkspaceState. services/block_topology.py: BlockTopology.sort() + detect_cycles() + resolve_inputs() + check_dependencies_ready() + safe_field_resolver con pre-validación. generic_report.py + handlers.py actualizados. 98 tests verdes en total (16 nuevos). |
| 2026-05-12 | 9R.4.1 | services/llm_spec_service.py: LLMSpecService(llm, model_name) + propose_template(prompt_nl, owner_kind) → ReportTemplateDraft. _build_system_prompt diferenciado por owner_kind (admin incluye is_global). _extract_json con soporte markdown fences. TypeAdapter para BlockContract. Sin acceso a BD. 102 tests verdes en total (4 nuevos). |
| 2026-05-12 | 9R.4.2 | services/draft_validator.py: DraftValidator.validate() — 4 checks (profile, depends_on, CHART/TABLE→DETERMINISTIC_DATA, AI+REVIEW_GATE) + _normalize() (IDs únicos, orden por sección). drafts.py: proposed_profile cambiado a str para aceptar output crudo LLM. 108 tests verdes en total (6 nuevos). |
| 2026-05-12 | 9R.4.3 | routers/redaccion/llm_drafts_router.py: 4 endpoints (propose, validate, approve-as-template, approve-as-workspace). get_llm_spec_service como dep inyectable. approve endpoints invocan DraftValidator; 403 si partner intenta is_global; 422 si draft inválido. Registrado en main.py bajo _register_edge. 114 tests verdes (6 nuevos). |
| 2026-05-12 | 9R.4.4 | TemplateMigrationService (detect_new_version + migrate_workspace) + NewVersionNotice + CompatibilityConflictError. ORM: 2 columnas nuevas en hub_workspaces (parent_workspace_id, archived_reason). Migración Alembic n5c6d7e8f9a0 aplicada. hub_redaccion_router.py: GET template-update-notice + POST migrate. Registrado en _register_edge. docs/REDACCION_CONTRACT_FIRST.md: sección "Versionado de plantillas". 163 tests verdes (10 nuevos). |
| 2026-05-12 | 9R.5.1 | pipelines/contracts.py: StorageRef + ExtractionInput + ExtractedTable + ExtractedMetric + ExtractionWarning + ExtractionProvenance + ExtractionResult + ExtractionPipeline (Protocol, runtime_checkable). tests/modules/redaccion/test_extraction_contracts.py: 14 tests verdes (nuevo directorio). 94 tests verdes en total. |
| 2026-05-13 | 9R.5.2 | excel_pipeline.py: ExcelExtractionPipeline (pandas+openpyxl, sheet/header_row/required_columns, provenance con _sheet/_header_row). pdf_text_pipeline.py: PDFTextExtractionPipeline (pdfplumber, detección NON_EXTRACTABLE_PDF). conftest.py con fixtures dinámicas (openpyxl + reportlab). 6 nuevos tests verdes. pandas + pdfplumber añadidos a pyproject.toml. 20 tests verdes en tests/modules/redaccion/. |
| 2026-05-13 | 9R.5.3 | pdf_table_pipeline.py: PDFTableExtractionPipeline (camelot lattice→stream, filtro df.shape[1]<2 para falsos positivos de texto plano, NO_TABLES_FOUND warning). manual_pipeline.py: ManualInputPipeline (parse_number en/es, parse_date ISO/EU, validación contra slot dict). conftest.py: fixture pdf_with_tables (reportlab Table+GRID, 3 cols). camelot-py + pdfplumber añadidos a pyproject.toml. 25 tests verdes en tests/modules/redaccion/. |
| 2026-05-13 | 9R.5.4 | factory.py: ExtractionPipelineFactory (register/get/list, UnknownSourceKindError, build_default_factory con imports tardíos para no cargar Docling en import). admin_script_pipeline.py: AdminScriptExtractionPipeline (aprobación HITL, re-audit AST, sandbox subprocess con repr() para serializaroptions como literales Python). services/script_auditor.py: ScriptSecurityAuditor migrado de supervisar_codigo() con AST real (ast.walk). 33 tests verdes en tests/modules/redaccion/. |
| 2026-05-13 | 9R.6.1 | contracts/runtime.py: spec + artifacts_normalized añadidos a WorkspaceState. graph/state.py: re-export. graph/nodes/load_template.py: LoadTemplateNode + TemplateVersionNotFoundError. graph/nodes/validate_inputs.py: ValidateInputContractNode (emite ExtractionWarning missing_input). graph/nodes/file_normalization.py: FileNormalizationNode. graph/core_graph.py: build_core_graph() → LangGraph compilado. 5 tests verdes en test_core_graph_nodes_load.py. |
| 2026-05-13 | 9R.6.2 | graph/nodes/deterministic_extraction.py: DeterministicExtractionNode (itera DETERMINISTIC_DATA blocks, mapea slot→artifact por kind, escribe content+status=extracted). graph/nodes/data_quality_check.py: DataQualityCheckNode (detecta critical kinds, status=in_review) + data_quality_router. graph/nodes/missing_data_question.py: MissingDataQuestionNode (hitl_question warnings accionables). core_graph.py actualizado con nodos nuevos y arista condicional. 6 tests verdes en test_core_graph_nodes_extraction.py. |
| 2026-05-13 | 9R.6.3 | graph/nodes/ai_assist_draft.py: AIAssistDraftNode (LLMService Protocol, contexto solo de extracted/approved, content={text,model_used,prompt_version}, salta approved/locked, status=error en fallo sin contaminar blocks). graph/nodes/citation_traceability.py: CitationAndTraceabilityNode (Citation desde depends_on, proyecciones raw/summary/field). core_graph.py: data_quality_router redirige ok→ai_assist_draft; missing_data→__end__; citations→finish. 5 tests verdes en test_core_graph_nodes_ai.py. |
| 2026-05-13 | 9R.6.4 | contracts/runtime.py: BlockState+original_ai_content, WorkspaceState+user_edits+final_document+final_document_hash. graph/nodes/review_gate.py: UserReviewGateNode (ai_generated→needs_review, status=in_review si pending) + review_gate_router. graph/nodes/apply_user_edits.py: ApplyUserEditsNode (override contenido, preserva original_ai_content). graph/nodes/final_assembler.py: FinalAssemblerNode (solo approved/locked, SHA-256, status=assembled). core_graph.py: flujo completo con arista condicional review_gate. 6 tests verdes en test_core_graph_nodes_assembly.py. |
| 2026-05-13 | 9R.6.5 | contracts/manifest.py: DraftingRunManifest (id, workspace_id, template_version_id, report_profile, warnings, user_approvals, final_document_hash, status_at_close). graph/tracing.py: SpanHandle+TracingService Protocol, NoOpTracingService, traced_node wrapper (node_span, AI attrs, error event). graph/nodes/audit_log.py: AuditLogNode (open_trace con workspace_id, HubRunManifest ORM, run_manifest_id en span). core_graph.py: todos los nodos envueltos con traced_node, audit_log como nodo final. 10 tests verdes en test_core_graph_audit_tracing.py. |
| 2026-05-13 | 9R.6.6 | runtime.py: FailureKind Literal + WorkspaceBlockedByFailedBlocksError + BlockState(failure_kind, last_error_message, retry_attempts) + WorkspaceState(regenerate_blocks, skip_blocks). services/block_executor.py: LLMTimeoutError/ScriptRuntimeError/ASTValidationError + BlockExecutor(retry 1×, span events, failure_kind map) + NodeResult + propagate_dependency_failures(cascada). ai_assist_draft.py: per-block failed(ai_failed), continúa. review_gate.py: REGENERATE (reset por failure_kind) + SKIP (solo no-required). final_assembler.py: lanza WorkspaceBlockedByFailedBlocksError para required fallidos fuera de skip_blocks. manifest.py: FailedBlockInfo + failed_blocks. audit_log.py: recoge failed_blocks. ORM: +failure_kind+last_error_message+retry_attempts en hub_workspace_blocks. Migración o6d7e8f9a0b1 (pendiente de BD). 79 tests verdes (14 nuevos en test_core_graph_failed_blocks.py). |
