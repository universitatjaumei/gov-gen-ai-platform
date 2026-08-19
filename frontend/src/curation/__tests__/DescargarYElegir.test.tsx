import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'

/**
 * La descarga y la selección (CUR.5).
 *
 * Dos botones que no funcionaban. El de descargar el informe es un `<a href download>` **sin
 * cabecera de autorización**: el servidor responde 401 y el navegador enseña su propio error de
 * descarga. Y en publicación no se podía elegir: «aparece Regla - Nueva y un icono de validación,
 * pero no pueden desmarcarse algunas. Convendría que se pudiera elegir».
 *
 * Marcar no es «ingerir todo»: cada página sigue entrando al corpus porque alguien la marcó. Lo que
 * desaparece es tener que pulsar trescientas veces para publicar un apartado.
 */

const SITIO = 's1'

const INFORME = {
  site_id: SITIO,
  site_name: 'Escola de Doctorat',
  generated_at: '2026-08-19T10:00:00Z',
  totals_by_type: { stale: 241 },
  totals_by_severity: { info: 241 },
  sections: [
    {
      finding_type: 'stale',
      recommendation: 'Revisar',
      findings: [{ id: 'f1', page_url: 'https://www.uji.es/a', related_page_url: null }],
    },
  ],
}

vi.mock('@/shared/api/download', () => ({ descargarConAutorizacion: vi.fn().mockResolvedValue(undefined) }))

vi.mock('@/shared/api/generated/hub-content-quality/hub-content-quality', () => ({
  useGetSiteQualityReport: () => ({ data: INFORME, isLoading: false }),
}))

const mockCandidatas = vi.hoisted(() => ({ list: [] as object[] }))
const mockIngerir = vi.hoisted(() => ({ mutate: vi.fn() }))

vi.mock('@/shared/api/generated/hub-sites/hub-sites', () => ({
  useListSites: () => ({ data: [{ id: SITIO, name: 'Escola de Doctorat' }], isLoading: false }),
  useListSelections: () => ({ data: [], isLoading: false }),
  useCreateSelection: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteSelection: () => ({ mutate: vi.fn(), isPending: false }),
  useListCandidates: () => ({ data: mockCandidatas.list, isLoading: false }),
  useIngestPage: () => ({ mutate: mockIngerir.mutate, isPending: false }),
  useGetPageContent: () => ({ data: undefined, isLoading: false }),
  getListSelectionsQueryKey: () => ['sel'],
  getListCandidatesQueryKey: () => ['cand'],
}))

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useListChatbotsApiV1HubChatbotsGet: () => ({ data: [{ id: 'bot-1', name: 'Assistent' }] }),
}))

const SIN_INGERIR = { page_id: 'p1', url: 'https://www.uji.es/a', title: 'A', matched_rule: null, is_new: true, is_ingested: false }
const OTRA = { page_id: 'p2', url: 'https://www.uji.es/b', title: 'B', matched_rule: '/base/', is_new: false, is_ingested: false }
const YA_INGERIDA = { page_id: 'p3', url: 'https://www.uji.es/c', title: 'C', matched_rule: null, is_new: false, is_ingested: true }

function envolver(elemento: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{elemento}</MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.clearAllMocks()
  mockCandidatas.list = []
})

