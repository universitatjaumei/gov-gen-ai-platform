import { describe, it, expect, beforeEach, beforeAll, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { AppLayout } from '../AppLayout'
import { useGetMeApiV1AuthMeGet } from '@/shared/api/generated/auth/auth'
import { useGetResolvedThemeApiV1HubThemesResolvedGet } from '@/shared/api/generated/hub-themes/hub-themes'

/**
 * La marca del panel viene del servidor, no del repositorio.
 *
 * `AppLayout` hacía `import logoUji from '@/assets/logo-uji.png'` y pintaba el logotipo de
 * la Universitat Jaume I con `alt="Universitat Jaume I"`. En un proyecto multiorganización
 * eso significa que cualquier ayuntamiento que clonara el repositorio arrancaba con la
 * marca de una universidad ajena en su barra lateral — y había una excepción en
 * `.gitignore` más un guardarraíl en integración continua que garantizaban que ese fichero
 * viajase.
 *
 * Ahora la marca la resuelve la cascada visual del servidor (plataforma → organización) y
 * el panel solo la pinta. Es el mismo reparto que `acciones_permitidas` o que los módulos
 * concedidos: el servidor decide, el cliente pinta.
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

function conMarca(branding: Record<string, unknown> | undefined) {
  vi.mocked(useGetResolvedThemeApiV1HubThemesResolvedGet).mockReturnValue({
    data: { config: branding === undefined ? {} : { branding } },
    isLoading: false,
  } as never)
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  localStorage.setItem('access_token', TOKEN)
  vi.mocked(useGetMeApiV1AuthMeGet).mockReturnValue({
    data: { modulos: ['chatbots', 'curacion', 'informes'] },
    isLoading: false,
  } as never)
  conMarca(undefined)
})

function renderLayout() {
  return render(
    <MemoryRouter initialEntries={['/hub']}>
      <AuthProvider>
        <AppLayout />
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('la marca del panel la decide el servidor', () => {
  it('should_paint_the_logo_that_the_cascade_resolves', () => {
    conMarca({ logoUrl: '/api/v1/hub/themes/abc/logo', logoAlt: 'Ayuntamiento de Vila-real' })
    renderLayout()

    const logo = screen.getByRole('img', { name: 'Ayuntamiento de Vila-real' })
    expect(logo.getAttribute('src')).toBe('/api/v1/hub/themes/abc/logo')
  })

  it('should_fall_back_to_the_platform_name_when_there_is_no_logo', () => {
    // Sin marca configurada no se pinta un hueco ni el logotipo de nadie: se pone el
    // nombre de la plataforma, que ya está traducido.
    renderLayout()

    expect(screen.getByText('Gov Gen AI Platform')).toBeDefined()
    expect(screen.queryByRole('img')).toBeNull()
  })

  it('should_use_the_platform_name_as_alt_text_when_the_mark_has_no_alt', () => {
    // Un logotipo sin texto alternativo es una imagen muda para un lector de pantalla, y
    // el `alt` lo rellena quien sube la marca: puede no venir.
    conMarca({ logoUrl: '/api/v1/hub/themes/abc/logo' })
    renderLayout()

    expect(screen.getByRole('img', { name: 'Gov Gen AI Platform' })).toBeDefined()
  })

  it('should_not_paint_any_institution_mark_bundled_with_the_code', () => {
    // El guardarraíl del cambio: mientras el logotipo salga de un `import`, la marca viaja
    // en el bundle y es la misma para todos los despliegues.
    conMarca({ logoUrl: '/api/v1/hub/themes/abc/logo', logoAlt: 'Quien sea' })
    renderLayout()

    const src = screen.getByRole('img').getAttribute('src') ?? ''
    expect(src.startsWith('/api/')).toBe(true)
    expect(src).not.toMatch(/assets|logo-uji/)
  })
})
