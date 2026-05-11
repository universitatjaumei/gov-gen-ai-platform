# Plan TDD — Fase 2: Automatización, Thin Client y Migración NiceGUI

> Actualizado: 2026-05-04. Generado dividiendo `PLAN_TDD_DETALLADO.md` en tres archivos por fase funcional.

## Propósito
Fase 2 del plan de desarrollo de Gov Gen AI Platform. Migra la lógica de automatización de NiceGUI
(`client_app/`) a la nueva arquitectura React/FastAPI, implementa el Thin Client local (agente de
ejecución edge), el Sandbox distribuido Edge↔Thin-client, el RunManifest+AuditService unificado
y el Script Registry con IA Frugal.

## Prerrequisito
Subfase 1.A de la Fase 1 desplegada en staging (chatbots públicos operativos).

## Alcance
- **Subfase 2.A:** Agente de ejecución local (Thin Client, Prompt 9.16) + Sandbox distribuido (FASE 14).
- **Subfase 2.B:** Migración de UI NiceGUI→React (Guía 9C.0, Prompts 9.12a, 9.12, 9.12b, 9.13, 9.14, 9.15).
- **Subfase 2.C:** RunManifest/AuditService unificado (FASE 15) + Fábricas como nodos LangGraph (FASE 16) + Bridges semánticos (FASE 18).

## Qué NO se ejecuta en esta fase
- Gestor de Expedientes → Fase 3.
- RPA Web (FASE 21) → Diferido a v2 (incluido al final de este documento como referencia).
- Microservicios de computación pesada (FASE 22) → Diferido post-cloud (ver Plan_TDD_Fase3.md).

## Prompts con TDD por detallar antes de ejecutar

### Prompts ya descritos en este documento (arquitectura definida, TDD pendiente)
- **FASE 14** (Sandbox distribuido Edge↔Thin-client)
- **FASE 15** (RunManifest + AuditService + Script Registry)
- **FASE 16** (Determinista-first + Fábricas como nodos LangGraph)
- **FASE 18** (Bridges Semánticos Ampliados)

### Prompts adicionales previstos (anotados al final de cada subfase)
Los siguientes prompts han sido identificados en la planificación pero sus prompts TDD
no se desarrollarán hasta comenzar la subfase correspondiente:

| ID tentativo | Subfase | Descripción |
|---|---|---|
| 2A.2 | 2.A | Secure Pairing del Thin Client |
| 2A.3 | 2.A | Skill de Sincronización de Workspace (Google Drive / OneDrive) |
| 2A.4 | 2.A | Vault Edge: almacenamiento cifrado de mappings NER |
| 2C.0 | 2.C | MCP Client: cliente de herramientas institucionales |
| 2C.5 | 2.C | Hermes NodoAprendizaje: SkillExtractor automático |
| 2C.6 | 2.C | Semantic Cache pre-LLM (activación condicional) |

---

## BLOQUE 9C — Automatización (migración NiceGUI)

*Prerrequisito: Bloque 9A completado (layout admin disponible). Cada prompt incluye el traslado del equivalente NiceGUI a _legacy_nicegui.*

**Orden de ejecución dentro del bloque** (las dependencias son estrictas):

```
Guía 9C.0 (conceptual, se lee antes de escribir código)
  ├── 9.12a  Focus Mode React          ──┐
  │                                       ├──► 9.12  Flujos
  │                                       │
  └── 9.12b  Refactor backend Docling  ──┼──► 9.13  PDF extractor (UI)
                                          │
                                          └──► 9.14  Scripts
                                               9.15  Traslado final NiceGUI a _legacy_nicegui
```

---

### Guía 9C.0 — Separación de lógica NiceGUI → React/FastAPI

**Objetivo**: Regla única y reutilizable para decidir, ante cualquier página NiceGUI a migrar, qué sube al servidor FastAPI y qué queda como estado local React. Aplica a los prompts 9.12, 9.13, 9.14 y a cualquier átomo/procesador que se migre en el futuro sin necesidad de una nueva revisión arquitectónica.

Esta guía **no produce código**: es el filtro conceptual que cada prompt de migración aplica en su sección "Separación de lógica". Léela antes de abrir el fichero NiceGUI y clasifica cada bloque según las reglas de abajo.

#### Reglas de clasificación

| Tipo de código en NiceGUI | Destino | Justificación |
|---|---|---|
| Acceso a BD, llamadas a LLM, lectura/escritura de ficheros de servidor | **FastAPI** (endpoint nuevo o existente) | Privilegios, credenciales y transaccionalidad viven en el servidor |
| Máquinas de estado con fases canónicas (`PHASE_RANGES`, progreso de ejecución, checkpoints) | **FastAPI** (persistido) | Debe sobrevivir a refresco de página y ser auditable |
| Servicios de automatización (WorkflowHealthService, CoherenceService, BridgeService, PillProvider, validaciones estructurales de FlowSpec/TaskSpec) | **FastAPI** (módulo `server/app/modules/automation/`) | Son reglas de dominio, no de UI; deben poder invocarse también desde ejecución headless |
| Orquestación de pasos, validación cruzada entre campos, cálculo de variables disponibles (data pills) | **FastAPI** | Dominio |
| Singletons `FocusManager`, `LayoutState`, `layout_manager` | **React state** (Context o Zustand) | Son estado de presentación puro; no tienen sentido en el servidor |
| Visibilidad de pestañas/drawer, pestaña activa, modo expert, colapso del sidebar | **React state local** | UI puro; volátil por diseño |
| Selección actual del usuario (`editing_step`, `designing_atom_type`, fila seleccionada) | **React state local** | UI puro |
| Caché de listados, mutaciones, invalidación | **react-query** (cliente) | Estándar del stack frontend |
| Formularios antes de `submit` | **react-hook-form + zod** (cliente) | Validación síncrona sin round-trip |
| Mensajes i18n, etiquetas, tooltips | **React + i18next** | Nunca hardcodeados en TSX |

#### Contrato de datos que viaja por la API

Por cada pantalla que se migra, el prompt correspondiente **debe** documentar:

1. **Endpoints consumidos** (verbo + path + body/query + response schema resumido).
2. **Esquema del estado de servidor** que persiste (tabla/columna o documento) y cuál es su clave primaria.
3. **Esquema del estado de cliente** (qué campos viven en React y cuándo se pierden al navegar).
4. **Polling / SSE**: si hay procesos largos, se indica cadencia y condición de parada.

#### Checklist aplicado en cada prompt de migración

Antes de cerrar un prompt 9.1x debe cumplirse:

- [ ] Toda lógica clasificable como "dominio" según la tabla vive en `server/app/modules/...`, con tests unitarios en `server/tests/`.
- [ ] La UI React es declarativa: no contiene `if/else` sobre reglas de negocio más allá de "qué componente renderizar".
- [ ] No hay duplicación cliente/servidor de la misma validación (una validación de dominio se aplica **solo** en el servidor; la validación de formulario del cliente es puramente ergonómica).
- [ ] El fichero NiceGUI equivalente está movido a _legacy_nicegui (no borrado).
- [ ] Ningún `grep -r` devuelve imports del módulo NiceGUI eliminado.
- [ ] `docker compose up` + `pytest` completan en verde tras el borrado.

---

### Prompt 9.12a - Focus Mode React: LayoutContext + DrawerHub

**Objetivo**: Replicar en React el "focus mode" de NiceGUI: drawer lateral derecho con tres pestañas (**Configuración**, **Data Pills**, **Copilot**) y colapso del sidebar izquierdo. Las pestañas visibles dependen del modo activo y del tipo de átomo/paso que se está diseñando. Prerequisito de 9.12 (Flujos); reutilizable por cualquier pantalla de automatización que necesite drawer contextual.

**Elección de arquitectura de estado — Zustand (no Context)**:

Justificación:
- El estado de layout lo leen y mutan componentes muy dispersos (sidebar, drawer, toolbar, páginas hijas). Con Context cualquier mutación re-renderiza a todos los consumidores; con Zustand cada componente se suscribe solo a las slices que usa.
- El equivalente NiceGUI (`FocusManager` + `LayoutState` + `layout_manager`) son singletons con polling cada 200 ms. En React eso se traduce a un store global con suscripción fina, no a un árbol de Providers.
- Zustand tiene API mínima, no exige Provider wrapper y se integra trivialmente con tests (se puede resetear entre tests con `useLayoutStore.setState(initialState)`).

