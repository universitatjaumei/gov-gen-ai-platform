import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import type { ChatbotRead } from '@/shared/api/generated/model'
import { ChatbotsPage } from '../pages/ChatbotsPage'

/**
 * FIX.1 — El modelo de un chatbot se elige, no se hereda de una constante.
 *
 * El formulario hardcodeaba `llm_config_id: DEV_LLM_ID`. Consecuencias que estos tests
 * fijan: no había forma de mover un chatbot a otro modelo cuando Google retiró
 * `gemini-2.0-flash`, y **editar cualquier chatbot le reasignaba el modelo en silencio** —el
 * «Chatbot de Ejemplo» usa Ollama a propósito y una edición inocente lo pasaba a Gemini—.
 */

const CONFIG_GEMINI = '00000000-0000-0000-0000-0000000000aa'
const CONFIG_OLLAMA = '00000000-0000-0000-0000-0000000000bb'

const { mockCreate, mockUpdate, mockData } = vi.hoisted(() => ({
  mockCreate: vi.fn(),
  mockUpdate: vi.fn(),
  mockData: {
    chatbots: [] as ChatbotRead[],
    configs: [] as unknown[],
    organizaciones: [] as unknown[],
  },
}))

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useListChatbotsApiV1HubChatbotsGet: vi.fn(() => ({ data: mockData.chatbots, isLoading: false })),
  useListChildrenApiV1HubChatbotsChatbotIdChildrenGet: vi.fn(() => ({ data: [], isLoading: false })),
  useGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGet: vi.fn(() => ({ data: undefined })),
  useCreateChatbotApiV1HubChatbotsPost: vi.fn(() => ({ mutate: mockCreate, isPending: false, reset: vi.fn() })),
  useUpdateChatbotApiV1HubChatbotsChatbotIdPatch: vi.fn(() => ({ mutate: mockUpdate, isPending: false, reset: vi.fn() })),
  useDeleteChatbotApiV1HubChatbotsChatbotIdDelete: vi.fn(() => ({ mutate: vi.fn(), isPending: false, reset: vi.fn() })),
  useAssignChildApiV1HubChatbotsChatbotIdChildrenPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRegenerateChunksApiV1HubChatbotsChatbotIdRegenerateChunksPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  getListChatbotsApiV1HubChatbotsGetQueryKey: vi.fn(() => ['/api/v1/hub/chatbots']),
  getListChildrenApiV1HubChatbotsChatbotIdChildrenGetQueryKey: vi.fn((id: string) => [`c/${id}`]),
  getGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGetQueryKey: vi.fn((id: string) => [`s/${id}`]),
}))

vi.mock('@/shared/api/generated/hub-llm-configs/hub-llm-configs', () => ({
  useListLlmConfigsApiV1HubLlmConfigsGet: vi.fn(() => ({ data: mockData.configs, isLoading: false })),
}))

vi.mock('@/shared/api/generated/hub-organizaciones/hub-organizaciones', () => ({
  useListOrganizacionesApiV1HubOrganizacionesGet: vi.fn(() => ({
    data: mockData.organizaciones,
    isLoading: false,
  })),
}))

const TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
})

afterEach(() => {
  vi.clearAllMocks()
  mockData.chatbots = []
  mockData.configs = []
  mockData.organizaciones = []
})

const CHATBOT_OLLAMA: ChatbotRead = {
  id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  name: 'Chatbot de Ejemplo',
  organizacion_id: '00000000-0000-0000-0000-000000000010',
  llm_config_id: CONFIG_OLLAMA,
  system_prompt: 'Eres un asistente.',
  sources: [],
  is_active: true,
  retrieval_mode: 'RAG',
  retrieval_top_k: 8,
  use_prompt_caching: false,
  cache_ttl: 3600,
  access_mode: 'authenticated',
  allowed_roles: [],
  allowed_saml_groups: [],
} as unknown as ChatbotRead

function sembrarCatalogos() {
  mockData.configs = [
    { id: CONFIG_GEMINI, provider: 'google', model_name: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', tier: 1, purpose: 'chat', is_default: true },
    { id: CONFIG_OLLAMA, provider: 'ollama', model_name: 'llama3.1:8b', label: '', tier: 1, purpose: 'chat', is_default: false },
  ]
  mockData.organizaciones = [
    { id: '00000000-0000-0000-0000-000000000010', name: 'UJI', partner_id: 'partner_dev' },
  ]
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <ChatbotsPage />
        </AuthProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('ChatbotsPage — selector de modelo', () => {
  it('should_list_available_llm_configs_in_the_form', async () => {
    sembrarCatalogos()
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /nuevo chatbot/i }))

    const selector = await screen.findByLabelText(/modelo/i)
    const opciones = Array.from(selector.querySelectorAll('option')).map((o) => o.textContent)
    expect(opciones.some((o) => o?.includes('gemini-2.5-flash'))).toBe(true)
    expect(opciones.some((o) => o?.includes('llama3.1:8b'))).toBe(true)
  })

  it('should_preselect_the_current_config_when_editing', async () => {
    sembrarCatalogos()
    mockData.chatbots = [CHATBOT_OLLAMA]
    renderPage()

    fireEvent.click(await screen.findByText('Chatbot de Ejemplo'))

    const selector = await screen.findByLabelText(/modelo/i)
    expect((selector as HTMLSelectElement).value).toBe(CONFIG_OLLAMA)
  })

  it('should_not_reassign_the_model_when_editing_without_touching_it', async () => {
    // El fallo que motivó el prompt: editar el nombre de un chatbot de Ollama lo pasaba a
    // Gemini porque el formulario mandaba siempre la constante.
    sembrarCatalogos()
    mockData.chatbots = [CHATBOT_OLLAMA]
    renderPage()

    fireEvent.click(await screen.findByText('Chatbot de Ejemplo'))
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))

    await waitFor(() => expect(mockUpdate).toHaveBeenCalled())
    const enviado = mockUpdate.mock.calls[0][0].data
    expect(enviado.llm_config_id).toBe(CONFIG_OLLAMA)
  })

  it('should_not_send_a_hardcoded_llm_config_id', async () => {
    sembrarCatalogos()
    renderPage()

    fireEvent.click(screen.getByRole('button', { name: /nuevo chatbot/i }))
    fireEvent.change(screen.getByLabelText(/nombre/i), { target: { value: 'Bot nuevo' } })
    fireEvent.change(screen.getByLabelText(/prompt/i), { target: { value: 'Eres un asistente.' } })
    fireEvent.change(await screen.findByLabelText(/modelo/i), { target: { value: CONFIG_OLLAMA } })
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))

    await waitFor(() => expect(mockCreate).toHaveBeenCalled())
    const enviado = mockCreate.mock.calls[0][0].data
    expect(enviado.llm_config_id).toBe(CONFIG_OLLAMA)
    expect(enviado.llm_config_id).not.toBe('00000000-0000-0000-0000-000000000001')
  })
})
