import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'

// ── Mock data hoisted ──────────────────────────────────────────────
const mockSites = vi.hoisted(() => ({ list: [] as object[] }))
const mockFindings = vi.hoisted(() => ({ list: [] as object[] }))
const mockCandidates = vi.hoisted(() => ({ list: [] as object[] }))
const mockReport = vi.hoisted(() => ({ data: null as object | null }))

vi.mock('@/shared/api/generated/hub-sites/hub-sites', () => ({
  useListSites: vi.fn(() => ({ data: mockSites.list, isLoading: false })),
  useCreateSite: vi.fn(() => ({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false })),
  useDeleteSite: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useTriggerSiteCrawl: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useListSelections: vi.fn(() => ({ data: [], isLoading: false })),
  useCreateSelection: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useDeleteSelection: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useListCandidates: vi.fn(() => ({ data: mockCandidates.list, isLoading: false })),
  useIngestPage: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRetirePage: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  getListSitesQueryKey: vi.fn(() => ['listSites']),
  getListSelectionsQueryKey: vi.fn(() => ['listSelections']),
  getListCandidatesQueryKey: vi.fn(() => ['listCandidates']),
}))

vi.mock('@/shared/api/generated/hub-content-quality/hub-content-quality', () => ({
  useListSiteFindings: vi.fn(() => ({ data: mockFindings.list, isLoading: false })),
  useTransitionFinding: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useAnalyzeSite: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useGetSiteQualityReport: vi.fn(() => ({ data: mockReport.data, isLoading: false })),
  getListSiteFindingsQueryKey: vi.fn(() => ['listSiteFindings']),
}))

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useListChatbotsApiV1HubChatbotsGet: vi.fn(() => ({ data: [], isLoading: false })),
}))

const TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
})

afterEach(() => {
  vi.clearAllMocks()
  mockSites.list = []
  mockFindings.list = []
  mockCandidates.list = []
  mockReport.data = null
})

const SITE = {
  id: 'site-001',
  name: 'Portal Institucional',
  root_url: 'https://ej.es',
  sitemap_url: null,
  spider_type: 'generic',
  crawl_interval_hours: 24,
  audit_semantic_scope: 'ingested',
  last_crawled_at: null,
  status: 'active',
  created_at: '2026-06-06T00:00:00Z',
  organizacion_id: null,
}

const FINDING = {
  id: 'finding-001',
  site_id: 'site-001',
  finding_type: 'stale',
  severity: 'info',
  status: 'new',
  confidence: 1.0,
  source_url: 'https://ej.es/tramites/2020',
  detected_at: '2026-06-06T00:00:00Z',
  reviewed_at: null,
}

function wrap(element: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{element}</MemoryRouter>
    </QueryClientProvider>
  )
}

// ── SitesPage ─────────────────────────────────────────────────────

describe('SitesPage', () => {
  it('muestra la lista de sitios', async () => {
    mockSites.list = [SITE]
    const { SitesPage } = await import('../SitesPage')
    render(wrap(<SitesPage />))
    await waitFor(() => {
      expect(screen.getByText('Portal Institucional')).toBeTruthy()
    })
  })

  it('"Rastrear ahora" invoca useTriggerSiteCrawl', async () => {
    const { useTriggerSiteCrawl } = await import('@/shared/api/generated/hub-sites/hub-sites')
    const mutateFn = vi.fn()
    ;(useTriggerSiteCrawl as ReturnType<typeof vi.fn>).mockReturnValue({ mutate: mutateFn, isPending: false })

    mockSites.list = [SITE]
    const { SitesPage } = await import('../SitesPage')
    render(wrap(<SitesPage />))

    const crawlBtn = await screen.findAllByText(/rastrear ahora/i)
    fireEvent.click(crawlBtn[0])

    expect(mutateFn).toHaveBeenCalledWith({ siteId: SITE.id })
  })

  it('muestra formulario al pulsar "Nuevo sitio"', async () => {
    const { SitesPage } = await import('../SitesPage')
    render(wrap(<SitesPage />))

    fireEvent.click(screen.getByText(/nuevo sitio/i))
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeTruthy()
    })
  })
})

// ── ContentQualityPage ────────────────────────────────────────────

