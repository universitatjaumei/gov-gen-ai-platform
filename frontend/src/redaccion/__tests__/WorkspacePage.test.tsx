import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { WorkspacePage } from '../pages/WorkspacePage'
import {
  useGetWorkspaceById,
  useGetTemplateUiContractApiV1HubRedaccionTemplateVersionsVersionIdUiContractGet as useGetTemplateUiContract,
} from '@/shared/api/generated/hub-redaccion/hub-redaccion'
import { useRunWorkspace, useUploadWorkspaceInput } from '@/shared/api/generated/redaccion-workspaces/redaccion-workspaces'

/**
 * VER.4 — la pantalla donde se trabaja un informe.
 *
 * El módulo sabía crear workspaces y **no tenía dónde abrirlos**: `WorkspaceEditor`,
 * `DynamicUploadSlots`, `AIBlockReviewPanel` y `DataQualityPanel` existían desde 9R sin que
 * ninguna ruta los montara. `App.tsx` solo enrutaba la vista de impresión.
 *
 * El formulario de entrada se construye desde el `ui_contract` de la versión de plantilla,
 * no desde campos fijos: es la regla maestra nº1 del proyecto.
 */
vi.mock('@/shared/api/generated/hub-redaccion/hub-redaccion', () => ({
  useGetWorkspaceById: vi.fn(),
  useGetTemplateUiContractApiV1HubRedaccionTemplateVersionsVersionIdUiContractGet: vi.fn(),
  getGetWorkspaceByIdQueryKey: vi.fn(() => ['workspace']),
  // Los usan los paneles que la página compone.
  useGetWorkspaceWarnings: vi.fn(() => ({ data: [], isLoading: false })),
  usePatchWorkspaceBlock: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))
vi.mock('@/shared/api/generated/redaccion-workspaces/redaccion-workspaces', () => ({
  useRunWorkspace: vi.fn(),
  useUploadWorkspaceInput: vi.fn(),
  useApproveBlock: vi.fn(),
  // SEG.4 — el panel de revisión ya edita, y editar es una mutación más de este módulo.
  useEditBlock: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRejectBlock: vi.fn(),
  useRegenerateBlock: vi.fn(),
}))

const WORKSPACE_ID = '11111111-1111-1111-1111-111111111111'
const VERSION_ID = '22222222-2222-2222-2222-222222222222'

const CONTRATO = {
  wizard_steps: [{ id: 's1', title: 'Datos', order: 1, block_ids: ['b_datos'] }],
  dropzones: [{
    slot_id: 'datos_excel',
    label: { es: 'Datos presupuestarios', ca: 'Dades', en: 'Data' },
    accept: ['.xlsx'], multiple: false, max_size_mb: null,
  }],
  manual_fields: [{
    slot_id: 'periodo',
    label: { es: 'Periodo', ca: 'Període', en: 'Period' },
    field_type: 'text', placeholder: {}, required: true,
  }],
  block_editor_enabled: true,
  ai_review_panel_enabled: true,
  preview_layout: 'markdown',
}

const WORKSPACE = {
  id: WORKSPACE_ID,
  template_version_id: VERSION_ID,
  status: 'draft',
  blocks: [
    { block_id: 'b_datos', kind: 'DETERMINISTIC_DATA', status: 'draft' },
    { block_id: 'b_resumen', kind: 'AI_ASSISTED_TEXT', status: 'draft' },
  ],
  created_at: '2026-08-17T00:00:00Z',
  updated_at: '2026-08-17T00:00:00Z',
}

const runMutate = vi.fn()

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useRunWorkspace).mockReturnValue({ mutate: runMutate, isPending: false } as any)
  vi.mocked(useUploadWorkspaceInput).mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({}), isPending: false,
  } as any)
})

function renderPage(workspace: object | undefined = WORKSPACE, contrato: object | undefined = CONTRATO) {
  vi.mocked(useGetWorkspaceById).mockReturnValue({ data: workspace, isLoading: false } as any)
  vi.mocked(useGetTemplateUiContract).mockReturnValue({ data: contrato, isLoading: false } as any)

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/redaccion/workspaces/${WORKSPACE_ID}`]}>
        <Routes>
          <Route path="/redaccion/workspaces/:id" element={<WorkspacePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('WorkspacePage', () => {
  it('should_build_the_input_form_from_the_contract_and_not_from_fixed_fields', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByLabelText(/datos presupuestarios/i)).toBeDefined()
      expect(screen.getByLabelText(/periodo/i)).toBeDefined()
    })
  })

  it('should_show_the_blocks_of_the_report', async () => {
    renderPage()

    await waitFor(() => expect(screen.getByTestId('workspace-editor')).toBeDefined())
  })

  it('should_let_the_user_generate_the_report', async () => {
    renderPage()

    const boton = await screen.findByTestId('btn-generar-informe')
    fireEvent.click(boton)

    expect(runMutate).toHaveBeenCalledWith(
      expect.objectContaining({ workspaceId: WORKSPACE_ID }),
      expect.anything(),
    )
  })

  it('should_say_when_the_generation_failed_instead_of_looking_idle', async () => {
    renderPage({ ...WORKSPACE, status: 'error' })

    expect(await screen.findByTestId('workspace-error')).toBeDefined()
  })

  it('should_offer_the_preview_once_there_is_something_to_preview', async () => {
    renderPage({ ...WORKSPACE, status: 'in_review' })

    const enlace = await screen.findByRole('link', { name: /vista previa/i })
    expect(enlace.getAttribute('href')).toBe(`/redaccion/workspaces/${WORKSPACE_ID}/preview`)
  })

  it('should_not_offer_the_preview_before_generating', async () => {
    renderPage()

    expect(screen.queryByRole('link', { name: /vista previa/i })).toBeNull()
  })
})
