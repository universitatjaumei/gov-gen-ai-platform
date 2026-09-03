## Subfase 1.C — Infraestructura de Diseño y Exportación Avanzada de Informes (PENDIENTE)

**Objetivo**: Completar la cadena de valor de los informes: infraestructura de diseño transversal (Focus Mode), exportación a formatos editables (DOCX/ODT) y entrega a flujos humanos externos (Google Drive).

**Dependencias**: BLOQUE 9R — Redacción Contract-First (DraftingCoreGraph + ReportProfiles + DraftingRunManifest). 1C.4 requiere especialmente el manifest emitido por 9R.9 para el anexo de auditoría. (Los antiguos 9.11a–9.11d quedan superseded por 9R.)

**Entregable**: Editor de informes en Focus Mode con exportación a DOCX/ODT con citas trazables y opción de guardar directamente en Google Drive institucional.

---

### Prompt 1C.0 — Focus Mode como Infraestructura de Diseño Transversal (TDD RED/GREEN)

**Modelo sugerido**: **Sonnet** — React + Zustand + componentes shadcn/ui con tests explícitos. Sin lógica LLM. Patrón conocido.

**Objetivo**: Implementar el sistema de Focus Mode y DrawerHub como infraestructura de diseño reutilizable en `frontend/src/shared/layout/`. Sirve tanto al workspace de informes (Subfase 1.C) como, en Fase 2, al editor de flujos de automatización.

**Contexto**: En los workspaces de informes (9.11d), el botón "Exportar" abre un panel lateral. En los flujos de automatización (Fase 2), el mismo panel mostrará las Data Pills y el Copilot. El mismo componente `DrawerHub` sirve a ambos contextos gracias al campo `context` del store.

**Instrucciones al agente**:
```text
Actúa como experto en React y Zustand. Implementa el sistema de Focus Mode y DrawerHub en
frontend/src/shared/layout/.

1. STORE GLOBAL (useFocusStore.ts):
   Zustand store con las siguientes propiedades:
     viewMode: 'standard' | 'focus'   (colapsa el sidebar principal cuando 'focus')
     drawerVisible: boolean
     activeTab: 'config' | 'blocks' | 'data' | 'ai' | 'pills' | 'copilot'
     context: { type: 'informe' | 'flujo'; entityId: string } | null
   Acciones: setViewMode, toggleDrawer, setActiveTab, setContext, reset.

2. DRAWERHUB (DrawerHub.tsx):
   Componente Sheet de shadcn/ui (side="right", width="420px").
   Renderiza pestañas dinámicas según context.type:
     - Si 'informe': pestañas 'Bloques', 'Datos', 'IA'.
     - Si 'flujo': pestañas 'Configuración', 'Data Pills', 'Copilot'.
   Cada pestaña renderiza un slot (children por nombre de pestaña).

3. FOCUSLAYOUT (FocusLayout.tsx):
   HOC/wrapper que:
     - Al montar: llama setContext({type, entityId}) y setViewMode('focus').
     - Al desmontar: llama reset() para restaurar el estado.
     - Colapsa el sidebar principal inyectando la clase 'sidebar-collapsed' en el layout raíz.
     - Renderiza {children} + <DrawerHub />.

USO PREVISTO:
   En AgentWorkspacePanel (9.11d):
     <FocusLayout context={{ type: 'informe', entityId: workspace.id }}>
       <WorkspaceContent />
     </FocusLayout>

TESTS REQUERIDOS (Vitest):
- should_set_focus_mode_on_mount_and_reset_on_unmount
- should_render_informe_tabs_when_context_type_is_informe
- should_render_flujo_tabs_when_context_type_is_flujo
- should_collapse_sidebar_when_view_mode_is_focus
- should_toggle_drawer_visibility
```

