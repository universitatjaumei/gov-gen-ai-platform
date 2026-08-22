import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const PLATAFORMA_SUBNAV = [
  { key: 'plataforma.modelos', path: '/plataforma/modelos' },
  { key: 'plataforma.prompts_actividad', path: '/plataforma/prompts-actividad' },
  { key: 'plataforma.tokens', path: '/plataforma/tokens' },
  { key: 'plataforma.usuarios_nav', path: '/plataforma/usuarios' },
  { key: 'plataforma.modulos_nav', path: '/plataforma/modulos' },
] as const

/**
 * La administración de la plataforma, que no es del módulo Chatbots (PLAT.2).
 *
 * El módulo `plataforma` estaba en `MODULOS_INICIALES` desde INF.7, se podía conceder y **no
 * abría nada**: se retiró del menú porque llevaba a un `PlaceholderPage`. Mientras tanto, tres
 * pantallas transversales vivían bajo `/hub`, que exige el módulo `chatbots`. La peor era
 * «Modelos LLM», porque su router **ya declara** `require_module("plataforma")`: quien tenía
 * `chatbots` y no `plataforma` veía el tab y recibía un 403, y quien tenía `plataforma` no podía
 * llegar a la única pantalla que su módulo protegía.
 *
 * El criterio de qué entra aquí no es de gusto: `Deploy: cloud` es configuración de la
 * plataforma y `Deploy: edge` es operación de un módulo (ver `AGENTS.md`, frontera edge/cloud).
 * Los niveles (*tiers*) de modelo, por ejemplo, los consumen Informes, Curación y Chatbots.
 */
export function PlataformaLayout() {
  const { t } = useTranslation('admin')

  return (
    <div className="space-y-4">
      <nav aria-label={t('plataforma.subnav_aria')} className="flex gap-1 border-b pb-2 flex-wrap">
        {PLATAFORMA_SUBNAV.map(({ key, path }) => (
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