**Instalación**:
```bash
npm install zustand
npx shadcn@latest add sheet scroll-area tabs
```

**`src/automation/state/useLayoutStore.ts`** — store de layout:
```typescript
// slices: viewMode ('standard' | 'focus'), drawerVisible, activeTab ('config' | 'pills' | 'copilot'),
//         currentMode ('gallery' | 'design' | 'documentation' | 'flow_edit'),
//         designingAtomType (string | null), editingStep (StepSpec | null),
//         sidebarCollapsed (boolean)
// acciones: enterFocusMode(step, flow?), exitFocusMode(), setActiveTab(tab),
//           setDesigningAtomType(type | null), setEditingStep(step | null)
// selectores derivados: selectVisibleTabs(state) → ('config' | 'pills' | 'copilot')[]
//   ├── regla: en flow_edit → las tres pestañas
//   ├── regla: si hay designingAtomType → según capabilityMap[type] (has_stepper, has_variables)
//   ├── regla: gallery/documentation → config + (pills si documentation)
//   └── regla: fallback → solo copilot
// efecto: al entrar en focus mode, sidebarCollapsed = true y drawerVisible = true
```

**`src/automation/config/capabilityMap.ts`** — réplica del mapa NiceGUI:
```typescript
// Mapa atomType → { hasStepper: boolean, hasVariables: boolean }
// Se exporta DEFAULT_CAPABILITY = { hasStepper: true, hasVariables: true }
// Derivado 1:1 de client_app/app/config/capability_map.py
```

**`src/automation/components/DrawerHub.tsx`**:
```typescript
// <Sheet side="right" open={drawerVisible} onOpenChange={...}>
//   <header>: icono contextual + título i18n + botón cerrar
//   <Tabs value={activeTab}>:
//     renderiza solo las pestañas devueltas por selectVisibleTabs
//     tabs posibles: Configuración (tune), Data Pills (data_object), Copilot (auto_awesome)
//   <TabsContent value="config">  → <ConfigPanel />
//   <TabsContent value="pills">   → <DataPillsPanel />
//   <TabsContent value="copilot"> → <CopilotPanel />
// </Sheet>
// Sincronización automática: un useEffect corrige activeTab si la pestaña
//   activa deja de ser visible (replica la lógica de drawer_hub.py líneas 62-77).
```

**`src/automation/components/DataPillsPanel.tsx`**:
```typescript
// Props: flowId, currentStepIndex
// useQuery: GET /api/v1/automation/flows/{flowId}/pills?beforeStep={currentStepIndex}
//   → DataPill[] = { label, originStep, varName, reference: "{{STEP.var}}" }
// Render agrupado por originStep (accordion)
// Cada pill es un botón copyable: click → navigator.clipboard.writeText(pill.reference)
// onInsert?: callback opcional que recibe la referencia para insertarla en el campo activo
```

**`src/automation/components/AutomationLayout.tsx`** — integración con sidebar:
```typescript
// Layout wrapper que lee viewMode + sidebarCollapsed del store
// <aside className={cn(
//   'transition-all',
//   sidebarCollapsed ? 'w-16' : 'w-64'
// )}>
// <main className={viewMode === 'focus' ? 'h-screen overflow-hidden' : 'max-w-7xl mx-auto p-4'}>
// <DrawerHub /> (solo montado cuando drawerVisible)
```

**Separación de lógica aplicada (según Guía 9C.0)**:

- **Servidor**: `PillProvider.get_available_pills(step_index)` se expone como `GET /api/v1/automation/flows/{id}/pills?beforeStep={n}` y devuelve `DataPill[]`. Se elimina la lógica Python de `client_app/app/ui/pill_logic.py` de la UI; queda un servicio en `server/app/modules/automation/pills_service.py`. El `capability_map` se expone adicionalmente como `GET /api/v1/automation/atoms/capabilities` para que el frontend lo cachee al arranque (react-query, `staleTime: Infinity`).
- **Cliente**: viewMode, drawerVisible, activeTab, editingStep, designingAtomType, sidebarCollapsed. Ninguno se persiste en BD; se pierden al recargar por diseño.
- **Contrato API**:
  ```
  GET /api/v1/automation/flows/{id}/pills?beforeStep=<int>
  → 200 { pills: [{ label, origin_step, var_name, reference }] }

  GET /api/v1/automation/atoms/capabilities
  → 200 { capabilities: { "email.send": {has_stepper, has_variables}, ... } }
  ```

**Tests requeridos** (Vitest + Testing Library):
```typescript
// src/automation/state/__tests__/useLayoutStore.test.ts
// should_enter_focus_mode_and_collapse_sidebar
// should_exit_focus_mode_and_restore_sidebar
// should_show_all_three_tabs_in_flow_edit_mode
// should_hide_pills_tab_when_capability_disables_variables
// should_auto_switch_active_tab_when_current_becomes_invisible

// src/automation/components/__tests__/DrawerHub.test.tsx
// should_render_only_visible_tabs
// should_close_drawer_on_header_button_click
// should_copy_pill_reference_to_clipboard_on_click

// src/automation/components/__tests__/DataPillsPanel.test.tsx
// should_group_pills_by_origin_step
// should_call_onInsert_with_reference_when_provided
// should_show_empty_state_when_no_previous_steps
```

**Traslado NiceGUI a _legacy_nicegui** (se aplica parcialmente aquí; el resto al cerrar 9.12/9.13/9.14):
```bash
# El borrado de focus_manager/layout_state/drawer_hub/pill_logic NO ocurre en este commit
# porque las páginas NiceGUI que aún no se han migrado siguen dependiendo de ellos.
# Se documenta como deuda que se cancela en 9.15 (Traslado final NiceGUI a _legacy_nicegui).
```

---

### Prompt 9.12 - Automation > Flujos

**Objetivo**: Pantalla de gestión de flujos de automatización con editor en Focus Mode. Reemplaza `client_app/app/ui/flows_page.py` (950 líneas, ~50% lógica mezclada).

**Endpoints que consume**:
- `GET    /api/v1/automation/flows`
- `POST   /api/v1/automation/flows`
- `GET    /api/v1/automation/flows/{id}`
- `PUT    /api/v1/automation/flows/{id}`
- `DELETE /api/v1/automation/flows/{id}`
- `POST   /api/v1/automation/flows/{id}/run`
- `GET    /api/v1/automation/flows/{id}/runs/{run_id}`
- `POST   /api/v1/automation/flows/{id}/validate` *(nuevo, ver separación)*
- `GET    /api/v1/automation/flows/{id}/pills?beforeStep={n}` *(de 9.12a)*

**Estructura de ficheros**:
```
src/admin/pages/FlowsPage.tsx           ← listado + acciones CRUD
src/automation/pages/FlowEditor.tsx     ← editor en focus mode
src/automation/components/FlowStepList.tsx
src/automation/components/FlowStepCard.tsx
src/automation/components/FlowValidationBadge.tsx
src/automation/hooks/useFlowValidation.ts
```

**`src/admin/pages/FlowsPage.tsx`** — listado:
```typescript
// DataTable (@tanstack/react-table): nombre, descripción, estado última ejecución, versión publicada, acciones
// Diálogo crear flujo: nombre + descripción (react-hook-form + zod)
// Botón "Ejecutar": POST /flows/{id}/run → navegar a vista de ejecución
// Badge de estado: pending / running / done / error (polling con react-query refetchInterval mientras running)
// Botón "Editar" → navega a /admin/flows/{id}/edit
```

**`src/automation/pages/FlowEditor.tsx`** — editor (usa Focus Mode):
```typescript
// Al montar: enterFocusMode() del store (9.12a)
// Layout de tres zonas:
//   - Sidebar izquierdo colapsado (desde 9.12a)
//   - Main: lista de pasos reordenables (dnd-kit)
//   - DrawerHub (desde 9.12a) con las tres pestañas
// Seleccionar paso: setEditingStep(step) → el DrawerHub muestra
//   Configuración (form del átomo), Data Pills (variables anteriores) y Copilot
// Validación del flujo: POST /flows/{id}/validate → devuelve issues[]
//   useFlowValidation() invalida cada vez que el usuario guarda un paso
// Guardar: PUT /flows/{id}; optimistic update con react-query
// Salir: exitFocusMode() + router back
```

