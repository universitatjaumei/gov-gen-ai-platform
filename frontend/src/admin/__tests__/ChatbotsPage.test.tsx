import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import type { ChatbotRead, CorpusStatsOut } from '@/shared/api/generated/model'
import { ChatbotsPage } from '../pages/ChatbotsPage'

const { mockAssignMutate, mockData } = vi.hoisted(() => ({
  mockAssignMutate: vi.fn(),
  mockData: {
    chatbots: [] as ChatbotRead[],
    children: [] as ChatbotRead[],
    corpusStats: undefined as CorpusStatsOut | undefined,
  },
}))

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useListChatbotsApiV1HubChatbotsGet: vi.fn(() => ({ data: mockData.chatbots, isLoading: false })),
  useListChildrenApiV1HubChatbotsChatbotIdChildrenGet: vi.fn(() => ({ data: mockData.children, isLoading: false })),
  useGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGet: vi.fn(() => ({ data: mockData.corpusStats })),
  useCreateChatbotApiV1HubChatbotsPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false, reset: vi.fn() })),
  useUpdateChatbotApiV1HubChatbotsChatbotIdPatch: vi.fn(() => ({ mutate: vi.fn(), isPending: false, reset: vi.fn() })),
  useDeleteChatbotApiV1HubChatbotsChatbotIdDelete: vi.fn(() => ({ mutate: vi.fn(), isPending: false, reset: vi.fn() })),
  useAssignChildApiV1HubChatbotsChatbotIdChildrenPost: vi.fn(() => ({ mutate: mockAssignMutate, isPending: false })),
  useRegenerateChunksApiV1HubChatbotsChatbotIdRegenerateChunksPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  getListChatbotsApiV1HubChatbotsGetQueryKey: vi.fn(() => ['/api/v1/hub/chatbots']),
  getListChildrenApiV1HubChatbotsChatbotIdChildrenGetQueryKey: vi.fn((id: string) => [`/api/v1/hub/chatbots/${id}/children`]),
  getGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGetQueryKey: vi.fn((id: string) => [`/api/v1/hub/chatbots/${id}/corpus-stats`]),
}))

const TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

const writeTextMock = vi.fn().mockResolvedValue(undefined)

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: writeTextMock },
    writable: true,
    configurable: true,
  })
})

afterEach(() => {
  vi.clearAllMocks()
  mockData.chatbots = []
  mockData.children = []
  mockData.corpusStats = undefined
})

