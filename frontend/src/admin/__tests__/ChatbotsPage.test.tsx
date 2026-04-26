import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { ChatbotsPage } from '../pages/ChatbotsPage'

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
  writeTextMock.mockClear()
  vi.unstubAllGlobals()
})

const DEMO_CHATBOT = {
  id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  name: 'Bot Demo',
  client_id: '00000000-0000-0000-0000-000000000010',
  llm_config_id: '00000000-0000-0000-0000-000000000001',
  system_prompt: 'Eres útil.',
  sources: [],
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

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

async function openEditDialog(chatbot = DEMO_CHATBOT) {
  renderPage([chatbot])
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
})