**Separación de lógica aplicada (según Guía 9C.0)**:

| Lógica en `flows_page.py` | Destino nuevo | Notas |
|---|---|---|
| `FlowsState` (filtros, orden) | **React local** (`useState` en FlowsPage) | UI puro |
| `async flow loading` + `save` (líneas 148-256, 840-924) | **FastAPI** existente (`GET/PUT /flows/{id}`) | Ya están |
| Validación estructural (líneas 900-920) | **FastAPI** nuevo endpoint `POST /flows/{id}/validate` | Reutiliza `WorkflowHealthService` que sube al servidor |
| `WorkflowHealthService`, `CoherenceService` | **FastAPI** (`server/app/modules/automation/health.py`) | Dominio, deben poder invocarse también en ejecución headless |
| Integración con copilot (callbacks `on_atom_select`) | **React** (`CopilotPanel` lee del store) | El copilot es UI |
| `FlowRegistryService` | **FastAPI** (si no existe ya) | Persistencia |
| Selección de paso, expansión de filas, modo edición | **React local** | UI puro |

**Nuevos endpoints a crear en el servidor**:
```
POST /api/v1/automation/flows/{id}/validate
  → 200 { issues: [{ step_index, severity, type, message, fix_suggestion? }] }
  Reutiliza WorkflowHealthService (movido desde client_app al servidor).
```

**Tests requeridos**:
```typescript
// src/admin/pages/__tests__/FlowsPage.test.tsx
// should_list_flows_on_mount
// should_open_create_dialog_on_button_click
// should_show_running_status_during_execution
// should_poll_until_execution_completes
// should_invalidate_cache_after_create

// src/automation/pages/__tests__/FlowEditor.test.tsx
// should_enter_focus_mode_on_mount
// should_exit_focus_mode_on_unmount
// should_show_step_form_in_drawer_when_step_selected
// should_show_validation_badge_for_step_with_issues
// should_reorder_steps_via_drag_and_drop
// should_save_flow_and_invalidate_queries
```

**Tests backend (pytest)**:
```python
# server/tests/modules/automation/test_health_service.py
# test_detects_missing_required_input
# test_detects_type_mismatch_between_steps
# test_validates_via_endpoint_returns_issues_list

# server/tests/modules/automation/test_pills_service.py  (de 9.12a)
# test_returns_only_outputs_of_previous_steps
# test_pill_reference_format_uses_step_id
```

**Traslado NiceGUI a _legacy_nicegui** (en el mismo commit que GREEN):
```bash
# Borrar: client_app/app/ui/flows_page.py
# Borrar: client_app/app/ui/flows_translations.json (migrado a i18next)
# Mover al servidor (no borrar antes de migrar lógica): servicios de health/coherence
#   client_app/app/services/health_service.py       → server/app/modules/automation/health.py
#   client_app/app/services/coherence_service.py    → server/app/modules/automation/coherence.py
#   client_app/app/services/bridge_creator.py       → server/app/modules/automation/bridge.py
# Verificar sin residuos:
grep -rn "flows_page\|FlowsState\b" client_app/ --include="*.py"   # debe ser vacío
grep -rn "health_service\|coherence_service" client_app/ --include="*.py"  # debe ser vacío
# Confirmar: docker compose up && pytest && npm test
```

---

### Prompt 9.12b.0 — Auditoría funcional del extractor legacy

**Objetivo**: Capturar el comportamiento funcional verificable del extractor NiceGUI como especificación antes de escribir una sola línea nueva. Evita que la migración rompa funcionalidad no documentada y permite medir si la nueva implementación cubre todos los casos críticos.

**Prerequisito de todos los prompts 9.12b–9.13.** No abrir ningún fichero nuevo hasta que este artefacto exista.

**Ficheros a analizar** (solo lectura):
```
client_app/app/ui/extraction_page.py
client_app/app/services/extraction_service.py
```

**Artefacto de salida**: `docs/migración/legacy_extraction_spec.md`

```
# Legacy Extraction Behaviour Spec
## Modos: library / design / execution
## Fases y transiciones (PHASE_RANGES con rangos de progreso)
## Inputs: tipos aceptados, validaciones, límites de tamaño
## Outputs: estructura de datos devuelta, ficheros generados, contratos implícitos
## Prompts LLM: plantillas, variables interpoladas, formato de salida esperado
## Scripts generados: formato, dependencias, restricciones sandbox
## Validaciones aplicadas: IBAN, NIF, fecha, importe, …
## Errores documentados y sus mensajes de usuario
## Casos críticos: PDFs sin OCR, tablas complejas, documentos multipágina
```

**Clasificación previa de bloques legacy** (aplicando tabla de Guía 9C.0):

| Bloque legacy | Destino nuevo | Riesgo |
|---|---|---|
| `ExtractionState`, `DesignState`, `ExecutionState` | React local | Bajo |
| `PHASE_RANGES`, rangos de progreso | Constante React + derivado de `progress` backend | Bajo |
| `extraer_texto_dual`, `PdfReaderDual` | **Eliminar** — reemplazado por Docling | Medio |
| Construcción de prompts (`{texto_fitz}`, `{texto_plumber}`) | FastAPI `prompts.py` — reescribir con `{markdown}` + `{tables_json}` | Alto |
| `FieldDef`, validación de valores (IBAN, NIF, …) | FastAPI `extraction_service.py` | Medio |
| Orquestación fases 0–3 | FastAPI (refactor de `extraction_strategies.py`) | Alto |
| Ejecución sandbox | FastAPI / Thin client (FASE 14) | Alto |
| Wizard, panels, drawers, stepper | React — composición manual (no autogenerable) | Bajo |
| Lógica de permisos y auditoría | FastAPI `audit_service.py` | Medio |

**Criterio de cierre**: `docs/migración/legacy_extraction_spec.md` creado y revisado. Solo entonces se arranca 9.12b.

---

### Prompt 9.12b - Refactor backend PDF extractor a Docling

**Objetivo**: Sustituir el motor dual `pdfplumber` + `fitz` (actualmente en `shared/automatia_shared/core/pdf_reader.py::PdfReaderDual` y consumido por `server/app/modules/automation/extraction_strategies.py`) por **Docling** (ya instalado para el módulo RAG). El cliente deja de extraer texto localmente: ahora sube el PDF y el servidor hace toda la extracción + prompting. Prerequisito obligatorio de 9.13 (UI del extractor).

**Por qué ahora y no después de la UI**: el contrato de datos que consumen los endpoints de extracción (`texto_fitz` + `texto_plumber`) cambia radicalmente tras el refactor. Diseñar la UI React sobre la API actual y luego rehacerla es trabajo duplicado. Ver PLAN_DESARROLLO.md §Bloque 4C para la decisión.

> **Marco de migración** — esta tarea abarca cuatro ejes simultáneos: (1) cambio de arquitectura UI (NiceGUI mezclaba UI+lógica; React/FastAPI exige separación estricta), (2) cambio de motor documental (`pdfplumber`+`fitz` → Docling), (3) cambio de contrato (`texto_fitz`/`texto_plumber` → `ExtractedDocument`), (4) cambio de interacción (wizard NiceGUI → máquina de estados + contratos de fase). La automatización frontend será alta para tipos, hooks y mutaciones, pero **parcial** para el wizard, que debe diseñarse como composición React específica sobre contratos estables.

**Riesgos conocidos** (por orden de probabilidad de daño):

1. **Empezar 9.13 con 9.12b en rojo**: el contrato `ExtractedDocument` es la única fuente de verdad de la UI. Si la UI se construye sobre la API antigua y luego se rehace, se duplica todo el trabajo de frontend. La regla de bloqueo de 9.12b→9.13 es **sin excepciones**.
2. **Prompts LLM obsoletos**: los prompts legacy referencian `{texto_fitz}` y `{texto_plumber}`. Si se migran literalmente, producirán prompts incoherentes con el contrato Docling. La batería `test_prompts.py` es la validación de este cambio — si falla el test `test_generate_script_no_longer_uses_fitz_or_pdfplumber`, el prompt aún tiene deuda técnica.
3. **Automatizar el wizard**: los formularios simples (campos, feedback, configuración de extracción) son automatizables con Orval+Zod. La navegación entre fases, el stepper, los previews de markdown/tablas y la interacción Copilot requieren diseño manual. Ver tabla de automatización en 9.13.

