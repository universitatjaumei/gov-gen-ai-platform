import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { GenericReportWizard } from '../pages/GenericReportWizard'
import {
  useListTemplates,
  useCreateWorkspace,
} from '@/shared/api/generated/hub-redaccion/hub-redaccion'

/**
 * VER.4 — crear el informe tiene que llevar al informe.
 *
 * El asistente lanzaba la mutación y no hacía nada más: el workspace se creaba en la base y
 * en pantalla no cambiaba nada, así que era indistinguible de un botón roto. Ahora que existe
 * la pantalla del workspace, hay sitio al que ir.
 */
vi.mock('@/shared/api/generated/hub-redaccion/hub-redaccion', () => ({
  useListTemplates: vi.fn(),
  useCreateWorkspace: vi.fn(),
}))

const PLANTILLA = {
  id: 'tpl-1',
  name: 'Informe presupuestario',
  report_profile: 'GENERIC_REPORT',
  current_version_id: 'ver-1',
}
const WORKSPACE_ID = '33333333-3333-3333-3333-333333333333'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useListTemplates).mockReturnValue({ data: [PLANTILLA], isLoading: false } as any)
})

function renderWizard(mutate: ReturnType<typeof vi.fn>) {
  vi.mocked(useCreateWorkspace).mockReturnValue({ mutate, isPending: false } as any)

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/redaccion/wizard']}>
        <Routes>
          <Route path="/redaccion/wizard" element={<GenericReportWizard />} />
          <Route
            path="/redaccion/workspaces/:id"
            element={<div data-testid="pantalla-del-informe" />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('GenericReportWizard', () => {
  it('should_open_the_workspace_it_just_created', async () => {
    const mutate = vi.fn((_vars, opciones) => {
      opciones?.onSuccess?.({ workspace_id: WORKSPACE_ID })
    })
    renderWizard(mutate)

    fireEvent.click(screen.getByTestId('btn-create-workspace-tpl-1'))

    await waitFor(() =>
      expect(screen.getByTestId('pantalla-del-informe')).toBeDefined()
    )
  })
})
