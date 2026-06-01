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

  it('should_render_informe_tabs_when_context_type_is_informe', () => {
    act(() => {
      useFocusStore.getState().setContext({ type: 'informe', entityId: 'ws-1' })
      useFocusStore.getState().toggleDrawer()
    })

    render(<DrawerHub />)

    expect(screen.getByRole('tab', { name: /bloques/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /datos/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /ia/i })).toBeInTheDocument()
    // 1C.0.bis añade tab Copilot también al contexto 'informe'
    expect(screen.getByRole('tab', { name: /copilot/i })).toBeInTheDocument()
    // Tabs específicas del flujo siguen sin aparecer
    expect(screen.queryByRole('tab', { name: /data pills/i })).not.toBeInTheDocument()
  })

  it('should_render_flujo_tabs_when_context_type_is_flujo', () => {
    act(() => {
      useFocusStore.getState().setContext({ type: 'flujo', entityId: 'flow-1' })
      useFocusStore.getState().toggleDrawer()
    })

    render(<DrawerHub />)

    expect(screen.getByRole('tab', { name: /configuraci/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /data pills/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /copilot/i })).toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /bloques/i })).not.toBeInTheDocument()
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