**Estructura de ficheros a crear**:
```
server/app/modules/automation/pdf_extractor/
├── __init__.py
├── docling_extractor.py          ← Wrapper de alto nivel sobre DoclingProcessor
├── schemas.py                    ← Pydantic: ExtractedDocument, ExtractedTable, ExtractedPage
├── extraction_service.py         ← Orquestación fases 0-3 (refactor de extraction_strategies.py)
├── prompts.py                    ← Prompts adaptados al nuevo formato Docling
└── storage.py                    ← Persistencia de PDFs temporales (MinIO) y runs
```

**Ficheros a eliminar al cerrar el prompt**:
```
shared/automatia_shared/core/pdf_reader.py                   ← PdfReaderDual (fitz)
server/app/modules/automation/extraction_strategies.py       ← lógica basada en texto_fitz/texto_plumber
client_app/app/modules/utilities/pdf_tools.py                ← extracción cliente (si solo se usa para extractor)
client_app/app/modules/extraction/pdf_text_detector.py       ← detector de calidad de texto (obsoleto)
client_app/app/services/extraction_service.py                ← cliente del antiguo API
# Revisar y limpiar en pyproject.toml: pdfplumber, pymupdf (fitz)
```

**Nuevo contrato de salida (`schemas.py`)**:
```python
from pydantic import BaseModel
from typing import Literal

class ExtractedCell(BaseModel):
    text: str
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1

class ExtractedTable(BaseModel):
    page: int                       # 1-based
    caption: str | None
    headers: list[str]
    cells: list[ExtractedCell]
    bbox: tuple[float, float, float, float] | None

class ExtractedPage(BaseModel):
    page: int                       # 1-based
    markdown: str                   # render markdown de la página (Docling)
    plain_text: str                 # texto lineal legible para LLM
    tables: list[ExtractedTable]

class ExtractedDocument(BaseModel):
    source_id: str                  # UUID del run (persistido)
    filename: str
    num_pages: int
    markdown: str                   # documento completo en markdown (Docling)
    pages: list[ExtractedPage]
    tables: list[ExtractedTable]    # vista plana de todas las tablas
    extraction_strategy: Literal["text_linear", "complex_tables"]
    docling_version: str
```

Este `ExtractedDocument` sustituye al "fichero acordeón" de la versión anterior (pares `texto_fitz` / `texto_plumber`). Los prompts de extracción consumirán `markdown` + `tables` estructuradas en lugar de dos vistas de texto plano.

**`docling_extractor.py`** — wrapper:
```python
# Reutiliza DoclingProcessor de server/app/modules/agents_hub/ingestion/docling_processor.py
# pero expone la estructura completa (no solo markdown):
#   result = DocumentConverter().convert(path)
#   - result.document.export_to_markdown()   → ExtractedDocument.markdown
#   - result.document.pages                  → ExtractedPage[] (iterar pages y extraer tables de cada page)
#   - result.document.tables                 → ExtractedTable[] (vista plana)
#
# async def extract(pdf_path: Path, strategy: str) -> ExtractedDocument
#   usa asyncio.to_thread para Docling (la librería es síncrona)
#
# Performance: Docling sobre CPU tarda segundos por PDF. El endpoint de upload
#   debe devolver un run_id inmediatamente y hacer la extracción en background
#   (BackgroundTasks de FastAPI). El cliente hace polling del estado.
```

**`extraction_service.py`** — refactor de `extraction_strategies.py`:
```python
# Fases refactorizadas:
#   Fase 0: analyze_document_structure(doc: ExtractedDocument, language_hint, config)
#     Antes: (doc_text_a, doc_text_b, ...)      → dos vistas de texto
#     Ahora: (doc.markdown[:30000], doc.tables) → markdown + tablas estructuradas
#   Fase 1: extract_precision(doc, selected_fields, user_definition, config)
#   Fase 2: refine_with_feedback(doc, previous_data, user_feedback, config)
#   Fase 3: generate_deterministic_script(docs: list[ExtractedDocument], ...)
#     El script generado YA NO debe usar fitz/pdfplumber directamente; debe
#     consumir un ExtractedDocument proporcionado por el runtime. Ver prompts.py.
#
# Prompts adaptados: el template ahora espera {markdown} y {tables_json}
# en lugar de {texto_fitz} y {texto_plumber}.
```

**`prompts.py`** — constructores de prompt sobre Docling (módulo nuevo):
```python
# build_analyze_structure_prompt(document: ExtractedDocument,
#                                language_hint: str, config) -> str
#   Entradas clave: document.markdown[:30000],
#                   json.dumps([t.model_dump() for t in document.tables])
#   Salida esperada del LLM: JSON { detected_fields: [{ name, type, description }] }

# build_extract_precision_prompt(document: ExtractedDocument,
#                                selected_fields: list[FieldDef],
#                                user_definition: str, config) -> str
#   Entradas: markdown + tables + esquema de campos seleccionados

# build_refine_prompt(document: ExtractedDocument, previous_data: dict,
#                     user_feedback: str, config) -> str
#   Conserva la forma de previous_data; añade el feedback del usuario como
#   instrucción de corrección. NO reemplaza los datos; los enriquece.

# build_generate_script_prompt(documents: list[ExtractedDocument],
#                               field_schema: list[FieldDef], config) -> str
#   El script generado DEBE consumir ExtractedDocument en runtime.
#   PROHIBIDO en el script generado: fitz, pdfplumber, rutas de fichero directas.

# PROHIBIDO en cualquiera de estos constructores:
#   texto_fitz, texto_plumber, import fitz, pdfplumber, PdfReaderDual
```

**Nuevos endpoints** (reemplazan los actuales en `server/app/api/v1/automation.py`):
```
POST /api/v1/automation/extraction/uploads
  multipart/form-data: files[] (PDFs)
  → 200 { run_id: str, file_ids: [str] }
  Dispara extracción en background via BackgroundTasks.

GET /api/v1/automation/extraction/uploads/{run_id}
  → 200 { status: "pending|extracting|done|error", progress: 0..100,
          documents: [ExtractedDocument]? , error?: str }
  El cliente hace polling cada 1s mientras status != done|error.

POST /api/v1/automation/extraction/{run_id}/analyze_structure
POST /api/v1/automation/extraction/{run_id}/extract
POST /api/v1/automation/extraction/{run_id}/refine
POST /api/v1/automation/extraction/{run_id}/generate_script
  Todos reciben campos + config + system_prompt y usan los ExtractedDocument del run.
  Los endpoints antiguos que aceptaban texto_fitz/texto_plumber se BORRAN.
```

**Separación de lógica aplicada (según Guía 9C.0)**:

| Lógica anterior | Destino | Notas |
|---|---|---|
| Extracción PDF en cliente (`pdf_tools.py`, `PdfReaderDual`) | **FastAPI** | El cliente ya no procesa PDFs |
| Estrategia dual fitz/plumber | **Eliminada** | Docling la reemplaza |
| Máquina de fases (analyze → extract → refine → generate) | **FastAPI** existente, prompts adaptados | Sin cambios de diseño, solo de datos de entrada |
| Storage temporal de PDFs | **MinIO** (ya en el stack) | Con TTL de 24h por `run_id` |
| Validación de tipos (IBAN, NIF, fecha, importe) | **FastAPI** `extract_field_from_snippet` | Ya está, se mantiene |

**Tests TDD requeridos**:

```python
# server/tests/modules/automation/pdf_extractor/test_docling_extractor.py
# --- RED primero, GREEN después ---
# test_extracts_markdown_from_text_pdf
# test_extracts_tables_from_tabular_pdf
# test_returns_page_numbers_1_based
# test_handles_multi_page_document
# test_raises_clear_error_on_corrupted_pdf
# test_extracted_document_schema_validates

# server/tests/modules/automation/pdf_extractor/test_extraction_service.py
# test_analyze_structure_receives_markdown_and_tables
# test_extract_precision_injects_markdown_into_prompt
# test_refine_with_feedback_preserves_previous_data_shape
# test_generate_script_no_longer_uses_fitz_or_pdfplumber  ← grep assertion en el script generado

# server/tests/api/v1/test_extraction_uploads.py
# test_upload_returns_run_id_immediately
# test_get_status_reports_progress
# test_get_status_returns_extracted_documents_on_done
# test_old_endpoint_with_texto_fitz_returns_410_gone  ← verificación de borrado
```

