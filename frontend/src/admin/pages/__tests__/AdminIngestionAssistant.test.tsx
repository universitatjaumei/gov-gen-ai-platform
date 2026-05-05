import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AdminIngestionAssistant } from '../AdminIngestionAssistant'
import * as ingestionApi from '@/shared/api/ingestion'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, defaultText?: string) => defaultText || _key,
    i18n: { changeLanguage: vi.fn() },
  }),
}))

vi.mock('@/shared/api/ingestion', () => ({
  analyzeHtml: vi.fn(),
  createSource: vi.fn(),
}))

const MOCK_ANALYSIS: ingestionApi.AnalysisResult = {
  proposed_selectors: {
    content: 'article.entry-content',
    title: 'h1.page-title',
    date: null,
  },
  confidence: 0.67,
  sample_extraction: {
    content: 'El presente reglamento regula los estudios de doctorado.',
    title: 'Reglamento de Doctorado',
  },
}

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('AdminIngestionAssistant', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should_disable_save_button_until_preview_is_shown', () => {
    render(<AdminIngestionAssistant chatbotId="bot-1" />, { wrapper: createWrapper() })

    const saveButton = screen.getByRole('button', { name: /guardar fuente/i })
    expect(saveButton).toBeDisabled()
  })

  it('should_enable_save_button_after_analyze_response_is_rendered', async () => {
    ;(ingestionApi.analyzeHtml as any).mockResolvedValue(MOCK_ANALYSIS)

    render(<AdminIngestionAssistant chatbotId="bot-1" />, { wrapper: createWrapper() })

    fireEvent.change(screen.getByLabelText(/html de la página/i), {
      target: { value: '<html><body><h1>Test</h1></body></html>' },
    })

    fireEvent.click(screen.getByRole('button', { name: /analizar/i }))

    await waitFor(() => {
      expect(screen.getByText(/selectores propuestos/i)).toBeInTheDocument()
    })

    expect(screen.getByRole('button', { name: /guardar fuente/i })).not.toBeDisabled()
  })

  it('should_call_analyze_endpoint_with_pasted_html', async () => {
    ;(ingestionApi.analyzeHtml as any).mockResolvedValue(MOCK_ANALYSIS)

    render(<AdminIngestionAssistant chatbotId="bot-1" />, { wrapper: createWrapper() })

    const htmlTextarea = screen.getByLabelText(/html de la página/i)
    fireEvent.change(htmlTextarea, { target: { value: '<html>test content</html>' } })

    fireEvent.change(screen.getByLabelText(/url de la fuente/i), {
      target: { value: 'https://www.uji.es/normativa' },
    })

    fireEvent.click(screen.getByRole('button', { name: /analizar/i }))

    await waitFor(() => {
      expect(ingestionApi.analyzeHtml).toHaveBeenCalledWith(
        '<html>test content</html>',
        'https://www.uji.es/normativa',
      )
    })
  })

  it('should_persist_proposed_selectors_on_save_click', async () => {
    ;(ingestionApi.analyzeHtml as any).mockResolvedValue(MOCK_ANALYSIS)
    ;(ingestionApi.createSource as any).mockResolvedValue({
      id: 'src-new',
      chatbot_id: 'bot-1',
      url: 'https://www.uji.es/normativa',
      label: null,
      check_interval_hours: 24,
      last_checked_at: null,
      last_content_hash: null,
      status: 'active',
      error_message: null,
      created_at: '2026-05-05T00:00:00Z',
    })

    render(<AdminIngestionAssistant chatbotId="bot-1" />, { wrapper: createWrapper() })

    fireEvent.change(screen.getByLabelText(/url de la fuente/i), {
      target: { value: 'https://www.uji.es/normativa' },
    })
    fireEvent.change(screen.getByLabelText(/html de la página/i), {
      target: { value: '<html>test</html>' },
    })

    fireEvent.click(screen.getByRole('button', { name: /analizar/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /guardar fuente/i })).not.toBeDisabled()
    })

    fireEvent.click(screen.getByRole('button', { name: /guardar fuente/i }))

    await waitFor(() => {
      expect(ingestionApi.createSource).toHaveBeenCalledWith(
        'bot-1',
        expect.objectContaining({
          url: 'https://www.uji.es/normativa',
          config_json: expect.objectContaining({
            proposed_selectors: MOCK_ANALYSIS.proposed_selectors,
          }),
        }),
      )
    })
  })
})
