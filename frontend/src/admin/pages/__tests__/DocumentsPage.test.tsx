import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DocumentsPage } from '../DocumentsPage'
import * as ingestionApi from '@/shared/api/ingestion'
import * as chatbotsApi from '@/shared/api/chatbots'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, defaultText?: string) => defaultText || _key,
    i18n: { changeLanguage: vi.fn() },
  }),
}))

vi.mock('lucide-react', () => ({
  UploadCloud: () => <div data-testid="upload-icon" />,
  Trash2: () => <div data-testid="trash-icon" />,
  FileText: () => <div data-testid="file-icon" />,
  AlertCircle: () => <div data-testid="alert-icon" />,
  CheckCircle2: () => <div data-testid="check-icon" />,
  Clock: () => <div data-testid="clock-icon" />,
  Loader2: () => <div data-testid="loader-icon" />,
  Link: () => <div data-testid="link-icon" />,
  Globe: () => <div data-testid="globe-icon" />,
  Play: () => <div data-testid="play-icon" />,
  Pause: () => <div data-testid="pause-icon" />,
  RefreshCw: () => <div data-testid="refresh-icon" />,
  Eye: () => <div data-testid="eye-icon" />,
  FileUp: () => <div data-testid="file-up-icon" />,
  ChevronDown: () => <div data-testid="chevron-down" />,
  ChevronUp: () => <div data-testid="chevron-up" />,
  Upload: () => <div data-testid="upload-subst-icon" />,
}))

vi.mock('react-dropzone', () => ({
  useDropzone: () => ({
    getRootProps: () => ({}),
    getInputProps: () => ({ type: 'file', accept: 'application/pdf,.pdf' }),
    isDragActive: false,
  }),
}))

vi.mock('@/shared/api/chatbots', () => ({
  fetchChatbots: vi.fn(),
}))

vi.mock('@/shared/api/ingestion', () => ({
  fetchDocuments: vi.fn(),
  fetchDocument: vi.fn(),
  deleteDocument: vi.fn(),
  fetchIngestionJobs: vi.fn(),
  uploadDocument: vi.fn(),
  deleteJob: vi.fn(),
  clearCollection: vi.fn(),
  fetchSources: vi.fn(),
  createSource: vi.fn(),
  updateSource: vi.fn(),
  deleteSource: vi.fn(),
  triggerSourceCheck: vi.fn(),
}))

vi.mock('@/components/ui/progress', () => ({
  Progress: () => <div data-testid="progress" />,
}))

