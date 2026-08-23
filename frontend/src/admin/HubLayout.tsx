import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const HUB_SUBNAV = [
  { key: 'hub.chatbots', path: '/hub/chatbots' },
  // PLAT.3 — los `default_*` de RAG salieron de la pantalla de Organizaciones: son
  // configuración de este módulo aplicada a una organización, no identidad del inquilino.
  { key: 'hub.valores_por_defecto_nav', path: '/hub/valores-por-defecto' },
  { key: 'hub.documents', path: '/hub/documents' },
  { key: 'hub.vigencia', path: '/hub/vigencia' },
  { key: 'hub.revision', path: '/hub/revision' },
  { key: 'hub.prompt_templates', path: '/hub/prompts' },
  { key: 'admin:hub.test_scenarios.title', path: '/hub/test-scenarios' },
] as const

// PLAT.2 — tres tabs salieron de aquí a la sección Plataforma: «Modelos LLM» (su router ya
// exigía `require_module("plataforma")`, así que el menú prometía lo que la API negaba),
// «Prompts de actividad» (que por definición no cuelgan de ningún chatbot, PRO.2.1) y
// «Tokens de acceso» (credenciales de máquina de la plataforma).

export function HubLayout() {
  const { t } = useTranslation(['admin', 'auth'])

  return (
    <div className="space-y-4">
      <nav aria-label={t('admin:hub.subnav_aria')} className="flex gap-1 border-b flex-wrap">
        {HUB_SUBNAV.map(({ key, path }) => (
          <NavLink
            key={path}
            to={path}
            /* REV.3 — pestaña subrayada, no recuadro. El `-mb-px` sube el subrayado sobre la
               línea del `<nav>` para que sean la misma, y `border-transparent` en las
               inactivas evita que la barra entera baile al cambiar de pestaña. */
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
