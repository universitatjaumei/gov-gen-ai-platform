import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReportsPage } from '../ReportsPage'
import * as feedbackApi from '@/shared/api/feedback'
import { useListChatbotsApiV1HubChatbotsGet } from '@/shared/api/generated/hub-chatbots/hub-chatbots'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, def?: string) => def ?? key,
  }),
}))

vi.mock('lucide-react', () => ({
  Download: () => <div data-testid="download-icon" />,
  Star: () => <div data-testid="star-icon" />,
  ChevronDown: () => <div data-testid="chevron-down" />,
  ChevronUp: () => <div data-testid="chevron-up" />,
  Loader2: () => <div data-testid="loader-icon" />,
}))

vi.mock('recharts', () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  Cell: () => null,
}))

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useListChatbotsApiV1HubChatbotsGet: vi.fn(),
  getListChatbotsApiV1HubChatbotsGetQueryKey: vi.fn(() => ['/api/v1/hub/chatbots']),
}))
vi.mock('@/shared/api/feedback', () => ({ fetchInteractions: vi.fn() }))

const SAMPLE_INTERACTIONS: feedbackApi.Interaction[] = [
  {
    id: 'i-1',
    user_message: 'How does Python work?',
    assistant_message: 'Python is an interpreted language that runs on a virtual machine.',
    feedback_score: 4,
    feedback_text: 'Good answer',
    run_id: null,
    created_at: '2026-04-01T10:00:00Z',
  },
  {
    id: 'i-2',
    user_message: 'What is FastAPI?',
    assistant_message: 'FastAPI is a modern web framework for building APIs with Python.',
    feedback_score: 2,
    feedback_text: 'Could be more detailed',
    run_id: null,
    created_at: '2026-04-02T12:00:00Z',
  },
]

const SAMPLE_CHATBOTS = [
  { id: 'c-1', name: 'Test Bot', client_id: '', llm_config_id: '', system_prompt: '', sources: [], is_active: true, retrieval_mode: 'vector' as const, retrieval_top_k: 8, created_at: '', updated_at: '' },
]

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <ReportsPage />
    </QueryClientProvider>,
  )
}

describe('ReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useListChatbotsApiV1HubChatbotsGet).mockReturnValue({ data: SAMPLE_CHATBOTS } as any)
    vi.mocked(feedbackApi.fetchInteractions).mockResolvedValue(SAMPLE_INTERACTIONS)
  })

  it('should_display_interactions_table', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('How does Python work?')).toBeInTheDocument()
      expect(screen.getByText('What is FastAPI?')).toBeInTheDocument()
    })
  })

  it('should_filter_low_score_interactions', async () => {
    renderPage()
    await waitFor(() => screen.getByText('How does Python work?'))

    fireEvent.click(screen.getByRole('checkbox'))

    await waitFor(() => {
      expect(feedbackApi.fetchInteractions).toHaveBeenCalledWith(
        'c-1',
        expect.objectContaining({ onlyLowScores: true }),
      )
    })
  })

  it('should_expand_row_to_show_full_messages', async () => {
    renderPage()
    await waitFor(() => screen.getByText('How does Python work?'))

    const expandBtns = screen.getAllByRole('button', { name: /expand/i })
    fireEvent.click(expandBtns[0])

    expect(
      screen.getByText('Python is an interpreted language that runs on a virtual machine.'),
    ).toBeInTheDocument()
  })

  it('should_export_data_as_csv', async () => {
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    renderPage()
    await waitFor(() => screen.getByText('How does Python work?'))

    fireEvent.click(screen.getByRole('button', { name: /csv/i }))

    expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob))
  })

  it('should_display_average_score_metric', async () => {
    renderPage()
    await waitFor(() => {
      // Average of scores 4 and 2 = 3.0
      expect(screen.getByTestId('avg-score')).toHaveTextContent('3.0')
    })
  })
})
