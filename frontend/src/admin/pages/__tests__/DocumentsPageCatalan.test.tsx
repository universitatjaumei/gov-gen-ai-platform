import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DocumentsPage } from '../DocumentsPage'
import {
  useListDocumentsApiV1HubIngestionChatbotIdDocumentsGet,
  useGetDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdGet,
  useDeleteDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdDelete,
  useGetIngestionJobsApiV1HubIngestionChatbotIdJobsGet,
  useDeleteIngestionJobApiV1HubIngestionChatbotIdJobsJobIdDelete,
  useUploadDocumentApiV1HubIngestionUploadPost,
  useClearChatbotCollectionApiV1HubIngestionChatbotIdChunksDelete,
} from '@/shared/api/generated/hub-ingestion/hub-ingestion'
import {
  useListChatbotsApiV1HubChatbotsGet,
  useRecalculateCorpusEndpointApiV1HubChatbotsChatbotIdRecalculateCorpusPost,
} from '@/shared/api/generated/hub-chatbots/hub-chatbots'
import type { HubDocumentOut } from '@/shared/api/generated/model'

/**
 * CAL.4.1 — la pantalla de documentos, entera en catalán.
 *
 * Antes de este prompt, sus etiquetas vivían como *default* dentro de la llamada a t() con un
 * texto castellano, así que con i18nextLng=ca la navegación salía en catalán y el cuerpo se
 * quedaba en castellano.
 * El doble resuelve contra el diccionario catalán real (no contra 'es' como el resto de tests
 * de esta pantalla): si una clave no está en ca/admin.json, aquí aparece el texto castellano
 * del default o la propia clave, no el texto catalán esperado.
 */
vi.mock('react-i18next', async () => {
  const ca = (await import('@/shared/i18n/locales/ca/admin.json')).default as Record<string, unknown>
  const resolver = (clave: string) =>
    clave.split('.').reduce<unknown>((o, p) => (o as Record<string, unknown>)?.[p], ca)
  return {
    useTranslation: () => ({
      t: (key: string, defaultText?: string) => (resolver(key) as string) ?? defaultText ?? key,
      i18n: { changeLanguage: vi.fn() },
    }),
  }
})

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

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useListChatbotsApiV1HubChatbotsGet: vi.fn(),
  useRecalculateCorpusEndpointApiV1HubChatbotsChatbotIdRecalculateCorpusPost: vi.fn(),
  getListChatbotsApiV1HubChatbotsGetQueryKey: vi.fn(() => ['/api/v1/hub/chatbots']),
}))

vi.mock('@/shared/api/generated/hub-ingestion/hub-ingestion', () => ({
  useListDocumentsApiV1HubIngestionChatbotIdDocumentsGet: vi.fn(),
  useGetDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdGet: vi.fn(),
  useDeleteDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdDelete: vi.fn(),
  useGetIngestionJobsApiV1HubIngestionChatbotIdJobsGet: vi.fn(),
  useDeleteIngestionJobApiV1HubIngestionChatbotIdJobsJobIdDelete: vi.fn(),
  useUploadDocumentApiV1HubIngestionUploadPost: vi.fn(),
  useClearChatbotCollectionApiV1HubIngestionChatbotIdChunksDelete: vi.fn(),
  getListDocumentsApiV1HubIngestionChatbotIdDocumentsGetQueryKey: vi.fn(
    (id: string) => [`/api/v1/hub/ingestion/${id}/documents`],
  ),
  getGetIngestionJobsApiV1HubIngestionChatbotIdJobsGetQueryKey: vi.fn(
    (id: string) => [`/api/v1/hub/ingestion/${id}/jobs`],
  ),
}))

vi.mock('@/components/ui/progress', () => ({
  Progress: () => <div data-testid="progress" />,
}))

const CHATBOT = {
  id: 'bot-1',
  name: 'Bot Test',
  organizacion_id: 'client-1',
  llm_config_id: 'llm-1',
  system_prompt: '',
  sources: [],
  is_active: true,
  retrieval_mode: 'vector' as const,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const DOC: HubDocumentOut = {
  id: 'doc-es',
  chatbot_id: 'bot-1',
  title: 'Normativa Española',
  canonical_url: 'https://example.com/normativa-es.pdf',
  language: 'es',
  source_kind: 'upload',
  token_count: 1200,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const mutationDouble = (mutate = vi.fn()) => ({ mutate, isPending: false }) as any

const createWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('DocumentsPage en catalán (CAL.4.1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useListChatbotsApiV1HubChatbotsGet).mockReturnValue({ data: [CHATBOT] } as any)
    vi.mocked(useListDocumentsApiV1HubIngestionChatbotIdDocumentsGet).mockReturnValue({
      data: { documents: [DOC] },
      isLoading: false,
    } as any)
    vi.mocked(useGetDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdGet).mockReturnValue({
      data: undefined,
      isLoading: false,
    } as any)
    vi.mocked(useGetIngestionJobsApiV1HubIngestionChatbotIdJobsGet).mockReturnValue({
      data: { jobs: [] },
      isLoading: false,
    } as any)
    vi.mocked(useDeleteDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdDelete)
      .mockReturnValue(mutationDouble())
    vi.mocked(useRecalculateCorpusEndpointApiV1HubChatbotsChatbotIdRecalculateCorpusPost)
      .mockReturnValue(mutationDouble())
    vi.mocked(useDeleteIngestionJobApiV1HubIngestionChatbotIdJobsJobIdDelete)
      .mockReturnValue(mutationDouble())
    vi.mocked(useUploadDocumentApiV1HubIngestionUploadPost).mockReturnValue(mutationDouble())
    vi.mocked(useClearChatbotCollectionApiV1HubIngestionChatbotIdChunksDelete)
      .mockReturnValue(mutationDouble())
  })

  it('should_render_documents_screen_in_catalan', async () => {
    render(<DocumentsPage />, { wrapper: createWrapper() })

    expect(await screen.findByText('Documents i Ingestió')).toBeInTheDocument()
    expect(screen.getByText('Gestiona la base de coneixement del chatbot.')).toBeInTheDocument()
    expect(screen.getByText('Documents del corpus')).toBeInTheDocument()
    // EXT.1: al corpus solo entra Markdown del pipeline de curación, no PDF.
    expect(
      screen.getByText('Arrossega i deixa anar els teus fitxers Markdown (.md) ací'),
    ).toBeInTheDocument()
    expect(screen.getByText('Jobs (tècnic)')).toBeInTheDocument()
    expect(screen.getByText('Recalcula el corpus')).toBeInTheDocument()
  })
})