describe('ContentQualityPage', () => {
  it('renderiza el selector de sitio', async () => {
    mockSites.list = [SITE]
    const { ContentQualityPage } = await import('../ContentQualityPage')
    render(wrap(<ContentQualityPage />))
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /seleccione un sitio/i })).toBeTruthy()
    })
  })

  it('tabla de hallazgos renderiza badge de severidad correcto', async () => {
    mockSites.list = [SITE]
    mockFindings.list = [FINDING]

    const { useListSiteFindings } = await import('@/shared/api/generated/hub-content-quality/hub-content-quality')
    ;(useListSiteFindings as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockFindings.list, isLoading: false,
    })

    const { ContentQualityPage } = await import('../ContentQualityPage')
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <ContentQualityPage />
        </MemoryRouter>
      </QueryClientProvider>
    )

    // Seleccionar sitio para mostrar hallazgos
    const selector = screen.getByRole('combobox', { name: /seleccione un sitio/i })
    fireEvent.change(selector, { target: { value: SITE.id } })

    await waitFor(() => {
      // El badge de severidad "Info" debe aparecer en la tabla de hallazgos
      const badges = screen.getAllByText(/^info$/i)
      expect(badges.length).toBeGreaterThan(0)
    })
  })

  it('"Analizar ahora" invoca useAnalyzeSite', async () => {
    const { useAnalyzeSite } = await import('@/shared/api/generated/hub-content-quality/hub-content-quality')
    const mutateFn = vi.fn()
    ;(useAnalyzeSite as ReturnType<typeof vi.fn>).mockReturnValue({ mutate: mutateFn, isPending: false })

    mockSites.list = [SITE]
    const { ContentQualityPage } = await import('../ContentQualityPage')
    render(wrap(<ContentQualityPage />))

    const selector = screen.getByRole('combobox', { name: /seleccione un sitio/i })
    fireEvent.change(selector, { target: { value: SITE.id } })

    const analyzeBtn = screen.getByText(/analizar ahora/i)
    fireEvent.click(analyzeBtn)

    expect(mutateFn).toHaveBeenCalledWith({ siteId: SITE.id })
  })

  it('Confirmar invoca useTransitionFinding', async () => {
    mockSites.list = [SITE]
    mockFindings.list = [FINDING]

    const { useListSiteFindings, useTransitionFinding } = await import('@/shared/api/generated/hub-content-quality/hub-content-quality')
    const mutateFn = vi.fn()
    ;(useTransitionFinding as ReturnType<typeof vi.fn>).mockReturnValue({ mutate: mutateFn, isPending: false })
    ;(useListSiteFindings as ReturnType<typeof vi.fn>).mockReturnValue({ data: mockFindings.list, isLoading: false })

    const { ContentQualityPage } = await import('../ContentQualityPage')
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter><ContentQualityPage /></MemoryRouter>
      </QueryClientProvider>
    )

    const selector = screen.getByRole('combobox', { name: /seleccione un sitio/i })
    fireEvent.change(selector, { target: { value: SITE.id } })

    await waitFor(() => {
      expect(screen.getByText(/confirmar/i)).toBeTruthy()
    })
    fireEvent.click(screen.getByText(/confirmar/i))

    expect(mutateFn).toHaveBeenCalledWith({
      siteId: SITE.id,
      findingId: FINDING.id,
      data: { new_status: 'confirmed' },
    })
  })
})

// ── WebQualityReportViewer ────────────────────────────────────────

describe('WebQualityReportViewer', () => {
  it('muestra totales del informe y el nombre del sitio', async () => {
    const REPORT = {
      site_id: 'site-001',
      site_name: 'Portal Institucional',
      generated_at: '2026-06-06T12:00:00Z',
      totals_by_type: { stale: 3, empty: 1 },
      totals_by_severity: { info: 3, critical: 1 },
      sections: [],
    }

    const { useGetSiteQualityReport } = await import('@/shared/api/generated/hub-content-quality/hub-content-quality')
    ;(useGetSiteQualityReport as ReturnType<typeof vi.fn>).mockReturnValue({ data: REPORT, isLoading: false })

    const { WebQualityReportViewer } = await import('../WebQualityReportViewer')
    render(wrap(<WebQualityReportViewer siteId="site-001" />))

    await waitFor(() => {
      expect(screen.getByText(/Portal Institucional/)).toBeTruthy()
      // Hay al menos un elemento con el texto "Desactualizada" (type_stale)
      expect(screen.getByText(/desactualizada/i)).toBeTruthy()
    })
  })

  it('muestra mensaje vacío si no hay hallazgos', async () => {
    const EMPTY_REPORT = {
      site_id: 'site-001',
      site_name: 'Portal',
      generated_at: '2026-06-06T12:00:00Z',
      totals_by_type: {},
      totals_by_severity: {},
      sections: [],
    }

    const { useGetSiteQualityReport } = await import('@/shared/api/generated/hub-content-quality/hub-content-quality')
    ;(useGetSiteQualityReport as ReturnType<typeof vi.fn>).mockReturnValue({ data: EMPTY_REPORT, isLoading: false })

    const { WebQualityReportViewer } = await import('../WebQualityReportViewer')
    render(wrap(<WebQualityReportViewer siteId="site-001" />))

    await waitFor(() => {
      expect(screen.getByText(/sin hallazgos/i)).toBeTruthy()
    })
  })

  it('muestra botones de descarga DOCX y PDF', async () => {
    const REPORT = {
      site_id: 'site-001',
      site_name: 'Portal',
      generated_at: '2026-06-06T12:00:00Z',
      totals_by_type: { stale: 1 },
      totals_by_severity: { info: 1 },
      sections: [],
    }

    const { useGetSiteQualityReport } = await import('@/shared/api/generated/hub-content-quality/hub-content-quality')
    ;(useGetSiteQualityReport as ReturnType<typeof vi.fn>).mockReturnValue({ data: REPORT, isLoading: false })

    const { WebQualityReportViewer } = await import('../WebQualityReportViewer')
    render(wrap(<WebQualityReportViewer siteId="site-001" />))

    await waitFor(() => {
      expect(screen.getByText(/descargar docx/i)).toBeTruthy()
      expect(screen.getByText(/descargar pdf/i)).toBeTruthy()
    })
  })
})