describe('la descarga del informe de auditoría', () => {
  it('no es un enlace: el fichero se pide con el token puesto', async () => {
    const { WebQualityReportViewer } = await import('../WebQualityReportViewer')
    const { descargarConAutorizacion } = await import('@/shared/api/download')
    envolver(<WebQualityReportViewer siteId={SITIO} />)

    // Un `<a href download>` es justo lo que no puede funcionar aquí.
    expect(screen.queryByRole('link', { name: /docx/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('btn-descargar-docx'))

    await waitFor(() =>
      expect(descargarConAutorizacion).toHaveBeenCalledWith(
        `/api/v1/hub/sites/${SITIO}/report/export?format=docx`,
        expect.stringContaining('.docx'),
      ),
    )
  })

  it('el PDF va por el mismo camino', async () => {
    const { WebQualityReportViewer } = await import('../WebQualityReportViewer')
    const { descargarConAutorizacion } = await import('@/shared/api/download')
    envolver(<WebQualityReportViewer siteId={SITIO} />)

    fireEvent.click(screen.getByTestId('btn-descargar-pdf'))

    await waitFor(() =>
      expect(descargarConAutorizacion).toHaveBeenCalledWith(
        `/api/v1/hub/sites/${SITIO}/report/export?format=pdf`,
        expect.stringContaining('.pdf'),
      ),
    )
  })

  it('si la descarga falla, se dice en pantalla en vez de no pasar nada', async () => {
    const { descargarConAutorizacion } = await import('@/shared/api/download')
    ;(descargarConAutorizacion as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('No hay informe'))

    const { WebQualityReportViewer } = await import('../WebQualityReportViewer')
    envolver(<WebQualityReportViewer siteId={SITIO} />)

    fireEvent.click(screen.getByTestId('btn-descargar-docx'))

    expect(await screen.findByTestId('error-descarga')).toBeInTheDocument()
  })
})

describe('elegir qué páginas se publican', () => {
  async function pantallaDePublicacion() {
    const { PublicationPage } = await import('../PublicationPage')
    envolver(<PublicationPage />)
    fireEvent.change(screen.getByRole('combobox', { name: /seleccione un sitio/i }), { target: { value: SITIO } })
    fireEvent.change(screen.getByRole('combobox', { name: /chatbot destino/i }), { target: { value: 'bot-1' } })
    // Por `data-testid` y no por el texto de la URL: la URL sale además en el `aria-label` de su
    // casilla, y esperar por texto ambiguo convierte la espera en un flake.
    await screen.findByTestId(`marca-${SIN_INGERIR.page_id}`)
  }

  it('se marca y se desmarca cada página', async () => {
    mockCandidatas.list = [SIN_INGERIR, OTRA]
    await pantallaDePublicacion()

    const casilla = screen.getByTestId('marca-p1') as HTMLInputElement
    expect(casilla.checked).toBe(false)

    fireEvent.click(casilla)
    expect((screen.getByTestId('marca-p1') as HTMLInputElement).checked).toBe(true)

    fireEvent.click(screen.getByTestId('marca-p1'))
    expect((screen.getByTestId('marca-p1') as HTMLInputElement).checked).toBe(false)
  })

  it('sólo se ingiere lo marcado', async () => {
    mockCandidatas.list = [SIN_INGERIR, OTRA]
    await pantallaDePublicacion()

    fireEvent.click(screen.getByTestId('marca-p2'))
    fireEvent.click(screen.getByTestId('btn-ingerir-marcadas'))

    expect(mockIngerir.mutate).toHaveBeenCalledTimes(1)
    expect(mockIngerir.mutate).toHaveBeenCalledWith({ chatbotId: 'bot-1', pageId: 'p2' })
  })

  it('sin nada marcado no hay nada que ingerir', async () => {
    mockCandidatas.list = [SIN_INGERIR, OTRA]
    await pantallaDePublicacion()

    expect(screen.getByTestId('btn-ingerir-marcadas')).toBeDisabled()
  })

  it('«marcar todo» marca lo que se puede publicar, y no lo que ya está en el corpus', async () => {
    mockCandidatas.list = [SIN_INGERIR, OTRA, YA_INGERIDA]
    await pantallaDePublicacion()

    fireEvent.click(screen.getByTestId('marca-todo'))

    expect((screen.getByTestId('marca-p1') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByTestId('marca-p2') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByTestId('marca-p3') as HTMLInputElement).disabled).toBe(true)

    fireEvent.click(screen.getByTestId('btn-ingerir-marcadas'))
    expect(mockIngerir.mutate).toHaveBeenCalledTimes(2)
  })

  it('una página que ya está en el corpus se ve como tal', async () => {
    mockCandidatas.list = [SIN_INGERIR, YA_INGERIDA]
    await pantallaDePublicacion()

    expect(screen.getByTestId('estado-corpus-p3').textContent).toMatch(/ingerida/i)
    expect(screen.getByTestId('estado-corpus-p1').textContent).not.toMatch(/ingerida/i)
  })

  it('dice cuántas hay marcadas: publicar 300 páginas sin saber cuántas son no es una decisión', async () => {
    mockCandidatas.list = [SIN_INGERIR, OTRA]
    await pantallaDePublicacion()

    fireEvent.click(screen.getByTestId('marca-todo'))

    expect(screen.getByTestId('btn-ingerir-marcadas').textContent).toContain('2')
  })
})
