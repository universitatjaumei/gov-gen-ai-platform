import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { expectNoA11yViolations } from '@/test/a11y'
import { AccessTokensPage } from '../AccessTokensPage'

const hooks = vi.hoisted(() => ({
  list: [] as object[],
  createMutate: vi.fn(),
  revokeMutate: vi.fn(),
  createdResponse: {
    id: 'pat-1',
    token: 'pat_abcd1234_secretvalue',
    token_prefix: 'abcd1234',
    name: 'mcp',
    scopes: ['redaccion:templates:read'],
    expires_at: null,
  },
}))

vi.mock('@/shared/api/generated/auth-pat/auth-pat', () => ({
  useListPats: vi.fn(() => ({ data: hooks.list, isLoading: false })),
  useCreatePat: vi.fn((opts?: { mutation?: { onSuccess?: (r: object) => void } }) => ({
    mutate: (vars: unknown) => {
      hooks.createMutate(vars)
      opts?.mutation?.onSuccess?.(hooks.createdResponse)
    },
    isPending: false,
  })),
  useRevokePat: vi.fn(() => ({ mutate: hooks.revokeMutate })),
  getListPatsQueryKey: vi.fn(() => ['/api/v1/auth/pats']),
}))

const ADMIN_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.sig'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

afterEach(() => {
  hooks.list = []
  hooks.createMutate.mockClear()
  hooks.revokeMutate.mockClear()
  localStorage.clear()
  vi.restoreAllMocks()
})

function renderPage() {
  localStorage.setItem('access_token', ADMIN_TOKEN)
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <AccessTokensPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AccessTokensPage', () => {
  it('should_create_pat_and_show_plaintext_once', async () => {
    renderPage()
    await act(async () => {
      fireEvent.click(screen.getByText('Crear token'))
    })
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'mcp' } })
    fireEvent.click(screen.getByLabelText('Plantillas: lectura'))
    await act(async () => {
      fireEvent.submit(screen.getByText('Crear').closest('form')!)
    })
    await waitFor(() => {
      expect(hooks.createMutate).toHaveBeenCalled()
      expect(screen.getByTestId('pat-plaintext').textContent).toContain('pat_abcd1234_secretvalue')
    })
  })

  it('should_hide_plaintext_after_closing_modal', async () => {
    renderPage()
    await act(async () => { fireEvent.click(screen.getByText('Crear token')) })
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'mcp' } })
    fireEvent.click(screen.getByLabelText('Plantillas: lectura'))
    await act(async () => { fireEvent.submit(screen.getByText('Crear').closest('form')!) })
    await waitFor(() => screen.getByTestId('pat-plaintext'))
    await act(async () => { fireEvent.click(screen.getByText('Cerrar')) })
    expect(screen.queryByTestId('pat-plaintext')).toBeNull()
  })

  it('should_revoke_pat_after_confirm', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    hooks.list = [{
      id: 'pat-9', name: 'old', token_prefix: 'deadbeef',
      scopes: ['chatbots:read'], created_at: '2026-01-01T00:00:00Z',
      expires_at: null, last_used_at: null, revoked_at: null,
    }]
    renderPage()
    await act(async () => {
      fireEvent.click(screen.getByLabelText('Revocar'))
    })
    expect(hooks.revokeMutate).toHaveBeenCalledWith({ patId: 'pat-9' })
  })

  it('should_have_no_a11y_violations', async () => {
    hooks.list = [{
      id: 'pat-9', name: 'old', token_prefix: 'deadbeef',
      scopes: ['chatbots:read'], created_at: '2026-01-01T00:00:00Z',
      expires_at: null, last_used_at: null, revoked_at: null,
    }]
    const { container } = renderPage()
    await waitFor(() => screen.getByText('old'))
    await expectNoA11yViolations(container)
  })
})
