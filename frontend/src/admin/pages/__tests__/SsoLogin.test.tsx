import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { LoginPage } from '../LoginPage'

const navigateSpy = vi.hoisted(() => vi.fn())
const loginSpy = vi.hoisted(() => vi.fn())

vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => navigateSpy,
}))

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

afterEach(() => {
  vi.unstubAllEnvs()
  navigateSpy.mockClear()
  loginSpy.mockClear()
})

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('LoginPage SSO', () => {
  it('should_show_sso_button_when_enabled', () => {
    vi.stubEnv('VITE_SAML_ENABLED', 'true')
    renderLogin()
    expect(screen.getByText('Entrar con SSO institucional')).toBeDefined()
  })

  it('should_hide_sso_button_when_disabled', () => {
    vi.stubEnv('VITE_SAML_ENABLED', 'false')
    renderLogin()
    expect(screen.queryByText('Entrar con SSO institucional')).toBeNull()
  })

  it('should_redirect_to_saml_login_on_click', () => {
    vi.stubEnv('VITE_SAML_ENABLED', 'true')
    const orig = window.location
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { href: '' },
    })
    renderLogin()
    act(() => {
      screen.getByText('Entrar con SSO institucional').click()
    })
    expect(window.location.href).toContain('/api/v1/auth/saml/login')
    Object.defineProperty(window, 'location', { configurable: true, value: orig })
  })
})

describe('AuthCallbackPage', () => {
  it('should_extract_token_from_fragment_and_login', async () => {
    vi.doMock('@/shared/auth', async (orig) => ({
      ...(await orig<typeof import('@/shared/auth')>()),
      useAuth: () => ({ login: loginSpy, logout: vi.fn(), user: null, isAuthenticated: false }),
    }))
    window.location.hash = '#token=jwt-token-value'
    const { AuthCallbackPage } = await import('../AuthCallbackPage')
    await act(async () => {
      render(
        <MemoryRouter>
          <AuthCallbackPage />
        </MemoryRouter>,
      )
    })
    expect(loginSpy).toHaveBeenCalledWith('jwt-token-value')
    expect(navigateSpy).toHaveBeenCalledWith('/hub', { replace: true })
    vi.doUnmock('@/shared/auth')
  })
})
