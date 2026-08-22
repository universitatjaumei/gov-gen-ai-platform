import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/shared/auth'
import { useModulos } from '@/shared/auth/useModulos'
import { SUPPORTED_LANGUAGES } from '@/shared/i18n'
import { useMarca } from '@/shared/marca/useMarca'

/** El nombre de cada idioma EN ese idioma: quien busca su lengua la reconoce escrita así. */
const IDIOMAS: Record<string, string> = {
  es: 'Castellano',
  ca: 'Valencià',
  en: 'English',
}

/** Lo que la plataforma sabe hacer, más su administración.
 *
 * «Automatización» y «Plataforma» eran `PlaceholderPage`: entradas de menú que llevaban a
 * una pantalla vacía. Un menú que promete lo que no hay es peor que un menú corto, así que
 * las dos se retiraron. «Automatización» sigue fuera —el módulo no existe—, pero
 * «Plataforma» vuelve en PLAT.2, esta vez con contenido: las pantallas que nunca fueron del
 * módulo Chatbots y estaban dentro de él.
 *
 * «Informes» apunta a `/redaccion`, que estaba construido —plantillas, asistente, borrador
 * con LLM— y no figuraba en ningún menú: sólo se llegaba escribiendo la URL.
 */
const NAV_SECTIONS = [
  { key: 'chatbots', path: '/hub', modulo: 'chatbots' },
  { key: 'reports', path: '/redaccion', modulo: 'informes' },
  { key: 'curation', path: '/curation', modulo: 'curacion' },
  { key: 'plataforma', path: '/plataforma', modulo: 'plataforma' },
] as const

export function AppLayout() {
  const { t, i18n } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const { user, logout } = useAuth()
  // INF.7 — el menu se genera con lo que el servidor concede. No habia nada que filtrar:
  // cualquier cuenta veia chatbots, informes y curacion.
  const { modulos } = useModulos()
  const secciones = NAV_SECTIONS.filter((s) => modulos.includes(s.modulo))
  // La marca la resuelve la cascada del servidor. Aquí estaba importada como código, así
  // que el panel llevaba el logotipo de una institución concreta en cualquier despliegue.
  const { marca, cargando: cargandoMarca } = useMarca()

  return (
    <div className="flex h-screen">
      {/* UX.5: el lateral usa `bg-sidebar`, no `bg-card`. Las variables del azul llevaban
          definidas desde el principio y no las aplicaba nadie, así que el panel salía
          blanco y sin identidad. */}
      <nav
        aria-label={t('nav.main')}
        className="flex flex-col w-56 shrink-0 bg-sidebar text-sidebar-foreground p-4 gap-1"
      >
        {/* Sin marca configurada va el nombre de la plataforma, ya traducido: ni un hueco
            ni el logotipo de nadie. Y mientras la cascada está en vuelo no se pinta
            ninguna de las dos cosas, para que la cabecera no cambie de forma al cargar. */}
        {cargandoMarca ? (
          <div className="h-8 mb-5 mt-1" />
        ) : marca.logoUrl ? (
          <img
            src={marca.logoUrl}
            alt={marca.logoAlt || tc('app_name')}
            className="h-8 w-auto self-start mb-5 mt-1"
          />
        ) : (
          <p className="h-8 mb-5 mt-1 self-start font-semibold leading-8">{tc('app_name')}</p>
        )}

        {secciones.map(({ key, path }) => (
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
          {/* El panel se traducía a tres idiomas y no había forma de cambiarlo: dependías
              de lo que el navegador dijera. El detector de i18next guarda la elección, así
              que basta con ofrecerla. */}
          <label htmlFor="idioma" className="block mb-1">
            {t('nav.language')}
          </label>
          <select
            id="idioma"
            value={i18n.resolvedLanguage ?? 'es'}
            onChange={e => void i18n.changeLanguage(e.target.value)}
            className="w-full mb-3 px-2 py-1 rounded-md bg-sidebar-accent text-sidebar-accent-foreground border border-sidebar-border"
          >
            {SUPPORTED_LANGUAGES.map(l => (
              <option key={l} value={l}>{IDIOMAS[l]}</option>
            ))}
          </select>
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