**Criterios de cierre (checklist obligatorio antes de pasar a 9.13)**:

- [ ] `pytest server/tests/modules/automation/pdf_extractor/` en verde
- [ ] `grep -rn "pdfplumber\|import fitz\|import pymupdf\|PdfReaderDual" server/ shared/ client_app/` no devuelve coincidencias (excepto `.venv/`)
- [ ] `pdfplumber` y `pymupdf` eliminados de `pyproject.toml` (raíz, `server/`, `shared/`, `client_app/`)
- [ ] `uv lock` regenerado tras el borrado de dependencias
- [ ] `server/app/modules/automation/extraction_strategies.py` **borrado** (no comentado)
- [ ] `shared/automatia_shared/core/pdf_reader.py` **borrado**
- [ ] `docker compose up` arranca sin errores y el endpoint `POST /extraction/uploads` devuelve un `run_id` contra un PDF de test

**Impacto documentado para 9.13 (UI)**:

Cuando 9.13 se implemente, dispondrá de esta API estable:
```
Upload → { run_id }                        (1 round-trip, devuelve en <500ms)
Polling → { status, progress, documents }  (cada 1s hasta done)
Analyze/Extract/Refine/Generate → operan sobre run_id, no sobre texto plano
```
La UI no necesita conocer nada sobre Docling; solo consume `ExtractedDocument`.

---

### Prompt 9.13 - Automation > PDF extractor (UI)

**Objetivo**: Interfaz React de extracción PDF sobre los contratos Docling definidos en 9.12b. Reemplaza `client_app/app/ui/extraction_page.py` (2.370 líneas, ~60% lógica mezclada). Es la migración más densa del bloque.

**Prerequisito**: 9.12b completado y verde. Si el `grep` de `pdfplumber`/`fitz` aún devuelve coincidencias, **no** arrancar este prompt.

**Endpoints que consume** (todos definidos en 9.12b):
- `POST /api/v1/automation/extraction/uploads`
- `GET  /api/v1/automation/extraction/uploads/{run_id}`
- `POST /api/v1/automation/extraction/{run_id}/analyze_structure`
- `POST /api/v1/automation/extraction/{run_id}/extract`
- `POST /api/v1/automation/extraction/{run_id}/refine`
- `POST /api/v1/automation/extraction/{run_id}/generate_script`

**Estructura de ficheros**:
```
src/admin/pages/PdfExtractPage.tsx                 ← Entry point, lista de runs
src/automation/pages/PdfExtractRun.tsx             ← Detalle de un run (Focus Mode)
src/automation/components/PdfDropzone.tsx
src/automation/components/ExtractionPhaseStepper.tsx
src/automation/components/FieldSelector.tsx         ← seleccionar campos tras Fase 0
src/automation/components/ExtractedDataTable.tsx    ← resultado Fase 1
src/automation/components/RefineFeedbackPanel.tsx   ← Fase 2
src/automation/components/GeneratedScriptViewer.tsx ← Fase 3
src/automation/hooks/useExtractionRun.ts            ← polling + mutaciones
```

**`PdfExtractPage.tsx`** — listado de runs:
```typescript
// DataTable: filename, status, fecha, nº de campos extraídos, acciones
// Botón "Nueva extracción" → abre <PdfDropzone /> modal
// Al subir: mutación POST /uploads → navegar a /admin/extraction/{run_id}
```

**`PdfExtractRun.tsx`** — editor en Focus Mode (reutiliza 9.12a):
```typescript
// Al montar: enterFocusMode()
// Stepper horizontal con 4 fases canónicas: Descubrir → Extraer → Refinar → Generar script
// Main area cambia según fase activa
// DrawerHub (desde 9.12a) con tabs: Configuración (estrategia, definición usuario), Data Pills (campos detectados), Copilot
// Barra de progreso global (0-100) mapeada desde el backend
```

**`useExtractionRun.ts`** — polling + fases:
```typescript
// ExtractionPhase — máquina de estados del wizard (fuente de verdad derivada del backend):
// type ExtractionPhase =
//   | 'uploading'       // PDF en tránsito al servidor
//   | 'discover'        // analyze_structure en curso o pendiente
//   | 'select_fields'   // usuario revisa/selecciona campos detectados
//   | 'extract'         // extract en curso
//   | 'refine'          // refine en curso o pendiente
//   | 'generate_script' // generate_script en curso
//   | 'done'
//   | 'error'
// La fase se DERIVA de run.status + run.progress; React no la persiste en BD.
// Regla de derivación: progress < 25 → 'discover'; 25-55 → 'extract';
//                      55-80 → 'refine'; 80-100 → 'generate_script'; 100 → 'done'

// useQuery GET /uploads/{run_id} con refetchInterval: 1000 mientras status !== 'done' && status !== 'error'
// useMutation para cada fase (analyze_structure, extract, refine, generate_script)
// Cada mutación invalida la query del run
// Expone: { run, phase, isLoading, analyze(), extract(fields), refine(feedback), generateScript() }
```

**`ExtractionPhaseStepper.tsx`** — fases:
```typescript
// Mapa fijo de fases (antes PHASE_RANGES en Python, ahora TypeScript):
//   { id: 'discover', label: i18n, range: [0, 25] }
//   { id: 'extract',  label: i18n, range: [25, 55] }
//   { id: 'refine',   label: i18n, range: [55, 80] }
//   { id: 'script',   label: i18n, range: [80, 100] }
// El stepper colorea la fase activa según run.progress
```

**Separación de lógica aplicada (según Guía 9C.0)**:

| Lógica en `extraction_page.py` (2.370 líneas) | Destino nuevo | Notas |
|---|---|---|
| `ExtractionState`, `DesignState`, `ExecutionState` | **React local** (estado del componente + react-query) | UI puro |
| `PHASE_RANGES` + mapeo de progreso global | **React constante** + cálculo derivado | Ya no hay fases internas distintas; el servidor reporta `progress` 0-100 directo |
| Orquestación fases 0-3 (llamadas a `extraction_strategies`) | **FastAPI** (ya movido en 9.12b) | La UI solo dispara mutaciones |
| Servicios `asset_finishing_service`, `extraction_service` | **FastAPI** `server/app/modules/automation/pdf_extractor/` | Ya en 9.12b |
| Validación de campos seleccionados antes de Fase 1 | **FastAPI** + **zod en cliente** | Doble: cliente para UX, servidor como fuente de verdad |
| Upload de PDFs vía NiceGUI | **React** `<PdfDropzone />` con `react-dropzone` | UI puro |
| Cola de procesamiento en Python (threads locales) | **FastAPI BackgroundTasks** | Ya en 9.12b |
| Preview del script generado | **React** `<GeneratedScriptViewer />` con `prismjs` | Render puro |

**Nivel de automatización por componente** (referencia para priorizar el trabajo):

| Componente | Automatización | Estrategia |
|---|---|---|
| Tipos API (`ExtractedDocument`, fases, runs) | Alta | OpenAPI + Orval |
| Hooks de datos | Alta | Orval + React Query |
| Formularios (campos, feedback, configuración) | Alta | react-hook-form + Zod derivado del contrato |
| Upload + polling | Media-alta | Hook manual sobre cliente generado |
| Wizard (stepper, `ExtractionPhase`, transiciones) | Media | State machine + componentes React manuales |
| Focus Mode | Media | Reutilizar patrón 9.12a |
| Preview markdown / tablas | Media | Componentes manuales |
| Prompts LLM | Baja-media | Backend + snapshots TDD |
| Generación de script | Baja-media | Backend + tests de seguridad (grep assertion) |
| UI wizard completa autogenerada | No recomendable | — |

**Nota sobre Focus Mode**: el extractor original tenía un wizard en pantalla completa similar al focus mode de flujos. Se replica el patrón: al entrar al detalle del run, el sidebar se colapsa y el drawer contextual aparece a la derecha. Si el usuario quiere volver al listado, sale del focus mode.

