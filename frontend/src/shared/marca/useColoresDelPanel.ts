import { useEffect } from 'react'
import { useGetResolvedThemeApiV1HubThemesResolvedGet } from '@/shared/api/generated/hub-themes/hub-themes'

import { aplicarColoresDelPanel } from './coloresDelPanel'

/**
 * Aplica al panel los colores que resuelve la cascada del servidor (REV.9).
 *
 * Es el hermano de `useMarca`, y nace del mismo hallazgo: la cascada visual existía —plataforma
 * → organización → asistente—, la pantalla de «Identidad visual» la editaba, y **el único que la
 * consumía era el logotipo**. Los colores del panel salían de `index.css`, escritos a mano, así
 * que cambiar la paleta de una organización no cambiaba nada y nadie tenía forma de saber por
 * qué.
 *
 * Usa el mismo endpoint que `useMarca`, así que no añade una petición: react-query devuelve la
 * misma consulta ya cacheada.
 */
export function useColoresDelPanel(): void {
  const { data } = useGetResolvedThemeApiV1HubThemesResolvedGet()
  const config = (data as { config?: Record<string, unknown> } | undefined)?.config
  const colores = config?.colors as Record<string, unknown> | undefined

  useEffect(() => {
    aplicarColoresDelPanel(colores)
    // Sin limpieza al desmontar a propósito: el panel vive mientras vive la sesión, y quitar
    // las variables al cambiar de pantalla haría que la identidad parpadeara en cada
    // navegación. Si la cascada devuelve otro valor, `setProperty` lo sobrescribe.
  }, [colores])
}
