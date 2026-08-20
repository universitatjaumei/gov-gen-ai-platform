import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { LLMDraftPreviewPage } from '../pages/LLMDraftPreviewPage'
import {
  useProposeLlmDraft,
  useValidateLlmDraft,
  useApproveAsTemplate,
  useApproveAsWorkspace,
  useDescribeSampleFile,
} from '@/shared/api/generated/redaccion-llm-drafts/redaccion-llm-drafts'

/**
 * INF.4 — el fichero de datos se ofrece antes del prompt, y lo que se va a enviar se ve.
 *
 * `propose` recibía solo el texto, así que el modelo no conocía las columnas y las adivinaba.
 * El legacy sí mandaba la estructura, anonimizada (`etl_factory`).
 */
vi.mock('@/shared/api/generated/redaccion-llm-drafts/redaccion-llm-drafts', () => ({
  useProposeLlmDraft: vi.fn(),
  useValidateLlmDraft: vi.fn(),
  useApproveAsTemplate: vi.fn(),
  useApproveAsWorkspace: vi.fn(),
  useDescribeSampleFile: vi.fn(),
}))
vi.mock('@/shared/auth', () => ({
  useAuth: () => ({ user: { role: 'superadmin', email: 'x@uji.es', user_id: '1' } }),
}))

const MUESTRA = {
  nombre_del_fichero: 'saldos.csv',
  columnas: ['ccc', 'periodo', 'saldo'],
  tipos: { ccc: 'object', periodo: 'object', saldo: 'object' },
  filas_totales: 412,
  primeras_filas: [{ ccc: '0001', periodo: '202601', saldo: '1.234,56' }],
}

const proponer = vi.fn()
const describir = vi.fn()

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useProposeLlmDraft).mockReturnValue({ mutate: proponer, isPending: false } as never)
  vi.mocked(useValidateLlmDraft).mockReturnValue({ mutate: vi.fn(), isPending: false } as never)
  vi.mocked(useApproveAsTemplate).mockReturnValue({ mutate: vi.fn(), isPending: false } as never)
  vi.mocked(useApproveAsWorkspace).mockReturnValue({ mutate: vi.fn(), isPending: false } as never)
  vi.mocked(useDescribeSampleFile).mockReturnValue({ mutate: describir, isPending: false } as never)
})

function pintar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <LLMDraftPreviewPage />
    </QueryClientProvider>,
  )
}

describe('INF.4 — la propuesta ve los datos', () => {
  it('should_offer_the_data_file_before_the_prompt', () => {
    pintar()
    expect(screen.getByTestId('input-muestra')).toBeDefined()
  })

  it('should_send_the_file_to_the_server_to_be_summarised_and_anonymised', async () => {
    pintar()

    const fichero = new File(['ccc,saldo\n1,2\n'], 'saldos.csv', { type: 'text/csv' })
    fireEvent.change(screen.getByTestId('input-muestra'), { target: { files: [fichero] } })

    await waitFor(() =>
      expect(describir).toHaveBeenCalledWith(
        expect.objectContaining({ data: { file: fichero } }),
        expect.anything(),
      ),
    )
  })

  it('should_show_what_is_going_to_be_sent', async () => {
    describir.mockImplementation((_v: unknown, o: { onSuccess?: (m: unknown) => void }) =>
      o?.onSuccess?.(MUESTRA),
    )
    pintar()

    fireEvent.change(screen.getByTestId('input-muestra'), {
      target: { files: [new File(['x'], 'saldos.csv')] },
    })

    const resumen = await screen.findByTestId('resumen-de-muestra')
    expect(resumen.textContent).toMatch(/saldos\.csv/)
    expect(resumen.textContent).toMatch(/412/)
    expect(resumen.textContent).toMatch(/ccc/)
  })

  it('should_include_the_sample_in_the_proposal_request', async () => {
    describir.mockImplementation((_v: unknown, o: { onSuccess?: (m: unknown) => void }) =>
      o?.onSuccess?.(MUESTRA),
    )
    pintar()

    fireEvent.change(screen.getByTestId('input-muestra'), {
      target: { files: [new File(['x'], 'saldos.csv')] },
    })
    await screen.findByTestId('resumen-de-muestra')

    fireEvent.change(screen.getByTestId('input-prompt'), {
      target: { value: 'Informe de tesoreria por ano y mes' },
    })
    fireEvent.click(screen.getByTestId('btn-propose'))

    await waitFor(() =>
      expect(proponer).toHaveBeenCalledWith(
        expect.objectContaining({ data: expect.objectContaining({ muestra: MUESTRA }) }),
      ),
    )
  })

  it('should_still_propose_without_a_file', async () => {
    pintar()

    fireEvent.change(screen.getByTestId('input-prompt'), { target: { value: 'Un informe' } })
    fireEvent.click(screen.getByTestId('btn-propose'))

    await waitFor(() =>
      expect(proponer).toHaveBeenCalledWith(
        expect.objectContaining({ data: expect.objectContaining({ muestra: null }) }),
      ),
    )
  })
})
