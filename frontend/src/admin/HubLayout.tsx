import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMemo } from 'react'

const HUB_SUBNAV = [
  { key: 'chatbots', path: '/hub/chatbots', ns: 'admin' },
  { key: 'clients', path: '/hub/clients', ns: 'admin' },
  { key: 'documents', path: '/hub/documents', ns: 'admin' },
  { key: 'reports', path: '/hub/reports', ns: 'admin' },
  { key: 'llm_configs', path: '/hub/llm-configs', ns: 'admin' },
  { key: 'prompt_templates', path: '/hub/prompts', ns: 'admin' },
  { key: 'ai_brain', path: '/hub/brain', ns: 'admin' },
  { key: 'nav_sites', path: '/hub/sites', ns: 'contentQuality' },
  { key: 'nav_quality', path: '/hub/content-quality', ns: 'contentQuality' },
] as const

export function HubLayout() {
  const { t } = useTranslation('admin')
  const { t: tq } = useTranslation('contentQuality')

  return (
    <div className="space-y-4">
      <nav aria-label={t('hub.subnav_aria')} className="flex gap-1 border-b pb-2 flex-wrap">
        {HUB_SUBNAV.map(({ key, path, ns }) => (
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
            {ns === 'contentQuality'
              ? tq(key as Parameters<typeof tq>[0])
              : t(`hub.${key}` as Parameters<typeof t>[0])}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
