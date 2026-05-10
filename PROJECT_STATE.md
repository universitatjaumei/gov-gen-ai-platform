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
| CF.5 — CI | — | CF.5.1 | ⏳ Pendiente |

**Cursor actual: CF.5.1 — Configurar CI (GitHub Actions)**

---

### Plan_TDD_Fase1.md — Hub Informativo, Personalización y Redacción (MVP)

| Bloque | Último completado | Siguiente | Estado |
|--------|-------------------|-----------|--------|
| Fase 0 — Infraestructura | — | — | ✅ Eliminada (heredada) |
| Subfase 1.A — Chatbots Públicos | 9B.3 ✅ | **9B.4 (RED)** | ▶ En progreso |
| Subfase 1.B — Identidad y Despliegue | — | Fase 10 / D.1 | ⏳ Pendiente |
| Subfase 1.C — Privacidad y Exportación | — | 1C.0 | ⏳ Pendiente |

**Cursor actual: 9B.4 (RED) — Contrato de evidencias + contrato de pipelines**

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