**Tests requeridos**:
```typescript
// src/admin/pages/__tests__/PdfExtractPage.test.tsx
// should_list_runs_on_mount
// should_open_dropzone_on_new_extraction_click
// should_accept_pdf_files_only
// should_navigate_to_run_detail_after_upload

// src/automation/pages/__tests__/PdfExtractRun.test.tsx
// should_enter_focus_mode_on_mount
// should_show_discover_phase_when_progress_below_25
// should_show_extract_phase_when_progress_25_to_55
// should_display_extracted_document_markdown_preview
// should_trigger_analyze_mutation_on_button_click

// src/automation/hooks/__tests__/useExtractionRun.test.ts
// should_poll_every_second_while_pending
// should_stop_polling_when_status_done
// should_stop_polling_on_error
// should_expose_analyze_mutation
// should_expose_extract_mutation
// should_expose_refine_mutation
// should_expose_generate_script_mutation
// should_invalidate_run_query_after_each_mutation

// src/automation/components/__tests__/FieldSelector.test.tsx
// should_render_detected_fields_from_analyze_response
// should_validate_at_least_one_field_selected
// should_use_zod_schema_derived_from_detected_fields_not_hardcoded

// src/automation/components/__tests__/ExtractedDataTable.test.tsx
// should_display_extracted_data_grouped_by_field
// should_show_empty_state_when_no_data

// src/automation/components/__tests__/RefineFeedbackPanel.test.tsx
// should_submit_feedback_via_refine_mutation
// should_disable_submit_while_refining

// src/automation/components/__tests__/GeneratedScriptViewer.test.tsx
// should_display_script_code_and_metadata
// should_not_expose_internal_file_paths_in_rendered_output
```

**Traslado NiceGUI a _legacy_nicegui** (en el mismo commit que GREEN):
```bash
# Borrar:
rm client_app/app/ui/extraction_page.py                 # 2.370 líneas
rm client_app/app/ui/extraction_page_refactored.py
rm client_app/app/ui/extraction_translations.json
# Verificar residuos:
grep -rn "extraction_page\|ExtractionState\|DesignState\|ExecutionState" client_app/ --include="*.py"
# Debe ser vacío. Si devuelve algo, investigar antes de cerrar.
# Confirmar: docker compose up && pytest && npm test
```

---

### Guía 9C.1 — Secuencia de implementación del extractor PDF (12 pasos)

**Objetivo**: Desglosar 9.12b.0 + 9.12b + 9.13 en pasos atómicos verificables para el agente de codificación. Cada paso produce un artefacto antes de avanzar. Bloqueo estricto: no empezar el paso N+1 si el paso N no está verde.

| Paso | Artefacto verificable | Corresponde a |
|---|---|---|
| 0 — Auditoría legacy | `docs/migración/legacy_extraction_spec.md` creado y revisado | 9.12b.0 |
| 1 — Tests RED Docling | `test_docling_extractor.py` falla por implementación pendiente | 9.12b |
| 2 — GREEN Docling | `docling_extractor.py` + `schemas.py`; tests en verde | 9.12b |
| 3 — Prompts sobre Docling | `prompts.py` + `test_prompts.py`; grep sin `texto_fitz` en prompts | 9.12b |
| 4 — API upload + polling | `test_extraction_uploads.py` + endpoints en verde | 9.12b |
| 5 — API fases | `test_extraction_phases.py` + 4 endpoints de fase en verde | 9.12b |
| 6 — Limpieza legacy PDF | grep sin `pdfplumber\|import fitz\|PdfReaderDual`; `pyproject.toml` limpio | 9.12b criterio cierre |
| 7 — Export OpenAPI | `openapi.json` actualizado con rutas de extracción | 9.12b criterio cierre |
| 8 — Orval generate | Hooks y tipos generados; `tsc --noEmit` verde | Prereq 9.13 |
| 9 — `useExtractionRun` | Hook con 8 tests verdes; `ExtractionPhase` implementado | 9.13 |
| 10 — UI base + Focus Mode | `PdfExtractPage` + `PdfExtractRun` + `ExtractionPhaseStepper` | 9.13 |
| 11 — Componentes wizard | `FieldSelector`, `ExtractedDataTable`, `RefineFeedbackPanel`, `GeneratedScriptViewer` | 9.13 |
| 12 — Retirada NiceGUI | grep sin residuos; `pytest` + `npm test` + `tsc --noEmit` verdes | 9.15 |

> Los prompts detallados para dar verbatim al agente en cada uno de estos pasos están en `Migración_extracción_pdf.txt`, sección 5 ("Propuesta de prompts para el agente"), prompts 1–12. Copiar el texto del prompt correspondiente al inicio de cada sesión de codificación.

---

### Prompt 9.14 - Automation > Scripts

**Objetivo**: Catálogo y ejecución de scripts. Reemplaza la vista NiceGUI equivalente.




**`src/admin/pages/ScriptsPage.tsx`** — estructura clave:
```typescript
// Tabs por categoría: trigger / input / processor / output
// Para cada script: nombre, descripción, formulario dinámico generado desde ui_contract
// Historial de ejecuciones por script (tabla colapsable)
// Toggle "Promover a átomo" (solo admin/partner)
```

**Tests requeridos**:
```typescript
// should_render_dynamic_form_from_ui_contract
// should_filter_scripts_by_category
// should_display_execution_history
```

**Traslado NiceGUI a _legacy_nicegui** en el mismo commit.

"Directrices para detallar el TDD de la Fase 2 (Scripts y UI Dinámica)"

Para el desarrollo de la ejecución de scripts y su UI en ScriptsPage.tsx, redacta los tests (fase RED) y la implementación (fase GREEN) exigiendo un contrato Server-Driven UI (SDUI).

Requisitos para el DTO del Backend:

El endpoint que devuelve el detalle de un script debe incluir un ui_contract (un JSON Schema o estructura equivalente). Este contrato debe definir los inputs necesarios (tipo, nombre, label, regex de validación, si es requerido).

Requisitos para los tests TDD del Frontend:

Escribe un test que VERIFIQUE que ScriptsPage.tsx falla o no renderiza nada si el backend no envía el ui_contract.

Escribe un test que VERIFIQUE que el frontend renderiza dinámicamente un <input type="text">, <select> o <input type="file"> basado ÚNICAMENTE en iterar sobre el JSON del ui_contract.

PROHIBIDO: El frontend no puede tener interfaces manuales TypeScript que definan los campos específicos de un script particular (ej. interface ScriptPadrón).

La validación en el cliente (Zod) debe generarse dinámicamente en tiempo de ejecución leyendo el ui_contract.


---

### Prompt 9.15 - Traslado final NiceGUI a _legacy_nicegui

**Objetivo**: Verificar que no queda ningún módulo NiceGUI sin migrar. Borrar los que queden.

**Checklist** (ver CLAUDE.md para el procedimiento completo):
```bash
# 1. Verificar qué módulos de client_app/app/ui/ quedan
ls client_app/app/ui/

# 2. Por cada módulo sin equivalente React todavía:
#    - Si tiene endpoint en el server → posponer (documentar)
#    - Si es UI pura sin backend → eliminar directamente

# 3. Confirmar que no hay imports rotos
grep -r "from client_app.app.ui" . --include="*.py"

# 4. docker compose up + pytest → todo verde
```

---


---

## BLOQUE 9D — Agente de ejecución local

*El agente local reemplaza el cliente NiceGUI como proceso sin UI. Patrón GitLab Runner.*

---

### Prompt 9.16 - Agente de ejecución local: scaffolding

**Objetivo**: Proceso Python ligero en `client_app/local_agent/` que se conecta al servidor por WebSocket, recibe jobs y los ejecuta localmente. Reemplaza la necesidad de que el usuario tenga abierto el cliente NiceGUI pesado para ejecutar tareas de automatización.

**Responsabilidad de Playwright en este agente** (distinción crítica):
- `handlers/rpa.py` implementa **automatización web interactiva para el usuario final**: rellenar formularios, navegar sesiones autenticadas, extraer datos en nombre del usuario. Es una acción puntual iniciada por el usuario a través del frontend.
- Este componente **no tiene nada que ver con el crawler de ingestión documental** (Prompt 9.7.1), que es un proceso server-side con scheduler propio. El crawler corre en el Edge node; el RPA corre en la máquina local del usuario tramitador.
- Playwright puede aparecer en ambos contextos pero con propósitos radicalmente distintos: aquí es un actor humano delegado; en el crawler es un fetcher automatizado de contenido público.

