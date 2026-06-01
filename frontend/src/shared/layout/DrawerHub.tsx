import FocusLock from 'react-focus-lock'
import { useFocusStore } from './useFocusStore'
import { CopilotPanel } from './copilot/CopilotPanel'

type TabDef = { key: string; label: string }

const INFORME_TABS: TabDef[] = [
  { key: 'blocks', label: 'Bloques' },
  { key: 'data', label: 'Datos' },
  { key: 'ai', label: 'IA' },
  { key: 'copilot', label: 'Copilot' },
]

const FLUJO_TABS: TabDef[] = [
  { key: 'config', label: 'Configuración' },
  { key: 'pills', label: 'Data Pills' },
  { key: 'copilot', label: 'Copilot' },
]

export function DrawerHub() {
  const { drawerVisible, context, activeTab, setActiveTab } = useFocusStore()

  if (!drawerVisible) return null

  const tabs = context?.type === 'flujo' ? FLUJO_TABS : INFORME_TABS

  return (
    <FocusLock returnFocus>
      <aside
        data-testid="drawer-hub"
        role="dialog"
        aria-modal="true"
        aria-label="Panel de herramientas"
        style={{ width: '420px' }}
        className="fixed right-0 top-0 h-full bg-background border-l shadow-lg z-50 flex flex-col"
      >
        <div role="tablist" className="flex border-b">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              role="tab"
              aria-selected={activeTab === tab.key}
              className={`px-4 py-2 text-sm border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-primary text-primary font-medium'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setActiveTab(tab.key as Parameters<typeof setActiveTab>[0])}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-auto" data-testid={`tab-panel-${activeTab}`}>
          {activeTab === 'copilot' && <CopilotPanel />}
        </div>
      </aside>
    </FocusLock>
  )
}
