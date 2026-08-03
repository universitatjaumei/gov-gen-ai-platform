import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AIBrainPage } from '../AIBrainPage'
import {
  useListPromptTemplatesApiV1HubPromptTemplatesGet,
  useUpdatePromptTemplateApiV1HubPromptTemplatesTemplateIdPatch,
} from '@/shared/api/generated/hub-prompt-templates/hub-prompt-templates'
import {
  useListLlmConfigsApiV1HubLlmConfigsGet,
  useUpdateLlmConfigApiV1HubLlmConfigsConfigIdPatch,
} from '@/shared/api/generated/hub-llm-configs/hub-llm-configs'

// ── Hoisted mock data ──────────────────────────────────────────────
const mockChatbotsData = vi.hoisted(() => ({ list: [] as object[] }))

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useListChatbotsApiV1HubChatbotsGet: vi.fn(() => ({
    data: mockChatbotsData.list,
    isLoading: false,
  })),
}))

// Desde CAL.2 la página consume los hooks generados por Orval, así que se doblan
// esos y no `fetch`: axios no pasa por `fetch` y el stub global no interceptaba.
vi.mock('@/shared/api/generated/hub-prompt-templates/hub-prompt-templates', () => ({
  useListPromptTemplatesApiV1HubPromptTemplatesGet: vi.fn(),
  useUpdatePromptTemplateApiV1HubPromptTemplatesTemplateIdPatch: vi.fn(),
  getListPromptTemplatesApiV1HubPromptTemplatesGetQueryKey: vi.fn(() => ['/api/v1/hub/prompt-templates/']),
}))

vi.mock('@/shared/api/generated/hub-llm-configs/hub-llm-configs', () => ({
  useListLlmConfigsApiV1HubLlmConfigsGet: vi.fn(),
  useUpdateLlmConfigApiV1HubLlmConfigsConfigIdPatch: vi.fn(),
  testLlmConnectionApiV1HubLlmConfigsConfigIdTestPost: vi.fn(),
  getListLlmConfigsApiV1HubLlmConfigsGetQueryKey: vi.fn(() => ['/api/v1/hub/llm-configs']),
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

const setDefaultMutate = vi.fn()

/** Doblado de los hooks generados que consume la página. */
function mockApi({
  templates = [] as object[],
  llmConfigs = DEMO_LLM_CONFIGS as object[],
  updateTemplateResponse = null as object | null,
} = {}) {
  vi.mocked(useListPromptTemplatesApiV1HubPromptTemplatesGet).mockReturnValue({
    data: templates,
    isLoading: false,
  } as any)
  vi.mocked(useListLlmConfigsApiV1HubLlmConfigsGet).mockReturnValue({
    data: llmConfigs,
    isLoading: false,
  } as any)

  // `useMutation` real dispararía la petición; aquí basta con invocar el `onSuccess`
  // que la página registra, que es donde vive la lógica que se está probando.
  vi.mocked(useUpdatePromptTemplateApiV1HubPromptTemplatesTemplateIdPatch).mockImplementation(
    ((options?: any) => ({
      mutate: () => options?.mutation?.onSuccess?.(updateTemplateResponse),
      isPending: false,
    })) as any,
  )
  vi.mocked(useUpdateLlmConfigApiV1HubLlmConfigsConfigIdPatch).mockReturnValue({
    mutate: setDefaultMutate,
    isPending: false,
  } as any)
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
      mockApi({
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
      mockApi()

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

      // La configuración elegida y el `is_default` viajan como variables del hook
      // generado, que es la forma que impone el contrato.
      await waitFor(() => {
        expect(setDefaultMutate).toHaveBeenCalledWith({
          configId: LLM_CONFIG_ID_OTHER,
          data: { is_default: true },
        })
      })
    })
  })
})
