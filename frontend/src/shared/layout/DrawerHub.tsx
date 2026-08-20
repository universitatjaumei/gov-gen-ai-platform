import { useEffect } from 'react'
import FocusLock from 'react-focus-lock'
import { useTranslation } from 'react-i18next'
import { useFocusStore } from './useFocusStore'
import { CopilotPanel } from './copilot/CopilotPanel'

/**
 * El cajón de herramientas (INF.8).
 *
 * De las pruebas humanas del 2026-08-20: «El copiloto tiene cuatro tablas de las cuales 3 están
 * totalmente en blanco» y «el cajón lateral debería llevar una aspa».
 *
 * Lo primero era literal: se declaraban cuatro pestañas —Bloques, Datos, IA, Copilot— y solo
 * `copilot` tenía panel. Las otras tres **se retiran**: una pestaña en blanco no es una promesa,
 * es un fallo aparente. Volverán cuando tengan contenido, y entonces será un prompt propio.
 *
 * Lo segundo era peor que estético. El `<aside>` es `role="dialog" aria-modal="true"` dentro de
 * un `FocusLock`, así que el foco quedaba **atrapado** sin ningún control de cierre y sin
 * Escape: con teclado no había forma de salir. Ahora hay aspa, Escape cierra, y al cerrar el
 * foco vuelve a donde estaba (lo hace `returnFocus` del propio FocusLock).
 */
type TabDef = { key: string; clave: string }

/** Las pestañas que **tienen panel**. Si una no lo tiene, no se declara. */
const PESTANAS: TabDef[] = [{ key: 'copilot', clave: 'drawer.copilot' }]

export function DrawerHub() {
  const { t } = useTranslation('redaccion')
  const { drawerVisible, activeTab, setActiveTab, toggleDrawer } = useFocusStore()

  // Escape cierra. Sin esto, un diálogo modal con el foco atrapado y sin salida de teclado es
  // un defecto de accesibilidad, no una decisión de diseño.
  useEffect(() => {
    if (!drawerVisible) return
    function alPulsar(evento: KeyboardEvent) {
      if (evento.key === 'Escape') toggleDrawer()
    }
    window.addEventListener('keydown', alPulsar)
    return () => window.removeEventListener('keydown', alPulsar)
  }, [drawerVisible, toggleDrawer])

  if (!drawerVisible) return null

  return (
    <FocusLock returnFocus>
      <aside
        data-testid="drawer-hub"
        role="dialog"
        aria-modal="true"
        aria-label={t('drawer.aria_label')}
        style={{ width: '420px' }}
        className="fixed right-0 top-0 h-full bg-background border-l shadow-lg z-50 flex flex-col"
      >
        <div className="flex items-center border-b">
          <div role="tablist" className="flex flex-1">
            {PESTANAS.map((pestana) => (
              <button
                key={pestana.key}
                role="tab"
                aria-selected={activeTab === pestana.key}
                className={`px-4 py-2 text-sm border-b-2 transition-colors ${
                  activeTab === pestana.key
                    ? 'border-primary text-primary font-medium'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
                onClick={() => setActiveTab(pestana.key as Parameters<typeof setActiveTab>[0])}
              >
                {t(pestana.clave)}
              </button>
            ))}
          </div>
          <button
            type="button"
            data-testid="btn-cerrar-cajon"
            aria-label={t('drawer.close')}
            onClick={toggleDrawer}
            className="px-3 py-2 text-muted-foreground hover:text-foreground"
          >
            {/* Un aspa dibujada, no el carácter «x»: se ve igual en cualquier tipografía. */}
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
              <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.6" fill="none" />
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-auto" data-testid={`tab-panel-${activeTab}`}>
          {activeTab === 'copilot' && <CopilotPanel />}
        </div>
      </aside>
    </FocusLock>
  )
}
