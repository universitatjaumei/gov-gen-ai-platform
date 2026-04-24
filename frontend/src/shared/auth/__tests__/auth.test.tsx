import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useSearchParams } from 'react-router-dom'
import { AuthProvider, useAuth } from '../AuthContext'
import { PrivateRoute } from '../PrivateRoute'

const TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ user_id: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

beforeEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})

function AuthConsumer() {
  const { user, isAuthenticated } = useAuth()
  return (
    <div>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="email">{user?.email ?? ''}</span>
      <span data-testid="role">{user?.role ?? ''}</span>
    </div>
  )
}

describe('AuthContext', () => {
  it('should_start_unauthenticated_with_no_token', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <AuthConsumer />
        </AuthProvider>
      </MemoryRouter>
    )
    expect(screen.getByTestId('authenticated').textContent).toBe('false')
    expect(screen.getByTestId('email').textContent).toBe('')
  })

  it('should_restore_session_from_localStorage', () => {
    localStorage.setItem('access_token', TOKEN)
    render(
      <MemoryRouter>
        <AuthProvider>
          <AuthConsumer />
        </AuthProvider>
      </MemoryRouter>
    )
    expect(screen.getByTestId('authenticated').textContent).toBe('true')
    expect(screen.getByTestId('email').textContent).toBe('admin@test.com')
    expect(screen.getByTestId('role').textContent).toBe('admin')
  })

  it('should_set_user_on_login', async () => {
    function LoginTrigger() {
      const { login, isAuthenticated } = useAuth()
      return (
        <div>
          <span data-testid="authenticated">{String(isAuthenticated)}</span>
          <button onClick={() => login(TOKEN)}>Login</button>
        </div>
      )
    }

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginTrigger />
        </AuthProvider>
      </MemoryRouter>
    )

    expect(screen.getByTestId('authenticated').textContent).toBe('false')
    await act(async () => {
      screen.getByRole('button', { name: 'Login' }).click()
    })
    expect(screen.getByTestId('authenticated').textContent).toBe('true')
    expect(localStorage.getItem('access_token')).toBe(TOKEN)
  })

  it('should_clear_user_on_logout', async () => {
    localStorage.setItem('access_token', TOKEN)

    function LogoutTrigger() {
      const { logout, isAuthenticated } = useAuth()
      return (
        <div>
          <span data-testid="authenticated">{String(isAuthenticated)}</span>
          <button onClick={logout}>Logout</button>
        </div>
      )
    }

    render(
      <MemoryRouter>
        <AuthProvider>
          <LogoutTrigger />
        </AuthProvider>
      </MemoryRouter>
    )

    await act(async () => {
      screen.getByRole('button', { name: 'Logout' }).click()
    })
    expect(screen.getByTestId('authenticated').textContent).toBe('false')
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})

describe('PrivateRoute', () => {
  it('should_render_children_when_authenticated', () => {
    localStorage.setItem('access_token', TOKEN)
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <AuthProvider>
          <Routes>
            <Route element={<PrivateRoute />}>
              <Route path="/protected" element={<div>Protected content</div>} />
            </Route>
            <Route path="/login" element={<div>Login page</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    )
    expect(screen.getByText('Protected content')).toBeDefined()
  })

  it('should_redirect_to_login_when_unauthenticated', () => {
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <AuthProvider>
          <Routes>
            <Route element={<PrivateRoute />}>
              <Route path="/protected" element={<div>Protected content</div>} />
            </Route>
            <Route path="/login" element={<div>Login page</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    )
    expect(screen.getByText('Login page')).toBeDefined()
    expect(screen.queryByText('Protected content')).toBeNull()
  })

  it('should_redirect_to_login_with_returnTo_param', () => {
    function CheckReturnTo() {
      const [params] = useSearchParams()
      return <div>from={params.get('from') ?? 'none'}</div>
    }

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <Routes>
            <Route element={<PrivateRoute />}>
              <Route path="/dashboard" element={<div>Dashboard</div>} />
            </Route>
            <Route path="/login" element={<CheckReturnTo />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    )
    expect(screen.getByText('from=/dashboard')).toBeDefined()
  })
})