**Tests RED — frontend/src/shared/layout/__tests__/FocusMode.test.tsx**:
```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { act } from 'react';

describe('useFocusStore', () => {
  beforeEach(() => {
    // Reset store between tests
    const { reset } = require('../useFocusStore').useFocusStore.getState();
    act(() => reset());
  });

  it('should_set_focus_mode_on_mount_and_reset_on_unmount', () => {
    const { useFocusStore } = require('../useFocusStore');
    const { FocusLayout } = require('../FocusLayout');

    const { unmount } = render(
      <FocusLayout context={{ type: 'informe', entityId: 'ws-123' }}>
        <div>contenido</div>
      </FocusLayout>
    );

    expect(useFocusStore.getState().viewMode).toBe('focus');
    expect(useFocusStore.getState().context?.entityId).toBe('ws-123');

    unmount();

    expect(useFocusStore.getState().viewMode).toBe('standard');
    expect(useFocusStore.getState().context).toBeNull();
  });

  it('should_render_informe_tabs_when_context_type_is_informe', () => {
    const { useFocusStore } = require('../useFocusStore');
    const { DrawerHub } = require('../DrawerHub');

    act(() => {
      useFocusStore.getState().setContext({ type: 'informe', entityId: 'ws-1' });
      useFocusStore.getState().toggleDrawer();
    });

    render(<DrawerHub />);

    expect(screen.getByRole('tab', { name: /bloques/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /datos/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /ia/i })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /copilot/i })).not.toBeInTheDocument();
  });

  it('should_render_flujo_tabs_when_context_type_is_flujo', () => {
    const { useFocusStore } = require('../useFocusStore');
    const { DrawerHub } = require('../DrawerHub');

    act(() => {
      useFocusStore.getState().setContext({ type: 'flujo', entityId: 'flow-1' });
      useFocusStore.getState().toggleDrawer();
    });

    render(<DrawerHub />);

    expect(screen.getByRole('tab', { name: /configuraci/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /data pills/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /copilot/i })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /bloques/i })).not.toBeInTheDocument();
  });

  it('should_collapse_sidebar_when_view_mode_is_focus', () => {
    const { FocusLayout } = require('../FocusLayout');

    const { container } = render(
      <FocusLayout context={{ type: 'informe', entityId: 'ws-1' }}>
        <div>contenido</div>
      </FocusLayout>
    );

    // FocusLayout debe añadir clase sidebar-collapsed al elemento raíz del layout
    const layoutWrapper = container.querySelector('[data-testid="focus-layout"]');
    expect(layoutWrapper).toHaveClass('sidebar-collapsed');
  });

  it('should_toggle_drawer_visibility', () => {
    const { useFocusStore } = require('../useFocusStore');

    expect(useFocusStore.getState().drawerVisible).toBe(false);
    act(() => useFocusStore.getState().toggleDrawer());
    expect(useFocusStore.getState().drawerVisible).toBe(true);
    act(() => useFocusStore.getState().toggleDrawer());
    expect(useFocusStore.getState().drawerVisible).toBe(false);
  });
});
```

**Criterios de aceptación**:
- `FocusLayout` activa `viewMode='focus'` al montar y llama `reset()` al desmontar.
- `DrawerHub` muestra pestañas de Informe cuando `context.type='informe'`; pestañas de Flujo cuando `context.type='flujo'`.
- El sidebar colapsa (clase `sidebar-collapsed`) cuando `viewMode='focus'`.
- `AgentWorkspacePanel` (9.11d) se envuelve con `<FocusLayout>` sin modificar su lógica interna.
- Los 5 tests pasan en verde.

---

### Prompt 1C.0.bis — Copilot Drawer: RAG sobre docs de módulo + NL→config (TDD RED/GREEN)

**Modelo sugerido**: **Opus** — tuning de comportamiento LLM (RAG sobre docs + traductor NL→config estructurada para tres targets distintos). Los prompts del sistema y la validación discriminated-union son finos: Opus reduce iteraciones notablemente sobre Sonnet.

**Objetivo**: añadir al `DrawerHub` (1C.0) un asistente conversacional (`CopilotPanel`) que cumple dos funciones, migradas conceptualmente del legacy `copilot_chat.py` (986 LOC NiceGUI):
1. **RAG sobre la documentación del módulo activo**: el usuario hace preguntas en lenguaje natural ("¿cómo creo un bloque de tabla?", "¿qué pasa si rechazo un bloque IA?") y recibe respuestas basadas en `docs/REDACCION_CONTRACT_FIRST.md` y similares, contextualizadas al módulo donde está navegando.
2. **NL → instrucciones deterministas**: el usuario dicta lo que quiere ("agrupa por mes y suma el importe", "haz un gráfico de barras del total por región") y el copilot produce **configuración estructurada** que las páginas wizard consumen (operaciones ETL del 9R.5.8, configuración de chart del 9R.5.7, propuesta de script del 9R.5.5).

