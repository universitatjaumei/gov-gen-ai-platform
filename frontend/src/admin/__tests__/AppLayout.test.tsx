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
  it('should_render_three_nav_sections', () => {
    renderLayout()
    expect(screen.getByText('Hub')).toBeDefined()
    expect(screen.getByText('Automatización')).toBeDefined()
    expect(screen.getByText('Plataforma')).toBeDefined()
  })

  it('should_mark_hub_section_active_on_hub_route', () => {
    renderLayout('/hub')
    const hubLink = screen.getByRole('link', { name: /hub/i })
    expect(hubLink.getAttribute('aria-current')).toBe('page')
  })

  it('should_mark_automation_section_active_on_automation_route', () => {
    renderLayout('/automation')
    const link = screen.getByRole('link', { name: /automatización/i })
    expect(link.getAttribute('aria-current')).toBe('page')
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
