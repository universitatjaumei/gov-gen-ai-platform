import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const PLATAFORMA_SUBNAV = [
  // REV.11 — la organización sirve al resto de los módulos, así que darla de alta es una
  // operación general y no del módulo de asistentes. Su router ya exigía `plataforma` para
  // crear y borrar (PLAT.5), así que quien tenía ese módulo y no `chatbots` no llegaba a la
  // pantalla que su propio módulo protege: el caso de «Modelos LLM» de PLAT.2 otra vez.
  { key: 'hub.organizaciones', path: '/plataforma/organizaciones' },
  { key: 'plataforma.modelos', path: '/plataforma/modelos' },
  { key: 'plataforma.prompts_actividad', path: '/plataforma/prompts-actividad' },
  { key: 'plataforma.tokens', path: '/plataforma/tokens' },
  { key: 'plataforma.usuarios_nav', path: '/plataforma/usuarios' },
  { key: 'plataforma.modulos_nav', path: '/plataforma/modulos' },
  { key: 'plataforma.identidad_visual_nav', path: '/plataforma/identidad-visual' },
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
      <nav aria-label={t('plataforma.subnav_aria')} className="flex gap-1 border-b flex-wrap">
        {PLATAFORMA_SUBNAV.map(({ key, path }) => (
          <NavLink
            key={path}
            to={path}
            /* REV.3 — mismo criterio que la subnav de Chatbots: subrayado del color del texto
               en vez de recuadro, y la barra reservada en las inactivas. */
            className={({ isActive }) =>
              `-mb-px border-b-2 px-3 py-1.5 text-sm transition-colors ${
                isActive
                  ? 'border-current font-semibold text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
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
