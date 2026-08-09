import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/shared/auth'

const NAV_SECTIONS = [
  { key: 'hub', path: '/hub' },
  { key: 'curation', path: '/curation' },
  { key: 'automation', path: '/automation' },
  { key: 'platform', path: '/platform' },
] as const

export function AppLayout() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const { user, logout } = useAuth()

  return (
    <div className="flex h-screen">
      <nav aria-label={t('nav.main')} className="flex flex-col w-56 shrink-0 border-r bg-card p-4 gap-1">
        {NAV_SECTIONS.map(({ key, path }) => (
          <NavLink
            key={key}
            to={path}
            className={({ isActive }) =>
              `px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-accent text-accent-foreground font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
              }`
            }
          >
            {t(`nav.${key}` as Parameters<typeof t>[0])}
          </NavLink>
        ))}

        <div className="mt-auto pt-4 border-t text-xs text-muted-foreground">
          <p className="truncate mb-2">{user?.email}</p>
          <button
            type="button"
            onClick={logout}
            className="w-full text-left hover:text-foreground transition-colors"
          >
            {tc('logout')}
          </button>
        </div>
      </nav>

      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
