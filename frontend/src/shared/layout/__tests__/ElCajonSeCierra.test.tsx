import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import i18n from '@/shared/i18n'
import { DrawerHub } from '../DrawerHub'
import { useFocusStore } from '../useFocusStore'

/**
 * INF.8 — el cajón se puede cerrar, y no promete pestañas que no existen.
 *
 * De las pruebas humanas del 2026-08-20: «El copiloto tiene cuatro tablas de las cuales 3 están
 * totalmente en blanco» y «el cajón lateral debería llevar una aspa». Lo segundo era peor que
 * estético: el `<aside>` es `role="dialog" aria-modal` dentro de un `FocusLock`, así que el foco
 * quedaba atrapado sin ningún control de cierre y sin Escape.
 */
vi.mock('../copilot/CopilotPanel', () => ({
  CopilotPanel: () => <div data-testid="panel-copiloto" />,
}))

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  useFocusStore.setState({ drawerVisible: true, activeTab: 'copilot', context: null })
})

describe('INF.8 — el cajón', () => {
  it('should_offer_a_close_control', () => {
    render(<DrawerHub />)
    expect(screen.getByTestId('btn-cerrar-cajon')).toBeDefined()
  })

  it('should_close_when_the_close_control_is_pressed', () => {
    render(<DrawerHub />)
    fireEvent.click(screen.getByTestId('btn-cerrar-cajon'))
    expect(useFocusStore.getState().drawerVisible).toBe(false)
  })

  it('should_close_with_escape', () => {
    render(<DrawerHub />)
    fireEvent.keyDown(window, { key: 'Escape' })
    // Sin esto, con teclado no había forma de salir del cajón.
    expect(useFocusStore.getState().drawerVisible).toBe(false)
  })

  it('should_not_declare_tabs_without_a_panel', () => {
    render(<DrawerHub />)
    const pestanas = screen.getAllByRole('tab')
    // Se declaraban cuatro y solo una tenía contenido. Una pestaña en blanco no es una
    // promesa, es un fallo aparente.
    expect(pestanas).toHaveLength(1)
    expect(screen.getByTestId('panel-copiloto')).toBeDefined()
  })

  it('should_not_leave_hardcoded_spanish_in_the_drawer', async () => {
    render(<DrawerHub />)
    await i18n.changeLanguage('en')
    expect(screen.queryByLabelText('Panel de herramientas')).toBeNull()
    await i18n.changeLanguage('es')
  })
})