**Estructura**:
```
client_app/local_agent/
├── main.py          # Punto de entrada; conecta al server por WebSocket
├── runner.py        # Recibe jobs {job_id, type, payload} y despacha al handler
├── handlers/
│   ├── script.py    # Ejecuta scripts Python (sandbox existente de AutomatIA)
│   ├── rpa.py       # Playwright RPA interactivo: simula acciones de usuario en webs
│   │                #   (formularios, login, extracción de datos en sesión)
│   │                #   NO se usa para ingesta documental automatizada
│   └── watcher.py   # FolderWatcher y EmailWatcher locales
└── config.py        # AGENT_SERVER_URL, AGENT_TOKEN (desde .env local)
```

**Protocolo WebSocket**:
```json
// Job recibido del servidor:
{ "job_id": "uuid", "type": "script|rpa|watcher", "payload": {...} }

// Resultado reportado al servidor:
{ "job_id": "uuid", "status": "done|error", "output": "...", "error": null }
```

**`main.py`** (esqueleto):
```python
import asyncio, websockets, json, os
from runner import Runner

async def connect():
    url = os.getenv("AGENT_SERVER_URL", "ws://localhost:8000/agent/ws")
    token = os.getenv("AGENT_TOKEN", "")
    runner = Runner()
    async with websockets.connect(url, additional_headers={"Authorization": f"Bearer {token}"}) as ws:
        async for message in ws:
            job = json.loads(message)
            result = await runner.dispatch(job)
            await ws.send(json.dumps(result))

if __name__ == "__main__":
    asyncio.run(connect())
```

**Tests requeridos** (`client_app/tests/test_runner.py`):
```python
# test_runner_dispatches_script_job
# test_runner_dispatches_rpa_job
# test_runner_reports_error_on_failure
# test_runner_unknown_type_returns_error
```

**Criterio de done**: El agente conecta al server, recibe un job de tipo `script`, lo ejecuta y reporta el resultado. Tests pasan.

---

## Subfase 2.A — Prompts adicionales previstos (sin TDD desarrollado)

> Estos prompts completan la Subfase 2.A. Sus prompts TDD atómicos se detallarán
> antes de comenzar su ejecución. Ninguno de ellos está listo para ejecutar en este momento.

---

### [2A.2] Secure Pairing del Thin Client

**Objetivo funcional:** Implementar el mecanismo de emparejamiento seguro del agente local
con el servidor Edge. El Admin genera un token de instalación de un solo uso que el thin
client canjea por credenciales de largo plazo.

**Problema que resuelve:** Sin emparejamiento verificado, cualquier proceso podría
registrarse como agente de ejecución y recibir scripts firmados. Este mecanismo garantiza
que solo agentes autorizados por un Admin pueden ejecutar tareas locales en nombre de una
Organización, cumpliendo el principio de frontera Edge-Cloud documentado en `CLAUDE.md`.

**Dependencias:** Prompt 9.16 (thin client operativo y conectado por WebSocket) · Auth
JWT (Fase 1 completada) · FASE 14 (firma de scripts con ECDSA).

> **Este prompt NO se desarrolla en este documento.** Los prompts TDD se detallarán
> antes de ejecutar la Subfase 2.A.

---

### [2A.3] Skill de Sincronización de Workspace

**Objetivo funcional:** Implementar en el thin client la detección automática de la carpeta
sincronizada de Google Drive File Stream o OneDrive en Windows/Linux, y el handler que
mueve los archivos generados por el servidor a dicha carpeta cuando el Edge emite el
evento `FILE_GENERATED` por WebSocket.

**Problema que resuelve:** Sin este skill, los informes y documentos generados en el
cloud quedan en una carpeta temporal y el usuario debe descargarlos y moverlos
manualmente. El skill cierra el ciclo de entrega local de forma transparente, habilitando
el flujo de trabajo humano fuera de la plataforma previsto en `CAMBIOS PLANIFICACIÓN.md`.

**Dependencias:** Prompt 9.16 (thin client + WebSocket operativo) · FASE 14 (firma y
verificación de scripts) · Prompt 1.B Export DOCX/ODT (Fase 1.C, que genera el fichero).

> **Este prompt NO se desarrolla en este documento.** Los prompts TDD se detallarán
> antes de ejecutar la Subfase 2.A.

---

### [2A.4] Vault Edge: almacenamiento cifrado de mappings NER

**Objetivo funcional:** Implementar en el Edge node el vault cifrado at rest de los
mappings pseudónimo↔valor-real del pipeline NER. El vault es inaccesible desde el cloud
y solo el proceso Edge con la clave privada puede rehidratar los outputs del LLM.

**Problema que resuelve:** La anonimización reversible (FASE 13, Fase 1.C) necesita
persistir los mappings para que la rehidratación sea posible en sesiones largas o
interrumpidas. Sin un vault Edge, los mappings tendrían que viajar al cloud (violando
la soberanía del dato) o perderse (haciendo irreversible la anonimización).

**Dependencias:** FASE 13 (Privacidad NER, Fase 1.C) · FASE 14 (Sandbox Edge) ·
Frontera Edge-Cloud §2.1 de `CLAUDE.md`.

> **Este prompt NO se desarrolla en este documento.** Los prompts TDD se detallarán
> antes de ejecutar la Subfase 2.A.

---

## FASE 14: Sandbox Distribuido Edge ↔ Thin-client

**Tipo**: Migración + split arquitectónico  
**Prerequisitos**: FASE 5 (thin client operativo)  
**Corresponde a**: Fase 5.4–5.5 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Separar la responsabilidad del sandbox entre el Edge node (diseño + auditoría AST + firma del script) y el Thin client (ejecución aislada del script firmado). El Edge firma con clave privada; el thin client verifica con la pública antes de ejecutar.

**Componentes legacy a migrar** (`client_app/app/`):
- `modules/sandbox/safety_sandbox.py` (76 LoC) → **Edge** `server/app/core/sandbox/`
- `services/sandbox_worker.py` (241 LoC) → **Thin client** `client_app/local_agent/sandbox/`
- `services/sandbox_service.py` (214 LoC) → **Edge** (orquestación)

**Contrato Edge ↔ Thin-client**:
1. Edge genera script + RunManifest firmado con ECDSA
2. Thin client verifica firma; rechaza si inválida
3. Thin client ejecuta en sandbox con CPU cap + network egress off + FS restringido
4. Thin client devuelve resultado + manifest de ejecución firmado
5. Edge verifica la firma del resultado y registra en AuditService

**Tests legacy a migrar**: `test_safety_sandbox`, `test_sandbox_isolation`

---

> **Nota:** Los prompts TDD atómicos de esta fase se detallarán antes de ejecutar la Subfase 2.A.


---

## FASE 15: RunManifest + AuditService + Script Registry Unificados (IA Frugal)

**Tipo**: Migración + refactor  
**Prerequisitos**: FASE 12.E3 (AuditService de expedientes), FASE 13 (privacidad)  
**Corresponde a**: Fase 6.2–6.4 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Unificar el formato `run_manifest.json` y la cadena de auditoría SHA-256 para que sea válida en los tres módulos (automation, Hub, expedientes). Migrar el Script Registry con índice semántico para reuso directo sin LLM.

**Componentes legacy a migrar** (`client_app/app/`):
- `services/manifest_generator.py` (165 LoC) + `manifest_signature_service.py` (258 LoC)
- `services/enterprise_audit_service.py` (281 LoC) + `external_script_audit_service.py` (188 LoC)
- `services/script_library_service.py` (840 LoC) + `flow_registry_service.py` (374 LoC)
- `services/script_generator_service.py` (405 LoC) + `script_adaptation_service.py` + `validation_loop.py` (143 LoC) + `custom_script_service.py`

**Destino**: `server/app/core/manifest/` + `server/app/core/audit/` + `server/app/modules/automation/scripts/`

**Capacidades clave**:
- Tabla `scripts_aprobados` con hash + versión + tenant + etiqueta semántica (bge-m3)
- Endpoint de búsqueda por taxonomía (reuso directo sin LLM)
- Métricas de reuso (% tareas resueltas sin invocar LLM) expuestas en panel admin
- Cache semántico pre-LLM (campo `intent_embedding`): activar solo si el piloto lo justifica — evaluar tras tener métricas de taxonomía

**Tests legacy a migrar**: `test_manifest_signature`, `test_script_signing`, `test_external_script_audit`, `test_script_generator_service`, `test_script_adaptation`, `test_script_ingestion`, `test_validation_loop`, `test_flow_registry`

---


> **Nota:** Los prompts TDD atómicos de esta fase se detallarán antes de ejecutar la Subfase 2.C.


