import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { LLMConfigsPage } from '../LLMConfigsPage'

const TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
})

afterEach(() => { vi.unstubAllGlobals() })

const DEMO_CONFIG = {
  id: 'cfg-0001-0000-0000-000000000001',
  provider: 'google',
  model_name: 'gemini-2.0-flash',
  temperature: 0.7,
  max_tokens: 2048,
  api_key_secret_name: 'GOOGLE_API_KEY',
  tier: 1,
  label: 'Gemini Flash',
  is_default: true,
}

function renderPage(configs: object[] = [], fetchOverride?: () => Promise<Response>) {
  vi.stubGlobal('fetch', fetchOverride ?? vi.fn().mockResolvedValue({
    ok: true,
    json: async () => configs,
  }))
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <LLMConfigsPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('LLMConfigsPage', () => {
  it('should_list_llm_configs_with_tier_chips', async () => {
    renderPage([DEMO_CONFIG])
    await waitFor(() => {
      expect(screen.getByText('Gemini Flash')).toBeDefined()
      expect(screen.getByText('Tier 1')).toBeDefined()
    })
  })

  it('should_open_create_form', async () => {
    renderPage([])
    await waitFor(() => screen.getByRole('button', { name: /nueva config/i }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /nueva config/i }))
    })
    expect(screen.getByRole('dialog')).toBeDefined()
  })

  it('should_show_latency_badge_after_test_connection', async () => {
    let callCount = 0
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string, opts?: RequestInit) => {
      if (typeof url === 'string' && url.includes('/test') && opts?.method === 'POST') {
        return { ok: true, json: async () => ({ ok: true, latency_ms: 342 }) }
      }
      callCount++
      return { ok: true, json: async () => [DEMO_CONFIG] }
    }))

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter><AuthProvider><LLMConfigsPage /></AuthProvider></MemoryRouter>
      </QueryClientProvider>
    )

    await waitFor(() => screen.getByRole('button', { name: /probar/i }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /probar/i }))
    })
    await waitFor(() => {
      expect(screen.getByTestId(`test-ok-${DEMO_CONFIG.id}`).textContent).toContain('342 ms')
    })
  })

  it('should_show_affected_chatbots_before_delete', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async (url: string, opts?: RequestInit) => {
      if (typeof url === 'string' && url.includes('/llm-configs/') && opts?.method === 'DELETE') {
        return {
          ok: false,
          json: async () => ({ detail: 'No se puede eliminar: hay chatbots usando esta configuración' }),
        }
      }
      return { ok: true, json: async () => [DEMO_CONFIG] }
    }))

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter><AuthProvider><LLMConfigsPage /></AuthProvider></MemoryRouter>
      </QueryClientProvider>
    )

    await waitFor(() => screen.getByRole('button', { name: /eliminar/i }))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: /eliminar/i })) })
    await waitFor(() => screen.getByRole('dialog'))
    await act(async () => {
      const btns = screen.getAllByRole('button', { name: /eliminar/i })
      fireEvent.click(btns[btns.length - 1])
    })
    await waitFor(() => {
      expect(screen.getByTestId('delete-error').textContent).toContain('chatbots')
    })
  })
})
