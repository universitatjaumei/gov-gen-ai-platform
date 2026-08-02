import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { LoginPage } from '../LoginPage'

/**
 * El envío del formulario no tenía ni un test, y por eso la página llevaba desde el
 * 2026-04-24 llamando a `/api/v1/auth/token/admin` — una ruta que no existe en el backend.
 * El 404 caía en el `catch` genérico y se pintaba «Credenciales incorrectas», así que el
 * síntoma señalaba a la contraseña y el fallo estaba en la URL.
 */

const navigateSpy = vi.hoisted(() => vi.fn())
const loginSpy = vi.hoisted(() => vi.fn())

vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => navigateSpy,
}))

vi.mock('@/shared/auth', async (orig) => ({
  ...(await orig<typeof import('@/shared/auth')>()),
  useAuth: () => ({ login: loginSpy, logout: vi.fn(), user: null, isAuthenticated: false }),
}))

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

afterEach(() => {
  vi.restoreAllMocks()
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

function mockFetch(responder: (url: string) => { ok: boolean; status: number; body?: unknown }) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = typeof input === 'string' ? input : (input as Request).url ?? String(input)
    const { ok, status, body } = responder(url)
    return {
      ok,
      status,
      json: async () => body ?? {},
    } as Response
  })
}

function rellenarYEnviar(password = 'C0l0m3r426!') {
  fireEvent.change(screen.getByLabelText('Usuario'), { target: { value: 'fabra@uji.es' } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: password } })
  fireEvent.submit(screen.getByRole('button', { name: 'Entrar' }).closest('form')!)
}

describe('LoginPage — envío del formulario', () => {
  it('should_post_to_the_superadmin_route_that_exists', async () => {
    const fetchSpy = mockFetch(() => ({ ok: true, status: 200, body: { access_token: 'jwt' } }))
    renderLogin()
    rellenarYEnviar()

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled())
    const llamadas = fetchSpy.mock.calls.map((c) => String(c[0]))
    expect(llamadas[0]).toContain('/api/v1/auth/superadmin/login')
    expect(llamadas.some((u) => u.includes('/auth/token/'))).toBe(false)
  })

  it('should_login_and_navigate_on_success', async () => {
    mockFetch(() => ({ ok: true, status: 200, body: { access_token: 'jwt-bueno' } }))
    renderLogin()
    rellenarYEnviar()

    await waitFor(() => expect(loginSpy).toHaveBeenCalledWith('jwt-bueno'))
    expect(navigateSpy).toHaveBeenCalledWith('/hub', { replace: true })
  })

  it('should_fall_back_to_the_admin_route_when_superadmin_rejects', async () => {
    // Un mismo formulario sirve a dos tablas de cuentas. Si el email no es de SuperAdmin,
    // el 401 no significa «contraseña mala», significa «prueba en la otra puerta».
    const fetchSpy = mockFetch((url) =>
      url.includes('superadmin')
        ? { ok: false, status: 401 }
        : { ok: true, status: 200, body: { access_token: 'jwt-admin' } },
    )
    renderLogin()
    rellenarYEnviar()

    await waitFor(() => expect(loginSpy).toHaveBeenCalledWith('jwt-admin'))
    const llamadas = fetchSpy.mock.calls.map((c) => String(c[0]))
    expect(llamadas[1]).toContain('/api/v1/auth/admin/login')
  })

  it('should_show_the_error_only_when_both_routes_reject', async () => {
    mockFetch(() => ({ ok: false, status: 401 }))
    renderLogin()
    rellenarYEnviar('mal')

    await waitFor(() => expect(screen.getByRole('alert').textContent).toBe('Credenciales incorrectas'))
    expect(loginSpy).not.toHaveBeenCalled()
  })
})

describe('LoginPage — ver la contraseña', () => {
  it('should_hide_the_password_by_default', () => {
    renderLogin()
    expect(screen.getByLabelText('Contraseña').getAttribute('type')).toBe('password')
  })

  it('should_reveal_the_password_when_the_toggle_is_pressed', () => {
    renderLogin()
    fireEvent.click(screen.getByRole('button', { name: 'Mostrar la contraseña' }))

    expect(screen.getByLabelText('Contraseña').getAttribute('type')).toBe('text')
    expect(screen.getByRole('button', { name: 'Ocultar la contraseña' })).toBeDefined()
  })

  it('should_hide_the_password_again_when_toggled_twice', () => {
    renderLogin()
    fireEvent.click(screen.getByRole('button', { name: 'Mostrar la contraseña' }))
    fireEvent.click(screen.getByRole('button', { name: 'Ocultar la contraseña' }))

    expect(screen.getByLabelText('Contraseña').getAttribute('type')).toBe('password')
  })

  it('should_expose_the_toggle_state_to_assistive_tech', () => {
    renderLogin()
    const boton = screen.getByRole('button', { name: 'Mostrar la contraseña' })
    expect(boton.getAttribute('aria-pressed')).toBe('false')

    fireEvent.click(boton)
    expect(screen.getByRole('button', { name: 'Ocultar la contraseña' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('should_not_submit_the_form_when_toggling', () => {
    // Un <button> sin type dentro de un <form> es type="submit" por defecto: sin
    // type="button" el ojo enviaria el formulario con la contrasena a medio escribir.
    const fetchSpy = mockFetch(() => ({ ok: true, status: 200, body: { access_token: 'x' } }))
    renderLogin()
    fireEvent.click(screen.getByRole('button', { name: 'Mostrar la contraseña' }))

    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
