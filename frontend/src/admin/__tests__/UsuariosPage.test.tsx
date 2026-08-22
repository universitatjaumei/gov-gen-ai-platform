import { describe, it, expect, beforeEach, beforeAll, vi } from 'vitest'
import { render, screen, within, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { UsuariosPage } from '../pages/UsuariosPage'
import {
  useListUsersApiV1HubUsersGet,
  useCreateUserApiV1HubUsersPost,
  useUpdateUserApiV1HubUsersUserIdPatch,
} from '@/shared/api/generated/hub-users/hub-users'
import { useAutoridadDelRol } from '@/shared/auth/useAutoridadDelRol'

/**
 * IDE.4 — quién existe en esta plataforma.
 *
 * No había ninguna pantalla de usuarios: quien administra no sabía quién tenía cuenta, ni con
 * qué rol, ni si había entrado alguna vez, y para averiguarlo necesitaba acceso a Postgres —
 * que es justo lo que no se le puede pedir a otra administración que despliegue esto.
 *
 * Dos cosas que la pantalla tiene que **decir**, no solo hacer:
 *
 * - **Quién manda sobre el rol en este despliegue.** Con `IDENTITY_ROLE_AUTHORITY=idp`, editar
 *   el rol a mano es tirar el trabajo: lo pisa el siguiente inicio de sesión. La pantalla lo
 *   avisa en vez de dejar que se descubra solo.
 * - **Que este listado no son todas las cuentas.** Las otras tres tablas de identidad siguen
 *   sin unificar (IDE.2), y un listado que se lee como completo miente por omisión.
 */
vi.mock('@/shared/api/generated/hub-users/hub-users', () => ({
  useListUsersApiV1HubUsersGet: vi.fn(),
  useCreateUserApiV1HubUsersPost: vi.fn(),
  useUpdateUserApiV1HubUsersUserIdPatch: vi.fn(),
}))

// La autoridad del rol la resuelve la pantalla contra el servidor, no la recibe por prop: un
// componente de ruta tiene que poder cargarse por separado (CAL.5), y un envoltorio en
// `App.tsx` que le pasara el dato rompía esa carga perezosa.
vi.mock('@/shared/auth/useAutoridadDelRol', () => ({
  useAutoridadDelRol: vi.fn(),
}))

const PERSONAS = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    email: 'manual@uji.es',
    display_name: 'Alta Manual',
    role: 'admin',
    organizacion_id: null,
    is_active: true,
    origen: 'manual',
    created_at: '2026-08-22T09:00:00Z',
    created_by: 'root',
    last_login_at: null,
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    email: 'porsso@uji.es',
    display_name: 'Llegó Por SSO',
    role: 'user',
    organizacion_id: null,
    is_active: false,
    origen: 'sso',
    created_at: '2026-08-01T09:00:00Z',
    created_by: null,
    last_login_at: '2026-08-20T10:00:00Z',
  },
]

const mutar = vi.fn()

function conPersonas(personas = PERSONAS, autoridad = 'app') {
  vi.mocked(useListUsersApiV1HubUsersGet).mockReturnValue({
    data: personas,
    isLoading: false,
    error: null,
  } as never)
  vi.mocked(useCreateUserApiV1HubUsersPost).mockReturnValue({
    mutate: mutar,
    isPending: false,
  } as never)
  vi.mocked(useUpdateUserApiV1HubUsersUserIdPatch).mockReturnValue({
    mutate: mutar,
    isPending: false,
  } as never)
  return autoridad
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  mutar.mockClear()
  conPersonas()
})

