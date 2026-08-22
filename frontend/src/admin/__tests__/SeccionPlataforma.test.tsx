import { describe, it, expect, beforeEach, beforeAll, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route, Navigate } from 'react-router-dom'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { RutaDeModulo, Aterrizaje, SinAcceso } from '@/shared/auth/RutaDeModulo'
import { AppLayout } from '../AppLayout'
import { PlataformaLayout } from '../PlataformaLayout'
import { primeraRutaConcedida, RUTA_DEL_MODULO } from '@/shared/auth/useModulos'
import { useGetMeApiV1AuthMeGet } from '@/shared/api/generated/auth/auth'
import { useGetResolvedThemeApiV1HubThemesResolvedGet } from '@/shared/api/generated/hub-themes/hub-themes'

/**
 * PLAT.2 — la administración de la plataforma deja de vivir dentro del módulo Chatbots.
 *
 * El módulo `plataforma` estaba en `MODULOS_INICIALES` desde INF.7, se podía conceder y **no
 * abría nada**: se retiró del menú porque llevaba a un `PlaceholderPage`. Mientras tanto, tres
 * pantallas que no son de Chatbots vivían bajo `/hub`, que exige el módulo `chatbots`:
 *
 * - «Modelos LLM», cuyo router **ya declara** `require_module("plataforma")`. Así que quien
 *   tenía `chatbots` y no `plataforma` veía el tab y recibía un 403, y quien tenía `plataforma`
 *   no podía llegar a la única pantalla que su módulo protege.
 * - «Prompts de actividad», que por definición no cuelgan de ningún chatbot (PRO.2.1).
 * - «Tokens de acceso», que son credenciales de máquina de la plataforma.
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

function conModulos(modulos: string[]) {
  vi.mocked(useGetMeApiV1AuthMeGet).mockReturnValue({
    data: { modulos },
    isLoading: false,
  } as never)
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  localStorage.setItem('access_token', TOKEN)
  vi.mocked(useGetResolvedThemeApiV1HubThemesResolvedGet).mockReturnValue({
    data: { config: {} },
    isLoading: false,
  } as never)
})

/** Árbol mínimo con las dos zonas, para poder comprobar el corte de `RutaDeModulo`. */
function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<Aterrizaje />} />
            <Route path="/sin-acceso" element={<SinAcceso />} />
            <Route
              path="/plataforma"
              element={
                <RutaDeModulo modulo="plataforma">
                  <PlataformaLayout />
                </RutaDeModulo>
              }
            >
              <Route index element={<Navigate to="/plataforma/modelos" replace />} />
              <Route path="modelos" element={<p>pantalla de modelos</p>} />
              <Route path="prompts-actividad" element={<p>pantalla de prompts de actividad</p>} />
              <Route path="tokens" element={<p>pantalla de tokens</p>} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('PLAT.2 — la sección Plataforma en el menú principal', () => {
  it('should_show_the_section_when_the_module_is_granted', () => {
    conModulos(['chatbots', 'plataforma'])
    renderApp('/plataforma/modelos')

    expect(screen.getByRole('link', { name: /plataforma/i })).toBeDefined()
  })

  it('should_not_show_the_section_without_the_module', () => {
    // El menú se genera con lo que concede el servidor: sin concesión, no hay entrada.
    conModulos(['chatbots'])
    renderApp('/sin-acceso')

    expect(screen.queryByRole('link', { name: /plataforma/i })).toBeNull()
  })
})

describe('PLAT.2 — las tres pantallas dejan de depender del módulo Chatbots', () => {
  it('should_open_modelos_with_plataforma_and_without_chatbots', () => {
    // Es el caso que hoy es imposible: la pantalla vive bajo `/hub`, que exige `chatbots`.
    conModulos(['plataforma'])
    renderApp('/plataforma/modelos')

    expect(screen.getByText('pantalla de modelos')).toBeDefined()
  })

  it('should_open_prompts_de_actividad_with_plataforma_only', () => {
    conModulos(['plataforma'])
    renderApp('/plataforma/prompts-actividad')

    expect(screen.getByText('pantalla de prompts de actividad')).toBeDefined()
  })

  it('should_open_tokens_with_plataforma_only', () => {
    conModulos(['plataforma'])
    renderApp('/plataforma/tokens')

    expect(screen.getByText('pantalla de tokens')).toBeDefined()
  })

  it('should_cut_the_section_for_someone_with_chatbots_but_not_plataforma', () => {
    conModulos(['chatbots'])
    renderApp('/plataforma/modelos')

    expect(screen.queryByText('pantalla de modelos')).toBeNull()
    expect(screen.getByTestId('sin-acceso')).toBeDefined()
  })
})

describe('PLAT.2 — el aterrizaje conoce la sección', () => {
  it('should_land_on_plataforma_for_someone_who_only_has_that_module', () => {
    // Sin esto, quien solo administra la plataforma aterriza en `/sin-acceso` teniendo acceso.
    expect(primeraRutaConcedida(['plataforma'])).toBe('/plataforma')
  })

  it('should_keep_plataforma_last_in_the_landing_order', () => {
    // Quien tenga informes y plataforma entra a trabajar, no a configurar.
    const codigos = RUTA_DEL_MODULO.map(([codigo]) => codigo)
    expect(codigos).toContain('plataforma')
    expect(codigos[codigos.length - 1]).toBe('plataforma')
  })

  it('should_render_the_landing_redirect_for_a_plataforma_only_account', () => {
    conModulos(['plataforma'])
    renderApp('/')

    expect(screen.getByText('pantalla de modelos')).toBeDefined()
  })
})

describe('PLAT.2 — la subnavegación de la sección', () => {
  it('should_link_the_three_screens_that_moved', () => {
    conModulos(['plataforma'])
    renderApp('/plataforma/modelos')

    const enlaces = screen.getAllByRole('link').map((a) => a.getAttribute('href'))
    expect(enlaces).toContain('/plataforma/modelos')
    expect(enlaces).toContain('/plataforma/prompts-actividad')
    expect(enlaces).toContain('/plataforma/tokens')
  })

  it('should_mark_the_active_tab', () => {
    conModulos(['plataforma'])
    renderApp('/plataforma/tokens')

    // Se acota a la subnavegación a propósito: el enlace de la sección en el menú principal
    // también lleva `aria-current`, porque un `NavLink` sin `end` marca la ruta padre. Es el
    // mismo comportamiento que ya tienen Chatbots y Curación, así que no hay nada que cambiar.
    const subnav = screen.getByRole('navigation', {
      name: 'Navegación de la administración de la plataforma',
    })
    const activo = [...subnav.querySelectorAll('a')].find(
      (a) => a.getAttribute('aria-current') === 'page'
    )
    expect(activo?.getAttribute('href')).toBe('/plataforma/tokens')
  })
})
