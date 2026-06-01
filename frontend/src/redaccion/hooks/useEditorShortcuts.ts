import { useEffect } from 'react'

export interface EditorShortcutHandlers {
  isDrawerOpen: boolean
  hasActiveBlock: boolean
  activeBlockState: string | null
  onCloseDrawer: () => void
  onLeaveFocusMode: () => void
  onForceSave: () => void
  onApproveActiveBlock: () => void
  onUndo: () => void
}

export function useEditorShortcuts(handlers: EditorShortcutHandlers): void {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent): void {
      if (e.key === 'Escape') {
        if (handlers.isDrawerOpen) {
          handlers.onCloseDrawer()
        } else {
          handlers.onLeaveFocusMode()
        }
        return
      }

      const mod = e.metaKey || e.ctrlKey

      if (mod && e.key.toLowerCase() === 's') {
        e.preventDefault()
        handlers.onForceSave()
        return
      }

      if (mod && e.key === 'Enter') {
        if (handlers.hasActiveBlock && handlers.activeBlockState === 'needs_review') {
          handlers.onApproveActiveBlock()
        }
        return
      }

      if (mod && e.key.toLowerCase() === 'z') {
        if (handlers.hasActiveBlock) {
          handlers.onUndo()
        }
        return
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handlers])
}