function renderPage(autoridadDelRol: 'app' | 'idp' = 'app') {
  vi.mocked(useAutoridadDelRol).mockReturnValue(autoridadDelRol)
  // Los hooks generados están doblados, pero la pantalla usa `useQueryClient` para invalidar
  // el listado tras un alta, y eso sí exige el proveedor de verdad.
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter>
        <UsuariosPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('IDE.4 — el listado de personas', () => {
  it('should_show_every_person_with_their_origin', () => {
    renderPage()

    expect(screen.getByText('manual@uji.es')).toBeDefined()
    expect(screen.getByText('porsso@uji.es')).toBeDefined()
  })

  it('should_distinguish_a_manual_row_from_one_provisioned_by_sso', () => {
    // Sin esta columna no se puede saber si el rol lo puso alguien o lo trajo el IdP.
    renderPage()

    const fila = screen.getByRole('row', { name: /manual@uji\.es/ })
    expect(fila.textContent).toMatch(/manual/i)
    const otra = screen.getByRole('row', { name: /porsso@uji\.es/ })
    expect(otra.textContent).toMatch(/sso/i)
  })

  it('should_say_when_someone_never_logged_in', () => {
    // Una fila creada a mano y sin entrada todavía es lo normal: hay que decirlo, no dejar
    // la celda vacía como si fuera un dato que falta.
    renderPage()

    const fila = screen.getByRole('row', { name: /manual@uji\.es/ })
    expect(fila.textContent).toMatch(/nunca/i)
  })

  it('should_mark_a_deactivated_person', () => {
    renderPage()

    const fila = screen.getByRole('row', { name: /porsso@uji\.es/ })
    expect(fila.textContent).toMatch(/desactivad|inactiv/i)
  })

  it('should_build_the_columns_from_the_server_response', () => {
    // El contrato manda: si el servidor deja de enviar a alguien, la fila desaparece.
    conPersonas([PERSONAS[0]])
    renderPage()

    expect(screen.queryByText('porsso@uji.es')).toBeNull()
  })
})

describe('IDE.4 — lo que la pantalla tiene que advertir', () => {
  it('should_warn_that_the_idp_owns_the_role_when_it_does', () => {
    renderPage('idp')

    expect(screen.getByRole('status').textContent).toMatch(/IdP|proveedor de identidad/i)
  })

  it('should_not_warn_when_the_application_owns_the_role', () => {
    renderPage('app')

    const aviso = screen.queryByRole('status')
    expect(aviso?.textContent ?? '').not.toMatch(/IdP|proveedor de identidad/i)
  })

  it('should_say_the_listing_is_not_every_account', () => {
    // Las otras tres tablas de identidad siguen sin unificar (IDE.2).
    renderPage()

    expect(document.body.textContent).toMatch(/no.*todas las cuentas|no incluye/i)
  })
})

describe('IDE.4 — alta y edición', () => {
  it('should_create_a_person_with_the_role_chosen', () => {
    renderPage()

    fireEvent.change(screen.getByLabelText(/correo/i), { target: { value: 'nueva@uji.es' } })
    fireEvent.change(screen.getByLabelText(/^rol/i), { target: { value: 'admin' } })
    fireEvent.click(screen.getByRole('button', { name: /dar de alta/i }))

    expect(mutar).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ email: 'nueva@uji.es', role: 'admin' }) }),
      expect.anything()
    )
  })

  it('should_not_offer_a_password_field', () => {
    // El alta crea identidad y permisos, no una credencial: quien entra, entra por SSO.
    renderPage()

    expect(screen.queryByLabelText(/contraseña/i)).toBeNull()
  })

  it('should_deactivate_a_person_without_deleting_them', () => {
    renderPage()

    const fila = screen.getByRole('row', { name: /manual@uji\.es/ })
    fireEvent.click(within(fila).getByRole('button', { name: /desactivar/i }))

    expect(mutar).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ is_active: false }) }),
      expect.anything()
    )
  })

  it('should_not_offer_a_delete_action', () => {
    // Una persona que ya entró tiene rastro en interacciones, informes y concesiones.
    renderPage()

    expect(screen.queryByRole('button', { name: /eliminar|borrar/i })).toBeNull()
  })
})