**Dependencias**: 1C.0 (FocusLayout + DrawerHub + useFocusStore), 9R.5.5 (ScriptProposalService — copilot lo invoca para scripts), 9R.5.7 (ChartFactory — copilot lo invoca para gráficos), 9R.5.8 (ETLFactory — copilot lo invoca para transformaciones).

**Origen legacy** (a migrar conceptualmente, no portar literalmente NiceGUI):
- `client_app/app/ui/components/copilot_chat.py` (986 LOC) — patrones reutilizables:
  - Parseo de tags `[PROMPT_PROPOSAL]`, `[ETL_AI_PROMPT]`, `[CHART_AI_PROMPT]` para distinguir "respuesta textual" de "configuración estructurada".
  - `STEP_TYPE_MAP` que mapea contexto del módulo (GRAPHICS/ETL/EXTRACTION) al tipo de instrucción esperada — equivalente a nuestro `BlockKind`.
  - **Pills contextuales**: sugerencias rápidas según el módulo donde está el usuario.
- `client_app/app/ui/focus_manager.py` (183 LOC) — `apply_fix()` con acciones tipadas (CREATE_STEP, ANONYMIZE_VAR…) — patrón a replicar con dispatch via `useFocusStore`.

**Instrucciones al agente**:
```text
Actúa como experto en React + Zustand + RAG. Implementa el CopilotPanel en
frontend/src/shared/layout/copilot/.

1. SERVICIO BACKEND (server/app/modules/redaccion/services/copilot/):
   - DocsRetriever: indexa docs/REDACCION_CONTRACT_FIRST.md + docs/CHATBOTS_PUBLICOS.md
     usando BGE-M3 (el embedding_service ya existente). Filtro por módulo activo.
   - CopilotService.answer(question, context): {answer: str, source_refs: list[str]}
   - CopilotService.translate_nl_to_config(instruction, target_kind): devuelve un
     discriminated union ChartConfig | list[Operation] | ProposalRequest según target_kind.
     Internamente invoca ChartFactory / ETLFactory / ScriptProposalService.
   - Endpoint: POST /api/v1/redaccion/copilot/ask
                POST /api/v1/redaccion/copilot/translate

2. UI (frontend/src/shared/layout/copilot/CopilotPanel.tsx):
   - Input de chat + botón enviar.
   - Pills contextuales (3-5 sugerencias rápidas según useFocusStore.context.type).
   - Distingue dos tipos de respuesta:
     - Textual con citas → renderiza como markdown + lista de referencias.
     - Configuración estructurada → muestra preview + botón "Aplicar" que despacha
       una acción al store de la página activa (ChartConfig al builder de chart,
       Operations al wizard ETL, ProposalRequest al wizard de script).

3. STORE (extiende useFocusStore):
   pendingAction: { kind: 'chart_config' | 'etl_ops' | 'script_proposal'; payload: any } | null
   Acción dispatchCopilotAction(action) que las páginas wizard consumen vía hook
   useCopilotAction(targetKind).

Tests Vitest:
- should_index_docs_and_retrieve_by_module
- should_answer_question_with_source_refs
- should_translate_nl_to_chart_config_when_target_is_chart
- should_translate_nl_to_etl_operations_when_target_is_data_transform
- should_translate_nl_to_script_proposal_when_target_is_admin_script
- should_render_pills_contextual_to_active_module
- should_dispatch_action_to_active_wizard_when_apply_clicked
```

**Criterios de aceptación**:
- 7 tests verdes.
- CopilotPanel integrado como pestaña en DrawerHub (tab "Copilot" tanto en 'informe' como en 'flujo').
- Cero llamadas manuales a fetch — solo hooks Orval.
- i18n en ES/EN/CA.

