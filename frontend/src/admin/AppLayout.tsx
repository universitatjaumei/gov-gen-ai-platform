import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/shared/auth'
import logoUji from '@/assets/logo-uji.png'

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
      {/* UX.5: el lateral usa `bg-sidebar`, no `bg-card`. Las variables del azul llevaban
          definidas desde el principio y no las aplicaba nadie, así que el panel salía
          blanco y sin identidad. */}
      <nav
        aria-label={t('nav.main')}
        className="flex flex-col w-56 shrink-0 bg-sidebar text-sidebar-foreground p-4 gap-1"
      >
        <img
          src={logoUji}
          alt="Universitat Jaume I"
          className="h-8 w-auto self-start mb-5 mt-1"
        />

        {NAV_SECTIONS.map(({ key, path }) => (
          <NavLink
            key={key}
            to={path}
            className={({ isActive }) =>
              `px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                  : 'text-sidebar-foreground/80 hover:text-sidebar-accent-foreground hover:bg-sidebar-accent/60'
              }`
            }
          >
            {t(`nav.${key}` as Parameters<typeof t>[0])}
          </NavLink>
        ))}

        <div className="mt-auto pt-4 border-t border-sidebar-border text-xs text-sidebar-foreground/80">
          <p className="truncate mb-2">{user?.email}</p>
          <button
            type="button"
            onClick={logout}
            className="w-full text-left hover:text-sidebar-accent-foreground transition-colors"
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
