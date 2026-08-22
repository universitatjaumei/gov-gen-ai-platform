import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const HUB_SUBNAV = [
  { key: 'hub.chatbots', path: '/hub/chatbots' },
  { key: 'hub.organizaciones', path: '/hub/organizaciones' },
  { key: 'hub.documents', path: '/hub/documents' },
  { key: 'hub.vigencia', path: '/hub/vigencia' },
  { key: 'hub.reports', path: '/hub/reports' },
  { key: 'hub.prompt_templates', path: '/hub/prompts' },
  { key: 'hub.ai_brain', path: '/hub/brain' },
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
      <nav aria-label={t('admin:hub.subnav_aria')} className="flex gap-1 border-b pb-2 flex-wrap">
        {HUB_SUBNAV.map(({ key, path }) => (
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