**Retirada legacy (CLAUDE.md regla Caso A)**:
Al cerrar este prompt en GREEN, mover a `_legacy_nicegui/`:
- `client_app/app/ui/components/copilot_chat.py`
- `client_app/app/ui/components/side_drawer.py`
- `client_app/app/ui/focus_manager.py`
- Tests asociados.
Borrado definitivo manual al cierre de Fase 1.

---

### Prompt 1C.1 — Autosave y resiliencia del Workspace (TDD RED/GREEN)

**Modelo sugerido**: **Sonnet** — concurrencia optimista con contrato explícito (version por workspace + bloque). Patrón conocido, alcance acotado.

**Objetivo**: Persistir automáticamente el estado del Workspace en backend tras cada cambio de bloque, con concurrencia optimista y detección de conflictos. Permite que el usuario pueda cerrar la pestaña o perder conexión sin perder trabajo, y evita pisar cambios de otra sesión abierta del mismo workspace.

**Contexto**: 9R.1.4 crea las tablas `hub_workspaces` y `hub_workspace_blocks`. El editor del 9R.7 emite cambios por bloque (`BlockState`, contenido editado por el usuario, edición de `ai_generated`). Sin autosave, un fallo de red o un cierre accidental pierde el trabajo. Sin versión optimista, dos pestañas abiertas se pisan silenciosamente.

**Dependencias**: 9R.1.4 (tablas), 9R.3.2 (BlockState machine), 1C.0 (Focus Mode).

**Instrucciones al agente**:
```text
Actúa como experto en FastAPI async y React Query. Implementa autosave con concurrencia optimista.

BACKEND — server/app/modules/redaccion/

1. Migración Alembic: añadir `version` (int, default 1, not null) a `hub_workspaces`.
   Cada UPDATE incrementa `version` en 1.

2. Schemas Pydantic en `redaccion/contracts/state_update.py`:
   class BlockUpdate(BaseModel):
       block_id: UUID
       state: BlockState | None          # opcional: transición de estado
       content: dict | None              # opcional: contenido editado del bloque
       expected_block_version: int       # versión esperada del bloque (optimistic lock por bloque)

   class WorkspaceStatePatch(BaseModel):
       expected_workspace_version: int   # versión esperada del workspace
       block_updates: list[BlockUpdate]

   class WorkspaceStatePatchResponse(BaseModel):
       workspace_version: int            # nueva versión tras el patch
       updated_block_versions: dict[UUID, int]
       saved_at: datetime

3. Endpoint en `hub_redaccion_router.py` (Deploy: edge):
   PATCH /api/v1/hub/redaccion/workspaces/{workspace_id}/state
   - 200: aplicado, devuelve nueva versión
   - 409 Conflict: `expected_workspace_version` o `expected_block_version` desactualizada
       Response body: { "current_workspace_version": int, "conflicting_block_ids": [UUID] }
   - 422: BlockState transition inválida (rechaza por la state machine de 9R.3.2)
   - 404: workspace no existe o no pertenece al usuario

4. Servicio `WorkspaceAutosaveService` con método `apply_patch(workspace_id, user_id, patch)`:
   - Lock pesimista de la fila del workspace (SELECT ... FOR UPDATE) durante el patch
   - Verifica `expected_workspace_version` y cada `expected_block_version`
   - Valida transiciones contra `BlockState` machine (9R.3.2)
   - Incrementa versiones, persiste, devuelve nuevo manifest de versiones

FRONTEND — frontend/src/redaccion/hooks/

1. `useAutosave(workspaceId, getState)`:
   - Debounce 1500ms tras el último cambio
   - useEffect con cleanup que cancela debounce al desmontar
   - Mutation que invoca PATCH; on success actualiza la versión en el store local
   - on 409: emite evento `workspace:conflict` con `conflicting_block_ids`
   - on error de red: reintenta con backoff exponencial (3 intentos máx), luego marca el workspace como "offline"

2. Componente `ConflictModal` (frontend/src/redaccion/components/):
   - Se abre al recibir `workspace:conflict`
   - Texto: "Otra sesión ha modificado este workspace. Recarga para ver los cambios; los tuyos no guardados se perderán."
   - Botón único "Recargar workspace" → invalida la query, refetch.

3. Indicador visual en `WorkspaceStatusBar` (9R.7.2):
   - "Guardado hace Ns" / "Guardando..." / "Sin conexión" / "Conflicto sin resolver"

TESTS REQUERIDOS:

Backend (pytest):
- test_patch_with_correct_versions_updates_workspace_and_blocks
- test_patch_with_stale_workspace_version_returns_409
- test_patch_with_stale_block_version_returns_409_with_conflicting_ids
- test_patch_with_invalid_block_state_transition_returns_422
- test_patch_increments_workspace_and_block_versions
- test_patch_is_atomic_on_partial_failure
- test_patch_requires_workspace_ownership

Frontend (Vitest):
- should_debounce_autosave_calls_to_at_most_one_per_1500ms
- should_open_conflict_modal_on_409_response
- should_retry_save_with_backoff_on_network_error
- should_mark_workspace_offline_after_3_failed_retries
- should_update_local_version_after_successful_save
```

