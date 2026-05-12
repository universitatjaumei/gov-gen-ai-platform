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
| Subfase 1.A → 1.C — Redacción Contract-First (9R) | — | 9R.0 (DOC) | ⏳ Pendiente — 33 prompts (incluye 9R.3.3, 9R.4.4, 9R.6.6 añadidos 2026-05-12) |
| Subfase 1.B — Identidad y Despliegue (Fase 10 + Fase Deploy GCP) | — | 10.1 | ⏳ Pendiente — Fase 10 (temas/plantillas) + D.1-D.5 |
| Subfase 1.C — Infraestructura de Diseño y Exportación Avanzada | — | 1C.0 | ⏳ Pendiente — 6 prompts (1C.0, 1C.1, 1C.2, 1C.3, 1C.4, 1C.5) |

**Cursor actual: 9R.0 (DOC) — Bloque 9R Redacción Contract-First (siguiente subfase)**

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
