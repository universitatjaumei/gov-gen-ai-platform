import { describe, it, expect, beforeAll, vi } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { OrganizacionesPage } from '../pages/OrganizacionesPage'

const TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

const SAMPLE_CLIENTS = [
  {
    id: '00000000-0000-0000-0000-000000000010',
    name: 'Universitat Jaume I',
    partner_id: 'partner-1',
    theme_config: {},
    is_active: true,
    chatbot_count: 3,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: '00000000-0000-0000-0000-000000000011',
    name: 'Ajuntament de Castelló',
    partner_id: 'partner-2',
    theme_config: {},
    is_active: false,
    chatbot_count: 0,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
]

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
})

function renderPage(clients: object[] = []) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => clients,
  }))

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <OrganizacionesPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('OrganizacionesPage', () => {
  it('should_render_organizaciones_page_from_generated_types', async () => {
    renderPage(SAMPLE_CLIENTS)
    await waitFor(() => {
      expect(screen.getByText('Universitat Jaume I')).toBeDefined()
      expect(screen.getByText('Ajuntament de Castelló')).toBeDefined()
    })
  })

  it('should_create_client_with_valid_data', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [] })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: '00000000-0000-0000-0000-000000000020',
          name: 'Nou Client',
          partner_id: 'partner-3',
          theme_config: {},
          is_active: true,
          chatbot_count: 0,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        }),
      })
      .mockResolvedValue({ ok: true, json: async () => [] })
    vi.stubGlobal('fetch', fetchMock)

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <OrganizacionesPage />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )

    await waitFor(() => screen.getByRole('button', { name: /nueva organización/i }))
    await act(async () => {
      screen.getByRole('button', { name: /nueva organización/i }).click()
    })

    expect(screen.getByRole('dialog')).toBeDefined()

    const nameInput = screen.getByLabelText(/nombre de la organización/i)
    const partnerInput = screen.getByLabelText(/admin id/i)
    fireEvent.change(nameInput, { target: { value: 'Nou Client' } })
    fireEvent.change(partnerInput, { target: { value: 'partner-3' } })

    await act(async () => {
      screen.getByRole('button', { name: /guardar/i }).click()
    })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/hub/organizaciones'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('should_show_assigned_chatbots_count', async () => {
    renderPage(SAMPLE_CLIENTS)
    await waitFor(() => {
      expect(screen.getByText('Universitat Jaume I')).toBeDefined()
    })
    const badges = screen.getAllByText('3')
    expect(badges.length).toBeGreaterThan(0)
  })

  it('should_filter_clients_by_name', async () => {
    renderPage(SAMPLE_CLIENTS)
    await waitFor(() => {
      expect(screen.getByText('Universitat Jaume I')).toBeDefined()
    })

    const filterInput = screen.getByPlaceholderText(/filtrar por nombre/i)
    fireEvent.change(filterInput, { target: { value: 'Jaume' } })

    await waitFor(() => {
      expect(screen.getByText('Universitat Jaume I')).toBeDefined()
      expect(screen.queryByText('Ajuntament de Castelló')).toBeNull()
    })
  })
})