**Tests RED — tests/modules/redaccion/unit/test_autosave_service.py**:
```python
"""Tests para WorkspaceAutosaveService — TDD RED."""
import pytest
from uuid import uuid4
from datetime import datetime

from server.app.modules.redaccion.services.autosave_service import (
    WorkspaceAutosaveService, ConflictError, InvalidTransitionError,
)
from server.app.modules.redaccion.contracts.state_update import (
    WorkspaceStatePatch, BlockUpdate,
)


class TestWorkspaceAutosaveService:

    @pytest.mark.asyncio
    async def test_patch_with_correct_versions_updates_workspace_and_blocks(
        self, autosave_service, seeded_workspace_v3_with_blocks
    ) -> None:
        ws, blocks = seeded_workspace_v3_with_blocks
        patch = WorkspaceStatePatch(
            expected_workspace_version=3,
            block_updates=[
                BlockUpdate(
                    block_id=blocks[0].id,
                    state="approved",
                    content={"text": "edited"},
                    expected_block_version=blocks[0].version,
                ),
            ],
        )
        result = await autosave_service.apply_patch(ws.id, ws.owner_id, patch)
        assert result.workspace_version == 4
        assert result.updated_block_versions[blocks[0].id] == blocks[0].version + 1

    @pytest.mark.asyncio
    async def test_patch_with_stale_workspace_version_raises_conflict(
        self, autosave_service, seeded_workspace_v3_with_blocks
    ) -> None:
        ws, _ = seeded_workspace_v3_with_blocks
        patch = WorkspaceStatePatch(expected_workspace_version=1, block_updates=[])
        with pytest.raises(ConflictError) as exc:
            await autosave_service.apply_patch(ws.id, ws.owner_id, patch)
        assert exc.value.current_workspace_version == 3

    @pytest.mark.asyncio
    async def test_patch_with_stale_block_version_raises_conflict_with_ids(
        self, autosave_service, seeded_workspace_v3_with_blocks
    ) -> None:
        ws, blocks = seeded_workspace_v3_with_blocks
        patch = WorkspaceStatePatch(
            expected_workspace_version=3,
            block_updates=[
                BlockUpdate(
                    block_id=blocks[0].id,
                    content={"text": "x"},
                    expected_block_version=blocks[0].version - 1,  # stale
                ),
            ],
        )
        with pytest.raises(ConflictError) as exc:
            await autosave_service.apply_patch(ws.id, ws.owner_id, patch)
        assert blocks[0].id in exc.value.conflicting_block_ids

    @pytest.mark.asyncio
    async def test_patch_with_invalid_state_transition_raises(
        self, autosave_service, seeded_workspace_v3_with_blocks
    ) -> None:
        ws, blocks = seeded_workspace_v3_with_blocks
        # blocks[0] está en 'draft'; no se puede pasar directamente a 'locked'
        patch = WorkspaceStatePatch(
            expected_workspace_version=3,
            block_updates=[
                BlockUpdate(
                    block_id=blocks[0].id,
                    state="locked",
                    expected_block_version=blocks[0].version,
                ),
            ],
        )
        with pytest.raises(InvalidTransitionError):
            await autosave_service.apply_patch(ws.id, ws.owner_id, patch)

    @pytest.mark.asyncio
    async def test_patch_is_atomic_on_partial_failure(
        self, autosave_service, seeded_workspace_v3_with_blocks, session
    ) -> None:
        ws, blocks = seeded_workspace_v3_with_blocks
        # Un update válido + uno inválido → toda la transacción se revierte
        patch = WorkspaceStatePatch(
            expected_workspace_version=3,
            block_updates=[
                BlockUpdate(
                    block_id=blocks[0].id, content={"x": 1},
                    expected_block_version=blocks[0].version,
                ),
                BlockUpdate(
                    block_id=blocks[1].id, state="locked",  # inválido
                    expected_block_version=blocks[1].version,
                ),
            ],
        )
        with pytest.raises(InvalidTransitionError):
            await autosave_service.apply_patch(ws.id, ws.owner_id, patch)
        # versión del workspace y bloques sin cambios
        await session.refresh(ws)
        assert ws.version == 3
```

