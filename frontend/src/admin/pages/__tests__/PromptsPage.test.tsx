import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { PromptsPage } from '../PromptsPage'

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
  client_id: 'client-1',
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

function mockFetch(templates: object[], chatbots: object[] = [DEMO_CHATBOT]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(async (url: string) => {
      if (typeof url === 'string' && url.includes('/hub/chatbots')) {
        return { ok: true, json: async () => chatbots }
      }
      if (typeof url === 'string' && url.includes('/hub/prompt-templates')) {
        return { ok: true, json: async () => templates }
      }
      return { ok: true, json: async () => [] }
    }),
  )
}

function renderPage(templates: object[] = [], chatbots: object[] = [DEMO_CHATBOT]) {
  mockFetch(templates, chatbots)
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
    const patchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...DEMO_TEMPLATE, version: 4 }),
    })
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async (url: string, opts?: RequestInit) => {
        if (typeof url === 'string' && url.includes('/hub/chatbots')) {
          return { ok: true, json: async () => [DEMO_CHATBOT] }
        }
        if (
          typeof url === 'string' &&
          url.includes('/hub/prompt-templates/') &&
          opts?.method === 'PATCH'
        ) {
          return patchMock(url, opts)
        }
        if (typeof url === 'string' && url.includes('/hub/prompt-templates')) {
          return { ok: true, json: async () => [DEMO_TEMPLATE] }
        }
        return { ok: true, json: async () => [] }
      }),
    )

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <PromptsPage />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await waitFor(() => screen.getByText('system_base'))
    await act(async () => {
      fireEvent.click(screen.getByText('system_base'))
    })
    await waitFor(() => screen.getByRole('button', { name: /guardar/i }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    })
    await waitFor(() => {
      expect(patchMock).toHaveBeenCalled()
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
