import { describe, it, expect, beforeEach, beforeAll } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { AppLayout } from '../AppLayout'

const TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ user_id: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  localStorage.setItem('access_token', TOKEN)
})

function renderLayout(path = '/hub') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <AppLayout />
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('AppLayout', () => {
  it('should_render_the_three_things_the_platform_does', () => {
    // «Automatización» y «Plataforma» eran pantallas vacías: un menú que promete lo que no
    // hay es peor que un menú corto. «Informes» estaba construido y fuera de todo menú.
    renderLayout()
    expect(screen.getByText('Chatbots')).toBeDefined()
    expect(screen.getByText('Informes')).toBeDefined()
    expect(screen.getByText('Curación')).toBeDefined()
    expect(screen.queryByText('Automatización')).toBeNull()
    expect(screen.queryByText('Plataforma')).toBeNull()
  })

  it('should_mark_chatbots_section_active_on_hub_route', () => {
    renderLayout('/hub')
    const enlace = screen.getByRole('link', { name: /chatbots/i })
    expect(enlace.getAttribute('aria-current')).toBe('page')
  })

  it('should_mark_reports_section_active_on_redaccion_route', () => {
    renderLayout('/redaccion')
    const enlace = screen.getByRole('link', { name: /informes/i })
    expect(enlace.getAttribute('aria-current')).toBe('page')
  })

  it('should_let_the_user_change_the_language', async () => {
    // El panel se traducía a tres idiomas y no había forma de elegir: dependías de lo que
    // dijera el navegador.
    renderLayout()
    const selector = screen.getByLabelText('Idioma') as HTMLSelectElement

    expect(selector.value).toBe('es')
    expect(screen.getByRole('option', { name: 'Valencià' })).toBeDefined()
    expect(screen.getByRole('option', { name: 'English' })).toBeDefined()
  })

  it('should_render_outlet_content_area', () => {
    renderLayout()
    expect(screen.getByRole('main')).toBeDefined()
  })

  it('should_show_user_email_in_sidebar', () => {
    renderLayout()
    expect(screen.getByText('admin@test.com')).toBeDefined()
  })

  it('should_have_logout_button', () => {
    renderLayout()
    expect(screen.getByRole('button', { name: /cerrar sesión/i })).toBeDefined()
  })
})
