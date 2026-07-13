import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AIBrainPage } from '../AIBrainPage'

// ── Hoisted mock data ──────────────────────────────────────────────
const mockChatbotsData = vi.hoisted(() => ({ list: [] as object[] }))

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useListChatbotsApiV1HubChatbotsGet: vi.fn(() => ({
    data: mockChatbotsData.list,
    isLoading: false,
  })),
}))

const TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_') +
  '.signature'

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
})

afterEach(() => {
  vi.unstubAllGlobals()
  mockChatbotsData.list = []
})

// ── Fixtures ──────────────────────────────────────────────────────
const CHATBOT_ID = 'cbot-brain-0001'
const TEMPLATE_ID = 'tmpl-brain-0001'
const LLM_CONFIG_ID_DEFAULT = 'llm-brain-default'
const LLM_CONFIG_ID_OTHER = 'llm-brain-other'

const DEMO_CHATBOT = {
  id: CHATBOT_ID,
  name: 'Bot Cerebro',
  organizacion_id: 'client-1',
  llm_config_id: LLM_CONFIG_ID_DEFAULT,
  system_prompt: '',
  sources: [],
  is_active: true,
  retrieval_mode: 'RAG',
  retrieval_top_k: 8,
  kind: 'atomic',
  parent_chatbot_id: null,
  created_at: '',
  updated_at: '',
}

const DEMO_TEMPLATE = {
  id: TEMPLATE_ID,
  chatbot_id: CHATBOT_ID,
  slug: 'system_base',
  language: 'es',
  template_text: 'Eres un asistente de {empresa}.',
  version: 3,
  default_tier: 2,
  override_tier: null,
}

const DEMO_LLM_CONFIGS = [
  {
    id: LLM_CONFIG_ID_DEFAULT,
    provider: 'openrouter',
    model_name: 'gpt-4o',
    label: 'GPT-4o (default)',
    tier: 1,
    is_default: true,
    temperature: 0.1,
    top_p: 1,
    max_tokens: 12000,
    api_key_secret_name: null,
  },
  {
    id: LLM_CONFIG_ID_OTHER,
    provider: 'google',
    model_name: 'gemini-pro',
    label: 'Gemini Pro',
    tier: 2,
    is_default: false,
    temperature: 0.0,
    top_p: 1,
    max_tokens: 8000,
    api_key_secret_name: null,
  },
]

function mockFetch({
  templates = [] as object[],
  llmConfigs = DEMO_LLM_CONFIGS as object[],
  updateTemplateResponse = null as object | null,
  updateLLMConfigResponse = null as object | null,
} = {}) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (url: string, opts?: RequestInit) => {
      const method = opts?.method ?? 'GET'

      if (typeof url === 'string' && url.includes('/hub/prompt-templates/') && method === 'PATCH') {
        return { ok: true, json: async () => updateTemplateResponse }
      }
      if (typeof url === 'string' && url.includes('/hub/prompt-templates')) {
        return { ok: true, json: async () => templates }
      }
      if (typeof url === 'string' && url.includes('/hub/llm-configs/') && method === 'PATCH') {
        return { ok: true, json: async () => updateLLMConfigResponse }
      }
      if (typeof url === 'string' && url.includes('/hub/llm-configs')) {
        return { ok: true, json: async () => llmConfigs }
      }
      return { ok: true, json: async () => [] }
    }),
  )
}

function renderBrainPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AIBrainPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// ── Tests ──────────────────────────────────────────────────────────
describe('AIBrainPage', () => {
  describe('test_prompt_editor_saves_new_version', () => {
    it('displays the updated version number after saving a prompt', async () => {
      mockChatbotsData.list = [DEMO_CHATBOT]
      mockFetch({
        templates: [DEMO_TEMPLATE],
        updateTemplateResponse: { ...DEMO_TEMPLATE, version: 4 },
      })

      renderBrainPage()

      // Select the chatbot
      const chatbotSelect = screen.getByTestId('chatbot-select')
      fireEvent.change(chatbotSelect, { target: { value: CHATBOT_ID } })

      // Wait for template to load and textarea to appear
      const textarea = await screen.findByTestId('prompt-textarea')
      expect(textarea).toBeTruthy()

      // Edit the prompt text
      fireEvent.change(textarea, { target: { value: 'Eres un asistente actualizado de {empresa}.' } })

      // Save the new version
      const saveBtn = screen.getByTestId('save-prompt-btn')
      fireEvent.click(saveBtn)

      // Verify the updated version (4) is shown
      await waitFor(() => {
        const versionEl = screen.getByTestId('saved-version')
        expect(versionEl.textContent).toContain('4')
      })
    })
  })

  describe('test_model_selector_updates_chatbot', () => {
    it('calls updateLLMConfig with is_default:true when a new model is selected and saved', async () => {
      mockChatbotsData.list = [DEMO_CHATBOT]
      const updatedConfig = { ...DEMO_LLM_CONFIGS[1], is_default: true }
      mockFetch({ updateLLMConfigResponse: updatedConfig })

      renderBrainPage()

      // Select the chatbot and wait for the model-select to appear
      await act(async () => {
        fireEvent.change(screen.getByTestId('chatbot-select'), { target: { value: CHATBOT_ID } })
      })
      await screen.findByTestId('model-select')

      // Select the non-default model and wait for button to become enabled
      await act(async () => {
        fireEvent.change(screen.getByTestId('model-select'), { target: { value: LLM_CONFIG_ID_OTHER } })
      })
      const btn = screen.getByTestId('set-default-btn')
      await waitFor(() => expect(btn).not.toBeDisabled())

      // Click "set as default"
      await act(async () => {
        fireEvent.click(btn)
      })

      // Verify fetch was called with PATCH and is_default: true
      await waitFor(() => {
        const fetchMock = vi.mocked(globalThis.fetch as ReturnType<typeof vi.fn>)
        const patchCall = fetchMock.mock.calls.find(
          ([url, opts]: any[]) =>
            typeof url === 'string' &&
            url.includes(LLM_CONFIG_ID_OTHER) &&
            opts?.method === 'PATCH',
        )
        expect(patchCall).toBeTruthy()
        const body = JSON.parse(patchCall![1]?.body as string)
        expect(body.is_default).toBe(true)
      })
    })
  })
})
