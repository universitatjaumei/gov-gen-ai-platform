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
  useDeleteUserApiV1HubUsersUserIdDelete as useBorrar,
} from '@/shared/api/generated/hub-users/hub-users'
import type { UsuarioRead } from '@/shared/api/generated/model'
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
  useDeleteUserApiV1HubUsersUserIdDelete: vi.fn(),
  getListUsersApiV1HubUsersGetQueryKey: () => ['usuarios'],
}))

// La autoridad del rol la resuelve la pantalla contra el servidor, no la recibe por prop: un
// componente de ruta tiene que poder cargarse por separado (CAL.5), y un envoltorio en
// `App.tsx` que le pasara el dato rompía esa carga perezosa.
vi.mock('@/shared/auth/useAutoridadDelRol', () => ({
  useAutoridadDelRol: vi.fn(),
}))

vi.mock('@/shared/api/generated/hub-organizaciones/hub-organizaciones', () => ({
  useListOrganizacionesApiV1HubOrganizacionesGet: () => ({
    data: [
      { id: 'org-uji', name: 'Universitat Jaume I' },
      { id: 'org-dipu', name: 'Diputación de Castellón' },
    ],
  }),
}))

const PERSONAS: UsuarioRead[] = [
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
    puede_borrarse: true,
    motivo_no_borrable: null,
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
    puede_borrarse: false,
    motivo_no_borrable: 'Esta persona ya ha entrado.',
  },
]

const mutar = vi.fn()
const borrar = vi.fn()

function conPersonas(personas: UsuarioRead[] = PERSONAS, autoridad = 'app') {
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
  vi.mocked(useBorrar).mockReturnValue({ mutate: borrar, isPending: false } as never)
  return autoridad
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  localStorage.clear()
  mutar.mockClear()
  borrar.mockClear()
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

  it('should_not_offer_a_delete_action_for_someone_who_has_used_the_platform', () => {
    // Una persona que ya entró tiene rastro en interacciones, informes y concesiones.
    //
    // REV.8 acota este «no hay borrado» en vez de tirarlo: sigue siendo cierto para quien ya
    // entró —que es de quien hablaba IDE.4— y deja de serlo para una fila creada a mano que
    // nadie ha usado. Se comprueba **sobre esa fila** y no sobre la pantalla entera, que es
    // lo que hacía este test cuando el borrado no existía para nadie.
    renderPage()

    const yaEntro = screen.getByTestId('persona-porsso@uji.es')
    expect(
      within(yaEntro).queryByRole('button', { name: /eliminar|borrar/i })
    ).toBeNull()
  })
})

/**
 * REV.8 — borrar, y ver al superadministrador.
 *
 * IDE.4 decidió «desactivar, nunca borrar», con buen motivo: quien ya entró tiene rastro. Era
 * absoluto de más — una fila creada a mano que nadie ha usado no tiene rastro de nada, y un
 * correo mal escrito se quedaba en el listado para siempre.
 *
 * Y el superadministrador principal no aparecía: vive en `superadminaccount` y el listado leía
 * sólo `hub_users`, así que la única cuenta real de una instalación nueva era invisible.
 */
const SUPERADMIN_DE_ARRANQUE: UsuarioRead = {
  id: '33333333-3333-3333-3333-333333333333',
  email: 'root@uji.es',
  display_name: 'SuperAdmin de arranque',
  role: 'superadmin',
  organizacion_id: null,
  is_active: true,
  origen: 'superadmin',
  created_at: '2026-01-01T09:00:00Z',
  created_by: null,
  last_login_at: null,
  puede_borrarse: false,
  motivo_no_borrable: 'Vive en otra tabla y se gestiona desde el servidor.',
}

