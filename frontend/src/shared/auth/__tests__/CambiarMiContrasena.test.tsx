import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import i18n from '@/shared/i18n'
import { CambiarMiContrasena } from '../CambiarMiContrasena'
import { useCambiarMiPassword } from '@/shared/api/generated/auth/auth'

/**
 * USR.7 — cambiar la propia contraseña, desde el menú de la propia cuenta.
 *
 * No existía en ningún rol. La consecuencia se vio el 2026-09-01: las seis cuentas del piloto se
 * crearon con la misma contraseña y ninguno de sus dueños podía cambiarla.
 *
 * Lo que estos tests fijan, y que es lo que se puede equivocar en una pantalla de contraseñas:
 *
 * - **Pide la actual**, porque es lo que el servidor exige y por el mismo motivo: con el token
 *   basta para actuar, no para quedarse la cuenta.
 * - **El valor no se queda en el formulario**, ni cuando falla. Es una contraseña, no un borrador.
 * - **El error del servidor no se interpreta**: un 401 aquí es «la actual no es ésa», y se dice
 *   así en vez de traducir un `detail` que el servidor deja a propósito indistinguible.
 */
vi.mock('@/shared/api/generated/auth/auth', () => ({
  useCambiarMiPassword: vi.fn(),
}))

const cambiar = vi.fn()

function conMutacion({ isError = false, isPending = false } = {}) {
  vi.mocked(useCambiarMiPassword).mockReturnValue({
    mutate: cambiar,
    isPending,
    isError,
  } as never)
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  cambiar.mockClear()
  conMutacion()
})

function abrir() {
  render(<CambiarMiContrasena />)
  fireEvent.click(screen.getByRole('button', { name: /cambiar mi contraseña/i }))
}

describe('USR.7 — el formulario de la propia contraseña', () => {
  it('should_stay_closed_until_asked', () => {
    render(<CambiarMiContrasena />)

    expect(screen.getByRole('button', { name: /cambiar mi contraseña/i })).toBeDefined()
    expect(screen.queryByLabelText(/contraseña actual/i)).toBeNull()
  })

  it('should_ask_for_the_current_password_too', () => {
    abrir()

    expect(screen.getByLabelText(/contraseña actual/i)).toBeDefined()
    expect(screen.getByLabelText(/contraseña nueva/i)).toBeDefined()
  })

  it('should_hide_both_values', () => {
    abrir()

    expect(screen.getByLabelText(/contraseña actual/i).getAttribute('type')).toBe('password')
    expect(screen.getByLabelText(/contraseña nueva/i).getAttribute('type')).toBe('password')
  })

  it('should_send_both_passwords', async () => {
    abrir()
    fireEvent.change(screen.getByLabelText(/contraseña actual/i), {
      target: { value: 'la-de-ahora' },
    })
    fireEvent.change(screen.getByLabelText(/contraseña nueva/i), {
      target: { value: 'una-contrasena-larga' },
    })
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))

    await waitFor(() => expect(cambiar).toHaveBeenCalled())
    expect(cambiar).toHaveBeenCalledWith(
      { data: { password_actual: 'la-de-ahora', password_nueva: 'una-contrasena-larga' } },
      expect.anything(),
    )
  })

  it('should_refuse_a_new_password_shorter_than_the_contract', async () => {
    abrir()
    fireEvent.change(screen.getByLabelText(/contraseña actual/i), {
      target: { value: 'la-de-ahora' },
    })
    fireEvent.change(screen.getByLabelText(/contraseña nueva/i), { target: { value: 'corta' } })
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeDefined())
    expect(cambiar).not.toHaveBeenCalled()
  })

  it('should_not_keep_the_typed_values_after_sending', async () => {
    abrir()
    fireEvent.change(screen.getByLabelText(/contraseña actual/i), {
      target: { value: 'la-de-ahora' },
    })
    fireEvent.change(screen.getByLabelText(/contraseña nueva/i), {
      target: { value: 'una-contrasena-larga' },
    })
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))

    await waitFor(() => expect(cambiar).toHaveBeenCalled())
    const actual = screen.queryByLabelText(/contraseña actual/i) as HTMLInputElement | null
    expect(actual?.value ?? '').toBe('')
  })

  it('should_say_that_the_current_one_is_wrong_when_the_server_refuses', () => {
    conMutacion({ isError: true })
    abrir()

    expect(screen.getByRole('alert').textContent).toMatch(/actual no es correcta/i)
  })

  it('should_close_without_sending_when_cancelled', async () => {
    abrir()
    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }))

    await waitFor(() =>
      expect(screen.queryByLabelText(/contraseña actual/i)).toBeNull(),
    )
    expect(cambiar).not.toHaveBeenCalled()
  })
})