const DEMO_CHATBOT: ChatbotRead = {
  id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  name: 'Bot Demo',
  client_id: '00000000-0000-0000-0000-000000000010',
  llm_config_id: '00000000-0000-0000-0000-000000000001',
  system_prompt: 'Eres útil.',
  sources: [],
  is_active: true,
  retrieval_mode: 'RAG',
  retrieval_top_k: 8,
  use_prompt_caching: false,
  cache_ttl: 3600,
  kind: 'atomic',
  parent_chatbot_id: null,
  public_graph_profile: 'PUBLIC_KB_RICH',
  language_mode: 'prefer',
  quality_threshold: 0.6,
  min_retrieval_results: 2,
  min_retrieval_score: 0.25,
  reranker_enabled: true,
  answer_template: 'generic',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const ROUTER_CHATBOT: ChatbotRead = {
  ...DEMO_CHATBOT,
  id: 'bbbbbbbb-bbbb-cccc-dddd-eeeeeeeeeeee',
  name: 'Router UJI',
  kind: 'router',
}

const CHILD_CHATBOT: ChatbotRead = {
  ...DEMO_CHATBOT,
  id: 'cccccccc-bbbb-cccc-dddd-eeeeeeeeeeee',
  name: 'RRHH',
}

const DEMO_CORPUS_STATS: CorpusStatsOut = {
  total_documents: 2,
  total_tokens: 120000,
  by_language: { es: 100000, ca: 20000 },
  recommended_mode: 'MD_AGENT_SELECTOR',
  recommendation_reason: 'Recomendado MD_AGENT_SELECTOR para este tamaño de corpus.',
}

function renderPage(chatbots: ChatbotRead[] = [], children: ChatbotRead[] = [], corpusStats?: CorpusStatsOut) {
  mockData.chatbots = chatbots
  mockData.children = children
  mockData.corpusStats = corpusStats
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <ChatbotsPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

async function openEditDialog(chatbot = DEMO_CHATBOT, allChatbots: ChatbotRead[] = [chatbot], children: ChatbotRead[] = [], corpusStats?: CorpusStatsOut) {
  renderPage(allChatbots, children, corpusStats)
  await waitFor(() => screen.getByText(chatbot.name))
  await act(async () => {
    fireEvent.click(screen.getByText(chatbot.name))
  })
  await waitFor(() => screen.getByRole('dialog'))
}

describe('ChatbotsPage', () => {
  it('should_show_empty_state_when_no_chatbots', async () => {
    renderPage([])
    await waitFor(() => {
      expect(screen.getByText('No hay chatbots creados')).toBeDefined()
    })
  })

  it('should_list_chatbots_from_api', async () => {
    renderPage([DEMO_CHATBOT])
    await waitFor(() => {
      expect(screen.getByText('Bot Demo')).toBeDefined()
    })
  })

  it('should_show_new_chatbot_button', async () => {
    renderPage([])
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /nuevo chatbot/i })).toBeDefined()
    })
  })

  it('should_open_form_on_new_chatbot_click', async () => {
    renderPage([])
    await waitFor(() => screen.getByRole('button', { name: /nuevo chatbot/i }))
    await act(async () => {
      screen.getByRole('button', { name: /nuevo chatbot/i }).click()
    })
    expect(screen.getByRole('dialog')).toBeDefined()
  })

  it('should_show_delete_button_per_chatbot', async () => {
    renderPage([DEMO_CHATBOT])
    await waitFor(() => screen.getByText('Bot Demo'))
    expect(screen.getByRole('button', { name: /eliminar/i })).toBeDefined()
  })

  it('should_show_chatbot_id_in_edit_dialog', async () => {
    await openEditDialog()
    expect(screen.getByText(DEMO_CHATBOT.id)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /copiar/i })).toBeInTheDocument()
  })

  it('should_copy_chatbot_id_to_clipboard', async () => {
    await openEditDialog()
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /copiar/i }))
    })
    expect(writeTextMock).toHaveBeenCalledWith(DEMO_CHATBOT.id)
  })

  it('should_show_install_snippet_in_edit_dialog', async () => {
    await openEditDialog()
    const snippet = screen.getByTestId('install-snippet')
    expect(snippet.textContent).toContain(`data-chatbot-id="${DEMO_CHATBOT.id}"`)
  })

  it('should_show_kind_selector_in_form', async () => {
    renderPage([])
    await waitFor(() => screen.getByRole('button', { name: /nuevo chatbot/i }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /nuevo chatbot/i }))
    })
    expect(screen.getByText(/tipo de chatbot/i)).toBeInTheDocument()
  })

  it('should_hide_retrieval_mode_when_kind_is_router', async () => {
    renderPage([])
    await waitFor(() => screen.getByRole('button', { name: /nuevo chatbot/i }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /nuevo chatbot/i }))
    })

    const kindSelect = screen.getAllByRole('combobox')[0]
    await act(async () => {
      fireEvent.change(kindSelect, { target: { value: 'router' } })
    })

    expect(screen.queryByText(/modo de retrieval/i)).not.toBeInTheDocument()
  })

  it('should_show_children_section_for_router_chatbots', async () => {
    await openEditDialog(ROUTER_CHATBOT, [ROUTER_CHATBOT], [])
    expect(screen.getByRole('button', { name: /asignar hijo/i })).toBeInTheDocument()
  })

  it('should_warn_when_router_has_no_children', async () => {
    await openEditDialog(ROUTER_CHATBOT, [ROUTER_CHATBOT], [])
    expect(screen.getByText(/no tiene sub-chatbots asignados/i)).toBeInTheDocument()
  })

  it('should_assign_child_via_modal', async () => {
    await openEditDialog(ROUTER_CHATBOT, [ROUTER_CHATBOT, CHILD_CHATBOT], [])
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /asignar hijo/i }))
    })

    const select = screen.getByDisplayValue('-- Seleccionar --')
    await act(async () => {
      fireEvent.change(select, { target: { value: CHILD_CHATBOT.id } })
    })

    const assignButtons = screen.getAllByRole('button', { name: /^asignar$/i })
    await act(async () => {
      fireEvent.click(assignButtons[assignButtons.length - 1])
    })

    expect(mockAssignMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        chatbotId: ROUTER_CHATBOT.id,
        data: expect.objectContaining({ child_chatbot_id: CHILD_CHATBOT.id }),
      })
    )
  })

  it('should_show_recommendation_banner_with_reason', async () => {
    await openEditDialog(DEMO_CHATBOT, [DEMO_CHATBOT], [], DEMO_CORPUS_STATS)
    expect(screen.getByText(/sugerido:/i)).toBeInTheDocument()
    expect(screen.getByText(/recomendado md_agent_selector/i)).toBeInTheDocument()
  })

  it('should_warn_when_user_picks_non_recommended_mode', async () => {
    await openEditDialog(DEMO_CHATBOT, [DEMO_CHATBOT], [], DEMO_CORPUS_STATS)
    await waitFor(() => screen.getByText(/sugerido:/i))

    const retrievalSelect = screen.getAllByRole('combobox')[1]
    await act(async () => {
      fireEvent.change(retrievalSelect, { target: { value: 'RAG' } })
    })

    expect(screen.getByText(/modo distinto del recomendado/i)).toBeInTheDocument()
  })

  it('should_show_chunk_regeneration_button_only_for_vector_mode', async () => {
    await openEditDialog(DEMO_CHATBOT, [DEMO_CHATBOT], [], DEMO_CORPUS_STATS)
    expect(screen.getByRole('button', { name: /recalcular chunks/i })).toBeInTheDocument()

    const retrievalSelect = screen.getAllByRole('combobox')[1]
    await act(async () => {
      fireEvent.change(retrievalSelect, { target: { value: 'MD_AGENT_SELECTOR' } })
    })

    expect(screen.queryByRole('button', { name: /recalcular chunks/i })).not.toBeInTheDocument()
  })
})
