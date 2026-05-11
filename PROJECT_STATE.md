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
| Subfase 1.A — Chatbots Públicos (9B) | 9B.5 ✅ | **9B.6 (RED)** | ▶ En progreso |
| Subfase 1.A → 1.C — Redacción Contract-First (9R) | — | 9R.0 (DOC) | ⏳ Pendiente |
| Subfase 1.B — Identidad y Despliegue | — | Fase 10 / D.1 | ⏳ Pendiente |
| Subfase 1.C — Privacidad y Exportación | — | 1C.0 | ⏳ Pendiente |

**Cursor actual: 9B.6 (RED) — Protocolos de estrategias actualizados para RetrievalPipeline**

> Nota: el bloque **9R** (Redacción Contract-First) se incorporó el 2026-05-11 a partir de `Rediseño_informes.md`.
> Sustituye los antiguos prompts 9.11a–9.11d. Es paralelo a 9B y bloquea la subfase 1.C (1C.4 requiere `DraftingRunManifest` de 9R.9).

---

### Plan_TDD_Fase2.md y Plan_TDD_Fase3.md

| Plan | Estado |
|------|--------|
| Fase 2 — Migración NiceGUI + Agente local | ⏳ No iniciada |
| Fase 3 — Gestor de Expedientes | ⏳ No iniciada |

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
