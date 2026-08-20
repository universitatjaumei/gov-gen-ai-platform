import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { useFocusStore } from '../useFocusStore'
import { DrawerHub } from '../DrawerHub'
import { FocusLayout } from '../FocusLayout'

describe('useFocusStore', () => {
  beforeEach(() => {
    act(() => useFocusStore.getState().reset())
  })

  it('should_set_focus_mode_on_mount_and_reset_on_unmount', () => {
    const { unmount } = render(
      <FocusLayout context={{ type: 'informe', entityId: 'ws-123' }}>
        <div>contenido</div>
      </FocusLayout>,
    )

    expect(useFocusStore.getState().viewMode).toBe('focus')
    expect(useFocusStore.getState().context?.entityId).toBe('ws-123')

    unmount()

    expect(useFocusStore.getState().viewMode).toBe('standard')
    expect(useFocusStore.getState().context).toBeNull()
  })

  /**
   * INF.8 — estos dos tests exigían que existieran las pestañas «Bloques», «Datos», «IA»,
   * «Configuración» y «Data Pills», y **ninguna tenía panel**: `DrawerHub` solo pintaba
   * contenido para `copilot`. O sea que codificaban el defecto que el usuario reportó —«el
   * copiloto tiene cuatro tablas de las cuales 3 están totalmente en blanco»— como
   * comportamiento correcto.
   *
   * Lo que se comprueba ahora es la regla: no se declara una pestaña sin panel. Cuando alguna
   * de esas vistas exista, volverá con su test.
   */
  it('should_only_declare_tabs_that_have_a_panel', () => {
    act(() => {
      useFocusStore.getState().setContext({ type: 'informe', entityId: 'ws-1' })
      useFocusStore.getState().toggleDrawer()
    })

    render(<DrawerHub />)

    expect(screen.getAllByRole('tab')).toHaveLength(1)
    expect(screen.getByRole('tab', { name: /copilot/i })).toBeInTheDocument()
    for (const ausente of [/bloques/i, /datos/i, /data pills/i, /configuraci/i]) {
      expect(screen.queryByRole('tab', { name: ausente })).not.toBeInTheDocument()
    }
  })

  it('should_offer_the_copilot_in_both_contexts', () => {
    act(() => {
      useFocusStore.getState().setContext({ type: 'flujo', entityId: 'flow-1' })
      useFocusStore.getState().toggleDrawer()
    })

    render(<DrawerHub />)

    expect(screen.getByRole('tab', { name: /copilot/i })).toBeInTheDocument()
  })

  it('should_collapse_sidebar_when_view_mode_is_focus', () => {
    const { container } = render(
      <FocusLayout context={{ type: 'informe', entityId: 'ws-1' }}>
        <div>contenido</div>
      </FocusLayout>,
    )

    const layoutWrapper = container.querySelector('[data-testid="focus-layout"]')
    expect(layoutWrapper).toHaveClass('sidebar-collapsed')
  })

  it('should_toggle_drawer_visibility', () => {
    expect(useFocusStore.getState().drawerVisible).toBe(false)
    act(() => useFocusStore.getState().toggleDrawer())
    expect(useFocusStore.getState().drawerVisible).toBe(true)
    act(() => useFocusStore.getState().toggleDrawer())
    expect(useFocusStore.getState().drawerVisible).toBe(false)
  })
})
