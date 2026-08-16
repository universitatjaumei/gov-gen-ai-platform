import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

/**
 * Navegación de Informes.
 *
 * Las pantallas existían desde 9R —plantillas, asistente de informe, borrador con LLM y la
 * cola de revisión de scripts— pero **sus rutas vivían sueltas en `App.tsx`, fuera de todo
 * menú**: sólo se llegaba escribiendo la URL a mano, así que en la práctica la funcionalidad
 * estaba construida y no existía para quien usa el panel.
 */
const REDACCION_SUBNAV = [
  { key: 'nav_templates', path: '/redaccion/builder' },
  { key: 'nav_new_report', path: '/redaccion/wizard' },
  { key: 'nav_scripts_review', path: '/redaccion/scripts/review' },
] as const

export function RedaccionLayout() {
  const { t } = useTranslation('redaccion')

  return (
    <div className="space-y-4">
      <nav aria-label={t('nav_aria')} className="flex gap-1 border-b pb-2 flex-wrap">
        {REDACCION_SUBNAV.map(({ key, path }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `px-3 py-1.5 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
              }`
            }
          >
            {t(key)}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
