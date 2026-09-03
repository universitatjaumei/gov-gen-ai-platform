import { describe, it, expect, beforeEach, beforeAll, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { AppLayout } from '../AppLayout'
import { HubLayout } from '../HubLayout'
import { PlataformaLayout } from '../PlataformaLayout'
import { useGetMeApiV1AuthMeGet } from '@/shared/api/generated/auth/auth'
import { useGetResolvedThemeApiV1HubThemesResolvedGet } from '@/shared/api/generated/hub-themes/hub-themes'
import { useListOrganizacionesApiV1HubOrganizacionesGet } from '@/shared/api/generated/hub-organizaciones/hub-organizaciones'

/**
 * REV.3 — cómo se marca la opción activa en los tres menús.
 *
 * Los tres la pintaban con un recuadro de fondo (`bg-sidebar-accent` en el lateral, `bg-accent`
 * en las dos barras de pestañas). El recuadro compite con el contenido y, en el lateral, mete
 * un segundo azul dentro del azul de la marca.
 *
 * Lo que se fija aquí es el criterio, no el color exacto: **negrita más una barra del color del
 * propio texto** —lateral a la izquierda, pestañas debajo—, y ningún relleno. La barra se
 * reserva también en los inactivos con `border-transparent`, porque si sólo la tuviera el
 * activo el menú entero se desplazaría al cambiar de sección.
 */
// USR.7 — el menú de la cuenta lleva el formulario de la propia contraseña, así que el
// layout consulta también esa mutación. Sin ella en el doble, el componente llama a
// `undefined` y no monta nada: los rojos parecen de esta pantalla y son del doble.
vi.mock('@/shared/api/generated/auth/auth', () => ({
  useGetMeApiV1AuthMeGet: vi.fn(),
  useCambiarMiPassword: () => ({ mutate: vi.fn(), isPending: false, isError: false }),
}))

vi.mock('@/shared/api/generated/hub-themes/hub-themes', () => ({
  useGetResolvedThemeApiV1HubThemesResolvedGet: vi.fn(),
}))

vi.mock('@/shared/api/generated/hub-organizaciones/hub-organizaciones', () => ({
  useListOrganizacionesApiV1HubOrganizacionesGet: vi.fn(),
}))

const TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ user_id: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_') +
  '.signature'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  localStorage.setItem('access_token', TOKEN)
  vi.mocked(useGetMeApiV1AuthMeGet).mockReturnValue({
    data: { modulos: ['chatbots', 'curacion', 'informes', 'plataforma'] },
    isLoading: false,
  } as never)
  vi.mocked(useGetResolvedThemeApiV1HubThemesResolvedGet).mockReturnValue({
    data: { config: {} },
    isLoading: false,
  } as never)
  vi.mocked(useListOrganizacionesApiV1HubOrganizacionesGet).mockReturnValue({ data: [] } as never)
})

function activo(nombre: RegExp): HTMLElement {
  const enlace = screen.getByRole('link', { name: nombre })
  expect(enlace.getAttribute('aria-current')).toBe('page')
  return enlace
}

