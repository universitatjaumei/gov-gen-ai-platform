/**
 * ROL.2 — Renombrado institucional en el frontend.
 *
 * Verifica la propagación del renombrado (superadmin|admin|user, Organización):
 * claves i18n renombradas sin labels hardcodeados, ruta /organizaciones en el
 * sub-nav del Hub, y el techo de capacidad por rol (superadmin=plataforma,
 * admin=organización, user=oculto). Las secciones de ruta gateadas por rol no
 * existen como infraestructura separada; el gating real vive en el techo de
 * scopes (`scopesForRole`) y en los checks de las páginas.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import esAdmin from '@/shared/i18n/locales/es/admin.json'
import { scopesForRole } from '@/admin/pages/AccessTokensPage'
import { HubLayout } from '@/admin/HubLayout'

describe('ROL.2 — i18n keys', () => {
  it('should_use_i18n_keys_not_hardcoded_role_labels', () => {
    // `as unknown` primero: el JSON tiene claves anidadas (test_scenarios) y el tipo
    // inferido no solapa con Record<string, string>. Aquí sólo se leen claves planas.
    const hub = (esAdmin as unknown as { hub: Record<string, string> }).hub
    // Claves renombradas presentes…
    expect(hub.organizaciones).toBeDefined()
    expect(hub.new_organizacion).toBeDefined()
    expect(hub.organizacion_admin).toBeDefined()
    // …y las antiguas ausentes (sin strings sueltos con nomenclatura vieja).
    expect(hub.clients).toBeUndefined()
    expect(hub.client_partner).toBeUndefined()
    expect(hub.new_client).toBeUndefined()
    // El label del gestor ya no dice "Partner".
    expect(hub.organizacion_admin).not.toMatch(/partner/i)
  })
})

describe('ROL.2 — routing / navegación por Organización', () => {
  it('should_expose_organizaciones_route_not_clients', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/hub/chatbots']}>
        <Routes>
          <Route path="/hub" element={<HubLayout />}>
            <Route path="chatbots" element={<div>stub</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(container.querySelector('a[href="/hub/organizaciones"]')).not.toBeNull()
    expect(container.querySelector('a[href="/hub/clients"]')).toBeNull()
  })
})

describe('ROL.2 — techo de capacidad por rol', () => {
  it('should_route_superadmin_to_platform_section', () => {
    // superadmin = capacidad de plataforma (todos los scopes).
    expect(scopesForRole('superadmin')).toContain('chatbots:write')
    expect(scopesForRole('superadmin').length).toBeGreaterThan(0)
  })

  it('should_route_admin_to_org_scoped_section', () => {
    // admin (ex-partner) = capacidad de organización, sin mutar chatbots en prod.
    const admin = scopesForRole('admin')
    expect(admin.length).toBeGreaterThan(0)
    expect(admin).not.toContain('chatbots:write')
  })

  it('should_hide_platform_admin_from_user_role', () => {
    expect(scopesForRole('user')).toEqual([])
    // 'partner' ya no existe como rol → sin capacidades.
    expect(scopesForRole('partner')).toEqual([])
  })
})
