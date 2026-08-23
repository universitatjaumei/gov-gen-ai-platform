import { useGetResolvedThemeApiV1HubThemesResolvedGet } from '@/shared/api/generated/hub-themes/hub-themes'
import { useOrganizacionElegida } from '@/shared/organizacion/useOrganizacionElegida'
import type { ThemeBranding } from '@/themes/types'

/**
 * La marca institucional que resuelve la cascada del servidor (plataforma → organización).
 *
 * **El frontend no decide.** Antes no había nada que decidir: `AppLayout` hacía
 * `import logoUji from '@/assets/logo-uji.png'` y pintaba el logotipo de la Universitat
 * Jaume I con `alt="Universitat Jaume I"`. En una plataforma multiorganización eso es un
 * error de diseño, no un detalle: la imagen se compila dentro del bundle, así que era la
 * misma para todos los despliegues, y cualquier institución que clonara el repositorio
 * arrancaba con la marca de otra.
 *
 * La cascada visual ya existía para los colores, la tipografía y el espaciado. Esto no
 * añade un mecanismo nuevo: mete la marca en el que ya había.
 *
 * `cargando` se distingue de «sin marca» a propósito: pintar el texto de reserva mientras
 * la petición está en vuelo haría que la cabecera cambiara de forma en cada recarga.
 */
export function useMarca(): { marca: ThemeBranding; cargando: boolean } {
  // REV.12 — la marca de la organización que se está mirando, no sólo la del token. Un
  // superadministrador no pertenece a ninguna, así que hasta aquí veía siempre la de
  // plataforma: configuraba el logotipo de la UJI y no lo veía en ninguna parte.
  const { elegida } = useOrganizacionElegida()
  const { data, isLoading } = useGetResolvedThemeApiV1HubThemesResolvedGet({
    organizacion: elegida || undefined,
  })
  const config = (data as { config?: Record<string, unknown> } | undefined)?.config
  const branding = config?.branding

  return {
    marca: (branding && typeof branding === 'object' ? branding : {}) as ThemeBranding,
    cargando: isLoading,
  }
}