describe('REV.3 — la opción activa se marca con negrita y barra, no con un recuadro', () => {
  it('should_not_fill_the_active_item_of_the_sidebar', () => {
    render(
      <MemoryRouter initialEntries={['/hub']}>
        <AuthProvider>
          <AppLayout />
        </AuthProvider>
      </MemoryRouter>
    )

    const clases = activo(/chatbots/i).className
    expect(clases).not.toMatch(/bg-sidebar-accent(?!\/)/)
    expect(clases).toMatch(/font-semibold/)
    expect(clases).toMatch(/border-l-2/)
    expect(clases).toMatch(/border-current/)
  })

  it('should_reserve_the_bar_on_the_inactive_items_of_the_sidebar', () => {
    // Sin reservarla, entrar en una sección desplaza el menú entero unos píxeles.
    render(
      <MemoryRouter initialEntries={['/hub']}>
        <AuthProvider>
          <AppLayout />
        </AuthProvider>
      </MemoryRouter>
    )

    const inactivo = screen.getByRole('link', { name: /curación/i })
    expect(inactivo.getAttribute('aria-current')).toBeNull()
    expect(inactivo.className).toMatch(/border-l-2/)
    expect(inactivo.className).toMatch(/border-transparent/)
    expect(inactivo.className).not.toMatch(/font-semibold/)
  })

  it('should_underline_the_active_tab_of_the_chatbots_subnav', () => {
    render(
      <MemoryRouter initialEntries={['/hub/documents']}>
        <Routes>
          <Route path="/hub" element={<HubLayout />}>
            <Route path="documents" element={<div />} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    const clases = activo(/documentos/i).className
    expect(clases).not.toMatch(/bg-accent(?!\/)/)
    expect(clases).toMatch(/font-semibold/)
    expect(clases).toMatch(/border-b-2/)
    expect(clases).toMatch(/border-current/)
  })

  it('should_underline_the_active_tab_of_the_platform_subnav', () => {
    render(
      <MemoryRouter initialEntries={['/plataforma/usuarios']}>
        <Routes>
          <Route path="/plataforma" element={<PlataformaLayout />}>
            <Route path="usuarios" element={<div />} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    const clases = activo(/personas|usuarios/i).className
    expect(clases).not.toMatch(/bg-accent(?!\/)/)
    expect(clases).toMatch(/font-semibold/)
    expect(clases).toMatch(/border-b-2/)
    expect(clases).toMatch(/border-current/)
  })
})

/**
 * REV.10 — el selector de organización, en la cabecera y una sola vez.
 *
 * Cada pantalla lo resolvía a su manera: «Valores por defecto» con su propio selector,
 * «Identidad visual» con otro, Vigencia por *chatbot*, Personas sin ninguno. Cambiar de
 * organización obligaba a repetir la elección pantalla por pantalla.
 */
describe('REV.10 — la organización se elige una vez', () => {
  function pintarConOrganizaciones(lista: { id: string; name: string }[]) {
    vi.mocked(useListOrganizacionesApiV1HubOrganizacionesGet).mockReturnValue({
      data: lista,
    } as never)
    return render(
      <MemoryRouter initialEntries={['/hub']}>
        <AuthProvider>
          <AppLayout />
        </AuthProvider>
      </MemoryRouter>
    )
  }

  it('should_offer_the_selector_in_the_sidebar', () => {
    pintarConOrganizaciones([
      { id: 'org-uji', name: 'Universitat Jaume I' },
      { id: 'org-dipu', name: 'Diputación de Castellón' },
    ])

    const selector = screen.getByLabelText(/organización/i)
    expect([...selector.querySelectorAll('option')].map(o => o.textContent)).toEqual([
      'Universitat Jaume I',
      'Diputación de Castellón',
    ])
  })

  it('should_not_show_it_with_a_single_organisation', () => {
    // Con una sola, un selector es ruido: es el mismo criterio que el buscador de REV.7.
    pintarConOrganizaciones([{ id: 'org-uji', name: 'Universitat Jaume I' }])

    expect(screen.queryByLabelText(/organización/i)).toBeNull()
  })
})

/**
 * REV.11 — Organizaciones no es del módulo Chatbots.
 *
 * `hub_organizaciones_router` protege crear, editar y borrar con `require_module("plataforma")`
 * y sólo los valores por defecto con `chatbots` (PLAT.5). Pero la pantalla vivía en
 * `/hub/organizaciones`, bajo `HubLayout`, que exige `chatbots`: **quien tenía `plataforma` y no
 * `chatbots` no llegaba a la pantalla que su propio módulo protege**. Es el caso de «Modelos
 * LLM» que arregló PLAT.2, que se quedó sin mover porque entonces nadie miró esta pantalla.
 *
 * Y el argumento de fondo: la organización sirve al resto de los módulos, así que darla de alta
 * es una operación general y no del módulo de asistentes.
 */
describe('REV.11 — Organizaciones vive en Plataforma', () => {
  it('should_offer_it_in_the_platform_subnav', () => {
    render(
      <MemoryRouter initialEntries={['/plataforma/organizaciones']}>
        <Routes>
          <Route path="/plataforma" element={<PlataformaLayout />}>
            <Route path="organizaciones" element={<div />} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByRole('link', { name: /organizaciones/i })).toBeDefined()
  })

  it('should_not_leave_it_in_the_chatbots_subnav', () => {
    render(
      <MemoryRouter initialEntries={['/hub/chatbots']}>
        <Routes>
          <Route path="/hub" element={<HubLayout />}>
            <Route path="chatbots" element={<div />} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    expect(screen.queryByRole('link', { name: /organizaciones/i })).toBeNull()
  })
})
