import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { useEditorShortcuts } from '../useEditorShortcuts'

function Harness({ handlers }: { handlers: Parameters<typeof useEditorShortcuts>[0] }) {
  useEditorShortcuts(handlers)
  return <div data-testid="harness" />
}

describe('useEditorShortcuts', () => {
  it('should_close_drawer_on_escape_when_drawer_is_open', () => {
    const handlers = {
      isDrawerOpen: true,
      hasActiveBlock: false,
      activeBlockState: null,
      onCloseDrawer: vi.fn(),
      onLeaveFocusMode: vi.fn(),
      onForceSave: vi.fn(),
      onApproveActiveBlock: vi.fn(),
      onUndo: vi.fn(),
    }
    render(<Harness handlers={handlers} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(handlers.onCloseDrawer).toHaveBeenCalled()
    expect(handlers.onLeaveFocusMode).not.toHaveBeenCalled()
  })

  it('should_leave_focus_mode_on_escape_when_drawer_closed', () => {
    const handlers = {
      isDrawerOpen: false,
      hasActiveBlock: false,
      activeBlockState: null,
      onCloseDrawer: vi.fn(),
      onLeaveFocusMode: vi.fn(),
      onForceSave: vi.fn(),
      onApproveActiveBlock: vi.fn(),
      onUndo: vi.fn(),
    }
    render(<Harness handlers={handlers} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(handlers.onLeaveFocusMode).toHaveBeenCalled()
  })

  it('should_call_force_save_on_cmd_s_and_prevent_default', () => {
    const handlers = {
      isDrawerOpen: false,
      hasActiveBlock: false,
      activeBlockState: null,
      onCloseDrawer: vi.fn(),
      onLeaveFocusMode: vi.fn(),
      onForceSave: vi.fn(),
      onApproveActiveBlock: vi.fn(),
      onUndo: vi.fn(),
    }
    render(<Harness handlers={handlers} />)
    const ev = new KeyboardEvent('keydown', { key: 's', metaKey: true, cancelable: true })
    const prevented = !window.dispatchEvent(ev)
    expect(handlers.onForceSave).toHaveBeenCalled()
    expect(prevented).toBe(true)
  })

  it('should_approve_active_block_on_cmd_enter_when_state_is_needs_review', () => {
    const handlers = {
      isDrawerOpen: false,
      hasActiveBlock: true,
      activeBlockState: 'needs_review' as const,
      onCloseDrawer: vi.fn(),
      onLeaveFocusMode: vi.fn(),
      onForceSave: vi.fn(),
      onApproveActiveBlock: vi.fn(),
      onUndo: vi.fn(),
    }
    render(<Harness handlers={handlers} />)
    fireEvent.keyDown(window, { key: 'Enter', metaKey: true })
    expect(handlers.onApproveActiveBlock).toHaveBeenCalled()
  })

  it('should_not_approve_block_on_cmd_enter_when_state_is_draft', () => {
    const handlers = {
      isDrawerOpen: false,
      hasActiveBlock: true,
      activeBlockState: 'draft' as const,
      onCloseDrawer: vi.fn(),
      onLeaveFocusMode: vi.fn(),
      onForceSave: vi.fn(),
      onApproveActiveBlock: vi.fn(),
      onUndo: vi.fn(),
    }
    render(<Harness handlers={handlers} />)
    fireEvent.keyDown(window, { key: 'Enter', metaKey: true })
    expect(handlers.onApproveActiveBlock).not.toHaveBeenCalled()
  })
})