---

## FASE 16: Determinista-first + Fábricas como Nodos LangGraph

**Tipo**: Migración + wrapper LangGraph  
**Prerequisitos**: FASE 12.E2 (motor LangGraph expedientes), FASE 15 (Script Registry)  
**Corresponde a**: Fase 6.5 + Fase 7.E2.6 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Migrar los servicios deterministas y las fábricas de código al servidor y exponerlos como nodos invocables desde el grafo LangGraph. La lógica "determinista por defecto, LLM si no encaja" se preserva como estrategia de ejecución.

**Componentes legacy a migrar** (`client_app/app/`):
- `services/deterministic_etl_service.py` (350 LoC) + `deterministic_graphics_service.py` (605 LoC)
- `modules/factory/etl_factory.py` (369 LoC) + `graphics_factory.py` (342 LoC) + `report_factory.py` (540+243 LoC)

**Destino**: `server/app/modules/automation/factories/`

**Nodos LangGraph nuevos** (Fase 7.E2.6):
- `NodoFabrica`: wrapper que invoca `etl_factory` / `graphics_factory` / `report_factory` o cualquier script del Registry
- `NodoValidador`: AST audit + `validation_loop` + heurísticas; etiqueta la propuesta como `segura | requiere_revisión | bloqueada`; intercalado antes del `NodoHuman`

**Tests legacy a migrar**: `test_etl_factory`, `test_graphics_factory`, `test_pdf_factory_refinements`, `test_etl_brain_decoupling`

---


> **Nota:** Los prompts TDD atómicos de esta fase se detallarán antes de ejecutar la Subfase 2.C.


---

## FASE 18: Bridges Semánticos Ampliados (Multi-contexto)

**Tipo**: Migración + extensión  
**Prerequisitos**: FASE 15 (Script Registry), FASE 7.E5 (Adaptadores UJI/G400)  
**Corresponde a**: Fase 6.6 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Pendiente — prompts TDD a detallar antes de ejecutar

**Objetivo**: Migrar los bridges semánticos y generalizarlos para ser invocables desde flows, expedientes y adaptadores de tramitación.

**Componentes legacy a migrar** (`client_app/app/`):
- `services/bridge_creator.py` (118 LoC) + `bridge_generation_service.py` (83 LoC) + `library_bridge.py`

**Destino**: `server/app/modules/automation/bridge/`

**Capacidades nuevas**:
- Interfaz común reutilizable desde flows, expedientes y adaptadores de tramitación
- Detección de discordancias entre esquemas (UJI ↔ Gestión 400) con score de confianza
- Catálogo de bridges reutilizables por par `(sistema_origen, sistema_destino)`
- Bridge como nodo invocable desde el grafo de expedientes

**Tests legacy a migrar**: `test_type_compatibility_bridge`

---


> **Nota:** Los prompts TDD atómicos de esta fase se detallarán antes de ejecutar la Subfase 2.C.


---

## Subfase 2.C — Prompts adicionales previstos (sin TDD desarrollado)

> Estos prompts amplían la Subfase 2.C con capacidades de la filosofía Hermes y el MCP Client.
> Sus prompts TDD atómicos se detallarán antes de comenzar su ejecución.

---

### [2C.0] MCP Client: cliente de herramientas institucionales

**Objetivo funcional:** Implementar el cliente MCP (Model Context Protocol) del lado del
servidor que permite invocar tools expuestas por servidores MCP externos (UJI, Gestión 400,
ENI/ENS). Es el componente que el grafo LangGraph usa para comunicarse con sistemas
institucionales de forma agnóstica.

**Problema que resuelve:** Sin un cliente MCP estandarizado, cada adaptador de Fase 3
requeriría su propia lógica de conexión y autenticación, generando deuda técnica y
acoplamiento. El MCP Client unifica la capa de conectividad y hace que los nodos del grafo
sean independientes del sistema de destino.

**Dependencias:** FASE 15 (Script Registry operativo) · Fase 3 (Adaptadores UJI/G400/ENI)
· FASE 18 (Bridges semánticos).

> **Este prompt NO se desarrolla en este documento.** Los prompts TDD se detallarán
> antes de ejecutar la Subfase 2.C. Es prerequisito bloqueante para la Fase 3.

---

### [2C.5] Hermes NodoAprendizaje: SkillExtractor automático

**Objetivo funcional:** Implementar el nodo LangGraph que, tras una ejecución validada
mediante HITL, extrae automáticamente el script o patrón de solución como un nuevo Skill
y lo propone para inclusión en el Script Registry, sujeto a aprobación del Admin.

**Problema que resuelve:** Sin un mecanismo de aprendizaje controlado, cada automatización
es un caso de uso aislado y la plataforma no acumula valor. El NodoAprendizaje convierte
las ejecuciones HITL-validadas en activos reutilizables, implementando el principio
Hermes de autoaprendizaje determinista (§2.4 de `Arquitectura.md`): "la IA propone,
el humano valida, el sistema aprende".

**Dependencias:** FASE 15 (Script Registry con índice semántico y tabla `scripts_aprobados`)
· FASE 16 (NodoFabrica y NodoValidador operativos) · HITL (Fase 4 base completada).

> **Este prompt NO se desarrolla en este documento.** Los prompts TDD se detallarán
> antes de ejecutar la Subfase 2.C.

---

### [2C.6] Semantic Cache pre-LLM (activación condicional)

**Objetivo funcional:** Implementar un cache semántico que intercepte peticiones al LLM
para tareas de automatización y devuelva directamente el resultado de una ejecución
anterior cuando la intención semántica de la solicitud (campo `intent_embedding`) sea
suficientemente similar a una ya resuelta y almacenada en el Script Registry.

**Problema que resuelve:** Reduce el coste de llamadas al LLM para patrones de
automatización repetitivos (el mismo tipo de extracción sobre formatos similares),
implementando la IA Frugal definida en FASE 15. Genera métricas de "tasa de reuso sin
LLM" visibles en el panel Admin.

**Dependencias:** FASE 15 (campo `intent_embedding` en `scripts_aprobados`) · FASE 16
(Fábricas como nodos LangGraph) · Datos de piloto reales (activar solo si las métricas
de taxonomía lo justifican, según el criterio documentado en FASE 15).

> **Este prompt NO se desarrolla en este documento.** Los prompts TDD se detallarán
> antes de ejecutar la Subfase 2.C, y solo si las métricas del piloto lo justifican.

---

### Nota arquitectónica: invariante de ejecución Edge

> Esta nota documenta un invariante que deben respetar **todos** los prompts de la
> Subfase 2.C. No es un prompt ejecutable.

Los scripts de automatización se ejecutan **en el Edge**, no en el cloud. Esta regla es
absoluta y aplica a:
- Flows y scripts del catálogo (Prompts 9.12–9.14).
- Extractor PDF basado en Docling (Prompt 9.12b / 9.13).
- Scripts de transformación y gráficos para informes (incluso si el informe se redacta
  en cloud institucional).
- Cualquier Skill del Script Registry invocado desde automatización o expedientes.

La orquestación puede residir en cloud (LangGraph), pero el nodo que ejecuta código
determinista llama siempre al Edge vía WebSocket. El cloud recibe el resultado ya
procesado, nunca el documento original ni datos personales en claro.

Este invariante se verifica en el checklist de cierre de cada prompt del Bloque 9C/9D
y de la Subfase 2.C.

---

## FASE 21: RPA Web (Diferido a v2)

**Tipo**: Decisión de no-migración  
**Fuera del alcance del piloto v1**  
**Corresponde a**: Fase 9 de `PLAN_DESARROLLO.md`  
**Estado**: ⏳ Fuera de roadmap v1 — decisión documentada

**Decisión**: `client_app/app/core/rpa_executor.py` (1049 LoC) y `client_app/app/services/web_watcher_service.py` (878 LoC) **no se migran** al thin client en v1. El peso de Playwright (~300-400 MB de navegadores) es incompatible con el objetivo de thin client ligero.

**Durante v1**: código legacy intacto en `client_app/` pero no incluido en el empaquetado del thin client. Si un flujo crítico del piloto requiere web RPA, se despliega un worker Playwright centralizado en el Edge node (Docker headless).

**En v2**: decidir entre re-empaquetar Playwright en el thin client o mantener el worker centralizado en Edge, según la demanda real del piloto.

---