const CHATBOT = {
  id: 'bot-1',
  name: 'Bot Test',
  client_id: 'client-1',
  llm_config_id: 'llm-1',
  system_prompt: '',
  sources: [],
  is_active: true,
  retrieval_mode: 'vector' as const,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const DOCS_ES_CA = [
  {
    id: 'doc-es',
    chatbot_id: 'bot-1',
    title: 'Normativa Española',
    canonical_url: 'https://example.com/normativa-es.pdf',
    language: 'es',
    source_kind: 'upload' as const,
    token_count: 1200,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'doc-ca',
    chatbot_id: 'bot-1',
    title: 'Normativa Catalana',
    canonical_url: 'https://example.com/normativa-ca.pdf',
    language: 'ca',
    source_kind: 'crawler' as const,
    token_count: 3500,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
]

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('DocumentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(chatbotsApi.fetchChatbots as any).mockResolvedValue([CHATBOT])
    ;(ingestionApi.fetchDocuments as any).mockResolvedValue(DOCS_ES_CA)
    ;(ingestionApi.fetchIngestionJobs as any).mockResolvedValue([])
    ;(ingestionApi.fetchSources as any).mockResolvedValue([])
  })

  it('should_list_documents_with_language_badge', async () => {
    render(<DocumentsPage />, { wrapper: createWrapper() })

    expect(await screen.findByText('Normativa Española')).toBeInTheDocument()
    expect(screen.getByText('Normativa Catalana')).toBeInTheDocument()
    // Language badges — may appear in multiple places (badge + filter option); just verify at least one
    expect(screen.getAllByText('ES').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('CA').length).toBeGreaterThanOrEqual(1)
  })

  it('should_filter_table_by_language', async () => {
    render(<DocumentsPage />, { wrapper: createWrapper() })
    await screen.findByText('Normativa Española')

    const select = screen.getByLabelText('Filtrar por idioma')
    fireEvent.change(select, { target: { value: 'es' } })

    expect(screen.getByText('Normativa Española')).toBeInTheDocument()
    expect(screen.queryByText('Normativa Catalana')).not.toBeInTheDocument()
  })

  it('should_show_two_versions_of_same_document_in_different_languages', async () => {
    const sameUrlDocs = [
      { ...DOCS_ES_CA[0], title: 'Normativa v2 ES', canonical_url: 'https://example.com/norm.pdf', language: 'es' },
      { ...DOCS_ES_CA[1], id: 'doc-ca-2', title: 'Normativa v2 CA', canonical_url: 'https://example.com/norm.pdf', language: 'ca' },
    ]
    ;(ingestionApi.fetchDocuments as any).mockResolvedValue(sameUrlDocs)

    render(<DocumentsPage />, { wrapper: createWrapper() })

    expect(await screen.findByText('Normativa v2 ES')).toBeInTheDocument()
    expect(screen.getByText('Normativa v2 CA')).toBeInTheDocument()
    expect(screen.getAllByText('ES').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('CA').length).toBeGreaterThanOrEqual(1)
  })

  it('should_show_source_kind_icon', async () => {
    render(<DocumentsPage />, { wrapper: createWrapper() })
    await screen.findByText('Normativa Española')

    // upload → FileText icon, crawler → Globe icon
    const fileIcons = screen.getAllByTestId('file-icon')
    const globeIcons = screen.getAllByTestId('globe-icon')
    expect(fileIcons.length).toBeGreaterThanOrEqual(1)
    expect(globeIcons.length).toBeGreaterThanOrEqual(1)
  })

  it('should_show_total_tokens_summary_banner', async () => {
    render(<DocumentsPage />, { wrapper: createWrapper() })
    await screen.findByText('Normativa Española')

    // Banner shows retrieval mode + total tokens (1200 + 3500 = 4700 → "4.7 k")
    expect(screen.getByText(/Modo de retrieval/i)).toBeInTheDocument()
    expect(screen.getByText(/Vectorial/i)).toBeInTheDocument()
    expect(screen.getByText(/4\.7 k tokens/i)).toBeInTheDocument()
  })

  it('should_open_preview_modal_on_view_action', async () => {
    ;(ingestionApi.fetchDocument as any).mockResolvedValue({
      ...DOCS_ES_CA[0],
      markdown_content: '# Normativa\n\nContenido de prueba.',
    })

    render(<DocumentsPage />, { wrapper: createWrapper() })
    await screen.findByText('Normativa Española')

    const eyeButtons = screen.getAllByTestId('eye-icon')
    fireEvent.click(eyeButtons[0].closest('button')!)

    // The <pre> contains the full markdown; use regex to match partial content
    expect(await screen.findByText(/# Normativa/)).toBeInTheDocument()
  })

  it('should_delete_document_with_confirm', async () => {
    ;(ingestionApi.deleteDocument as any).mockResolvedValue(undefined)

    render(<DocumentsPage />, { wrapper: createWrapper() })
    await screen.findByText('Normativa Española')

    // trash-icon[0] is "Limpiar colección"; trash-icon[1] is the first document row
    const trashButtons = screen.getAllByTestId('trash-icon')
    const firstDocTrash = trashButtons.find(
      el => el.closest('button')?.title === 'Eliminar documento'
    )
    expect(firstDocTrash).toBeDefined()
    fireEvent.click(firstDocTrash!.closest('button')!)

    const confirmDialog = await screen.findByText('¿Eliminar documento?')
    expect(confirmDialog).toBeInTheDocument()

    fireEvent.click(screen.getByText('Sí, eliminar'))

    await waitFor(() => {
      expect(ingestionApi.deleteDocument).toHaveBeenCalledWith('bot-1', 'doc-es')
    })
  })

  it('should_keep_sources_tab_unchanged', async () => {
    ;(ingestionApi.fetchSources as any).mockResolvedValue([
      {
        id: 'src-1',
        chatbot_id: 'bot-1',
        url: 'https://example.com/feed',
        label: 'Feed principal',
        check_interval_hours: 24,
        last_checked_at: null,
        last_content_hash: null,
        status: 'active',
        error_message: null,
        created_at: '2024-01-01T00:00:00Z',
      },
    ])

    render(<DocumentsPage />, { wrapper: createWrapper() })
    await screen.findByText('Normativa Española')

    fireEvent.click(screen.getByText('Fuentes web'))

    expect(await screen.findByText('https://example.com/feed')).toBeInTheDocument()
    expect(screen.getByText('Añadir fuente web')).toBeInTheDocument()
  })
})
