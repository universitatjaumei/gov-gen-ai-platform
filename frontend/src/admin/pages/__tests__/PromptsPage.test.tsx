import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { PromptsPage } from '../PromptsPage'
import {
  useListPromptTemplatesApiV1HubPromptTemplatesGet,
  useCreatePromptTemplateApiV1HubPromptTemplatesPost,
  useUpdatePromptTemplateApiV1HubPromptTemplatesTemplateIdPatch,
  useDeletePromptTemplateApiV1HubPromptTemplatesTemplateIdDelete,
} from '@/shared/api/generated/hub-prompt-templates/hub-prompt-templates'

const mockChatbotsData = vi.hoisted(() => ({ list: [] as object[] }))

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useOpcionesDeGrafoApiV1HubChatbotsOpcionesDeGrafoGet: () => ({ data: { perfiles: [{ nombre: 'PUBLIC_KB_RICH', configurable: true }], modos: [{ nombre: 'RAG' }, { nombre: 'MD_LONG_CONTEXT' }, { nombre: 'MD_AGENT_SELECTOR' }], estrategias: { retrieval: [], merge: [], template: [], language: [] }, ejes: ['retrieval', 'merge', 'template', 'language'] } }),
  useListChatbotsApiV1HubChatbotsGet: vi.fn(() => ({ data: mockChatbotsData.list, isLoading: false })),
  useUpdateChatbotApiV1HubChatbotsChatbotIdPatch: vi.fn(() => ({ mutate: vi.fn(), isPending: false, reset: vi.fn() })),
  getListChatbotsApiV1HubChatbotsGetQueryKey: vi.fn(() => ['/api/v1/hub/chatbots']),
}))

// Desde CAL.2 las plantillas llegan por el hook generado, no por `fetch`.
vi.mock('@/shared/api/generated/hub-prompt-templates/hub-prompt-templates', () => ({
  useListPromptTemplatesApiV1HubPromptTemplatesGet: vi.fn(),
  useCreatePromptTemplateApiV1HubPromptTemplatesPost: vi.fn(),
  useUpdatePromptTemplateApiV1HubPromptTemplatesTemplateIdPatch: vi.fn(),
  useDeletePromptTemplateApiV1HubPromptTemplatesTemplateIdDelete: vi.fn(),
  getListPromptTemplatesApiV1HubPromptTemplatesGetQueryKey: vi.fn(() => ['/api/v1/hub/prompt-templates/']),
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

const CHATBOT_ID = 'cbot-0001-0000-0000-000000000001'

const DEMO_TEMPLATE = {
  id: 'tmpl-0001-0000-0000-000000000001',
  chatbot_id: CHATBOT_ID,
  slug: 'system_base',
  language: 'es',
  template_text: 'Eres un asistente de {empresa}. Responde a {usuario}.',
  version: 3,
  default_tier: 2,
  override_tier: null,
}

const DEMO_TEMPLATE_OVERRIDE = {
  ...DEMO_TEMPLATE,
  id: 'tmpl-0002-0000-0000-000000000002',
  override_tier: 1,
}

const DEMO_CHATBOT = {
  id: CHATBOT_ID,
  name: 'Bot Demo',
  organizacion_id: 'client-1',
  llm_config_id: 'llm-1',
  system_prompt: 'Eres útil.',
  sources: [],
  is_active: true,
  retrieval_mode: 'vector',
  retrieval_top_k: 8,
  kind: 'atomic',
  parent_chatbot_id: null,
  created_at: '',
  updated_at: '',
}

const savePromptMutate = vi.fn()
const mutationDouble = (mutate = vi.fn()) => ({ mutate, isPending: false }) as any

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useCreatePromptTemplateApiV1HubPromptTemplatesPost).mockReturnValue(mutationDouble())
  vi.mocked(useDeletePromptTemplateApiV1HubPromptTemplatesTemplateIdDelete).mockReturnValue(mutationDouble())
  vi.mocked(useUpdatePromptTemplateApiV1HubPromptTemplatesTemplateIdPatch)
    .mockReturnValue(mutationDouble(savePromptMutate))
})

function renderPage(templates: object[] = [], chatbots: object[] = [DEMO_CHATBOT]) {
  mockChatbotsData.list = chatbots
  vi.mocked(useListPromptTemplatesApiV1HubPromptTemplatesGet).mockReturnValue({
    data: templates,
    isLoading: false,
  } as any)
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <PromptsPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PromptsPage', () => {
  it('should_list_prompt_templates', async () => {
    renderPage([DEMO_TEMPLATE])
    await waitFor(() => {
      expect(screen.getByText('system_base')).toBeDefined()
      expect(screen.getByText('v3')).toBeDefined()
    })
  })

  it('should_highlight_variables_in_editor', async () => {
    renderPage([DEMO_TEMPLATE])
    await waitFor(() => screen.getByText('system_base'))
    await act(async () => {
      fireEvent.click(screen.getByText('system_base'))
    })
    await waitFor(() => {
      const highlights = document.querySelectorAll('[data-testid="var-highlight"]')
      expect(highlights.length).toBeGreaterThan(0)
      const texts = Array.from(highlights).map((el) => el.textContent)
      expect(texts).toContain('{empresa}')
    })
  })

  it('should_show_effective_tier_with_override', async () => {
    renderPage([DEMO_TEMPLATE_OVERRIDE])
    await waitFor(() => screen.getByText('system_base'))
    await act(async () => {
      fireEvent.click(screen.getByText('system_base'))
    })
    await waitFor(() => {
      expect(screen.getByTestId('effective-tier').textContent).toContain('1')
    })
  })

  it('should_increment_version_on_save', async () => {
    renderPage([DEMO_TEMPLATE])

    await waitFor(() => screen.getByText('system_base'))
    await act(async () => {
      fireEvent.click(screen.getByText('system_base'))
    })
    await waitFor(() => screen.getByRole('button', { name: /guardar/i }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    })

    // El PATCH viaja como variables del hook generado: id en `templateId`, cuerpo en
    // `data`. Es el servidor quien decide el número de versión resultante.
    await waitFor(() => {
      expect(savePromptMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          templateId: DEMO_TEMPLATE.id,
          data: expect.objectContaining({ template_text: DEMO_TEMPLATE.template_text }),
        }),
      )
    })
  })

  it('should_preview_prompt_with_example_values', async () => {
    renderPage([DEMO_TEMPLATE])
    await waitFor(() => screen.getByText('system_base'))
    await act(async () => {
      fireEvent.click(screen.getByText('system_base'))
    })
    await waitFor(() => {
      const preview = screen.getByTestId('prompt-preview')
      expect(preview.textContent).toContain('empresa')
      expect(preview.textContent).not.toContain('{empresa}')
    })
  })

  it('should_list_chatbot_base_prompts', async () => {
    renderPage([DEMO_TEMPLATE])
    await waitFor(() => {
      expect(screen.getByText('Prompts base de chatbot')).toBeDefined()
      expect(screen.getAllByText('Bot Demo').length).toBeGreaterThan(0)
      expect(screen.getByText('Eres útil.')).toBeDefined()
    })
  })
})
