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
vi.mock('@/shared/api/generated/auth/auth', () => ({
  useGetMeApiV1AuthMeGet: vi.fn(),
}))

vi.mock('@/shared/api/generated/hub-themes/hub-themes', () => ({
  useGetResolvedThemeApiV1HubThemesResolvedGet: vi.fn(),
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