describe('REV.8 — borrar a quien nunca entró', () => {
  it('should_offer_deleting_someone_the_server_says_can_be_deleted', () => {
    renderPage()

    const fila = screen.getByTestId('persona-manual@uji.es')
    expect(within(fila).getByRole('button', { name: /eliminar|borrar/i })).toBeDefined()
  })

  it('should_delete_after_confirming', () => {
    // Con confirmación: es la única acción de esta pantalla que no se puede deshacer.
    renderPage()

    const fila = screen.getByTestId('persona-manual@uji.es')
    fireEvent.click(within(fila).getByRole('button', { name: /eliminar|borrar/i }))
    fireEvent.click(screen.getByRole('button', { name: /confirmar/i }))

    expect(borrar).toHaveBeenCalledWith(
      { userId: '11111111-1111-1111-1111-111111111111' },
      expect.anything()
    )
  })

  it('should_not_delete_if_the_confirmation_is_dismissed', () => {
    renderPage()

    const fila = screen.getByTestId('persona-manual@uji.es')
    fireEvent.click(within(fila).getByRole('button', { name: /eliminar|borrar/i }))
    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }))

    expect(borrar).not.toHaveBeenCalled()
  })

  it('should_say_why_a_row_cannot_be_deleted', () => {
    // No basta con esconder el botón: sin el motivo, la fila se lee como «aquí no se puede
    // hacer nada» y quien administra no sabe si es una regla o un fallo.
    renderPage()

    const fila = screen.getByTestId('persona-porsso@uji.es')
    expect(fila.textContent).toMatch(/ya ha entrado/i)
  })

  it('should_take_the_decision_from_the_server_and_not_from_last_login', () => {
    // **El test del prompt.** Si el React decidiera por `last_login_at`, esa regla viviría en
    // dos sitios. Aquí el servidor dice que NO se puede borrar a alguien que nunca entró —un
    // caso que hoy no se da, pero que llegará el día que haya más motivos— y la pantalla
    // obedece en vez de recalcular.
    conPersonas([
      { ...PERSONAS[0], last_login_at: null, puede_borrarse: false, motivo_no_borrable: 'Da igual el motivo.' },
    ])
    renderPage()

    const fila = screen.getByTestId('persona-manual@uji.es')
    expect(within(fila).queryByRole('button', { name: /eliminar|borrar/i })).toBeNull()
  })
})

describe('REV.8 — el superadministrador de arranque', () => {
  it('should_show_it_in_the_listing', () => {
    conPersonas([SUPERADMIN_DE_ARRANQUE, ...PERSONAS])
    renderPage()

    expect(screen.getByText('root@uji.es')).toBeDefined()
  })

  it('should_not_offer_deleting_or_deactivating_it', () => {
    // Vive en otra tabla: los dos botones darían un 404 y parecerían un fallo.
    conPersonas([SUPERADMIN_DE_ARRANQUE, ...PERSONAS])
    renderPage()

    const fila = screen.getByTestId('persona-root@uji.es')
    expect(within(fila).queryByRole('button', { name: /eliminar|borrar/i })).toBeNull()
    expect(within(fila).queryByRole('button', { name: /desactivar/i })).toBeNull()
  })
})

/**
 * REV.10 — a qué organización pertenece cada persona.
 *
 * `HubUser.organizacion_id` existe con su clave ajena desde AUTH.2 y **la pantalla no lo
 * enseñaba ni lo pedía**: se podía dar de alta a gente sin organización sin enterarse, y no
 * había forma de saber de quién era nadie. El usuario lo dijo así: «en personas no veo el
 * selector de la organización».
 */
describe('REV.10 — la organización de cada persona', () => {
  it('should_show_which_organisation_each_person_belongs_to', () => {
    conPersonas([{ ...PERSONAS[0], organizacion_id: 'org-uji' }])
    renderPage()

    const fila = screen.getByTestId('persona-manual@uji.es')
    expect(fila.textContent).toMatch(/Universitat Jaume I/)
  })

  it('should_say_when_someone_has_no_organisation', () => {
    // Una celda vacía se lee como un dato que falta; esto es una fila que nadie asignó, y hay
    // que poder verla para arreglarla.
    conPersonas([{ ...PERSONAS[0], organizacion_id: null }])
    renderPage()

    const fila = screen.getByTestId('persona-manual@uji.es')
    expect(fila.textContent).toMatch(/sin organización/i)
  })

  it('should_let_the_alta_choose_an_organisation', () => {
    renderPage()

    fireEvent.change(screen.getByLabelText(/correo/i), { target: { value: 'nueva@uji.es' } })
    fireEvent.change(screen.getByLabelText(/^organización/i), { target: { value: 'org-dipu' } })
    fireEvent.click(screen.getByRole('button', { name: /dar de alta/i }))

    expect(mutar).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({ organizacion_id: 'org-dipu' }),
      }),
      expect.anything()
    )
  })

  it('should_default_the_alta_to_the_organisation_chosen_in_the_panel', () => {
    // La elección compartida de REV.10: si ya se está trabajando sobre una organización, el
    // alta no tiene que volver a preguntarlo.
    localStorage.setItem('organizacion-elegida', 'org-dipu')
    renderPage()

    expect((screen.getByLabelText(/^organización/i) as HTMLSelectElement).value).toBe('org-dipu')
  })
})
