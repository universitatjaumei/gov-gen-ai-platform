import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const HUB_SUBNAV = [
  { key: 'chatbots', path: '/hub/chatbots' },
  { key: 'clients', path: '/hub/clients' },
  { key: 'documents', path: '/hub/documents' },
  { key: 'reports', path: '/hub/reports' },
  { key: 'llm_configs', path: '/hub/llm-configs' },
] as const

export function HubLayout() {
  const { t } = useTranslation('admin')

  return (
    <div className="space-y-4">
      <nav className="flex gap-1 border-b pb-2">
        {HUB_SUBNAV.map(({ key, path }) => (
          <NavLink
            key={key}
            to={path}
            className={({ isActive }) =>
              `px-3 py-1.5 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
              }`
            }
          >
            {t(`hub.${key}` as Parameters<typeof t>[0])}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