**Tests RED — frontend/src/redaccion/hooks/\_\_tests\_\_/useAutosave.test.tsx**:
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAutosave } from '../useAutosave';

const PATCH_URL = /\/api\/v1\/hub\/redaccion\/workspaces\/.+\/state/;

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('useAutosave', () => {
  beforeEach(() => { vi.useFakeTimers(); });

  it('should_debounce_autosave_calls_to_at_most_one_per_1500ms', async () => {
    const patchMock = vi.fn().mockResolvedValue({ workspace_version: 2 });
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock),
      { wrapper },
    );
    act(() => { result.current.markDirty(); });
    act(() => { result.current.markDirty(); });
    act(() => { result.current.markDirty(); });
    vi.advanceTimersByTime(1499);
    expect(patchMock).not.toHaveBeenCalled();
    vi.advanceTimersByTime(2);
    await waitFor(() => expect(patchMock).toHaveBeenCalledTimes(1));
  });

  it('should_open_conflict_modal_on_409_response', async () => {
    const patchMock = vi.fn().mockRejectedValue({
      status: 409, body: { current_workspace_version: 5, conflicting_block_ids: ['b1'] },
    });
    const onConflict = vi.fn();
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock, { onConflict }),
      { wrapper },
    );
    act(() => { result.current.markDirty(); });
    vi.advanceTimersByTime(1600);
    await waitFor(() => expect(onConflict).toHaveBeenCalledWith({
      current_workspace_version: 5, conflicting_block_ids: ['b1'],
    }));
  });

  it('should_retry_save_with_backoff_on_network_error', async () => {
    const patchMock = vi.fn()
      .mockRejectedValueOnce(new Error('network'))
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValue({ workspace_version: 2 });
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock),
      { wrapper },
    );
    act(() => { result.current.markDirty(); });
    vi.advanceTimersByTime(1600);
    await vi.runAllTimersAsync();
    expect(patchMock).toHaveBeenCalledTimes(3);
  });

  it('should_mark_workspace_offline_after_3_failed_retries', async () => {
    const patchMock = vi.fn().mockRejectedValue(new Error('network'));
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock),
      { wrapper },
    );
    act(() => { result.current.markDirty(); });
    vi.advanceTimersByTime(1600);
    await vi.runAllTimersAsync();
    expect(result.current.status).toBe('offline');
  });
});
```

**Criterios de aceptación**:
- Migración Alembic añade `version` a `hub_workspaces` y `hub_workspace_blocks`.
- `PATCH /api/v1/hub/redaccion/workspaces/{id}/state` devuelve 200/409/422 según contrato.
- `WorkspaceAutosaveService` es atómico: si un `BlockUpdate` falla, ningún cambio se persiste.
- `useAutosave` debounceá 1500ms, reintenta con backoff y emite `onConflict` ante 409.
- `WorkspaceStatusBar` muestra estado (`saved`/`saving`/`offline`/`conflict`).
- 7 tests backend + 4 tests frontend en verde.

---
