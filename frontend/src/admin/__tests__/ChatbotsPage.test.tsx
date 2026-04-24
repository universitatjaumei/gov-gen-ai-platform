import { describe, it, expect, beforeAll, vi } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { ChatbotsPage } from '../pages/ChatbotsPage'

const TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
})

function renderPage(chatbots: object[] = []) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => chatbots,
  }))

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

describe('ChatbotsPage', () => {
  it('should_show_empty_state_when_no_chatbots', async () => {
    renderPage([])
    await waitFor(() => {
      expect(screen.getByText('No hay chatbots creados')).toBeDefined()
    })
  })

  it('should_list_chatbots_from_api', async () => {
    renderPage([
      {
        id: '00000000-0000-0000-0000-000000000100',
        name: 'Bot Demo',
        client_id: '00000000-0000-0000-0000-000000000010',
        llm_config_id: '00000000-0000-0000-0000-000000000001',
        system_prompt: 'Eres útil.',
        sources: [],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ])
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
    renderPage([
      {
        id: '00000000-0000-0000-0000-000000000100',
        name: 'Bot Demo',
        client_id: '00000000-0000-0000-0000-000000000010',
        llm_config_id: '00000000-0000-0000-0000-000000000001',
        system_prompt: 'Eres útil.',
        sources: [],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ])
    await waitFor(() => screen.getByText('Bot Demo'))
    expect(screen.getByRole('button', { name: /eliminar/i })).toBeDefined()
  })
})
