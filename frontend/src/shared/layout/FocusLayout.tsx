import { ReactNode, useEffect } from 'react'
import { useFocusStore } from './useFocusStore'
import { DrawerHub } from './DrawerHub'

interface FocusLayoutProps {
  children: ReactNode
  context: {
    type: 'informe' | 'flujo'
    entityId: string
  }
}

export function FocusLayout({ children, context }: FocusLayoutProps) {
  const { setContext, setViewMode, reset, viewMode } = useFocusStore()

  useEffect(() => {
    setContext(context)
    setViewMode('focus')
    return () => {
      reset()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      data-testid="focus-layout"
      className={viewMode === 'focus' ? 'sidebar-collapsed' : ''}
    >
      {children}
      <DrawerHub />
    </div>
  )
}
