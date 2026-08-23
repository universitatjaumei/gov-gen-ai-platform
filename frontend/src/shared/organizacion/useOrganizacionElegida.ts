import { useCallback, useEffect, useState } from 'react'
import { useListOrganizacionesApiV1HubOrganizacionesGet } from '@/shared/api/generated/hub-organizaciones/hub-organizaciones'

/** Dónde se recuerda la elección. Por navegador y por persona que usa ese navegador. */
export const CLAVE_GUARDADA = 'organizacion-elegida'

export interface OrganizacionBreve {
  id: string
  name: string
}

export interface EleccionDeOrganizacion {
  organizaciones: OrganizacionBreve[]
  /** El id elegido, o `''` mientras no hay ninguna organización cargada. */
  elegida: string
  elegir: (id: string) => void
  /** Si merece la pena ofrecer el selector: con una sola organización es ruido. */
  hayVarias: boolean
}

/**
 * De qué organización se está hablando en el panel (REV.10).
 *
 * Antes esto no existía y **cada pantalla lo resolvía a su manera**: «Valores por defecto» tenía
 * su propio selector, «Identidad visual» otro, Vigencia elegía por *chatbot*, y Personas y
 * Prompts de actividad no tenían ninguno —una porque le faltaba, la otra porque no le hace
 * falta—. El resultado es que cambiar de organización obligaba a repetir la elección en cada
 * pantalla, y no había forma de saber si una pantalla sin selector era de plataforma o estaba
 * incompleta.
 *
 * **La elección se recuerda** en `localStorage`: es una preferencia de quien usa el panel, no un
 * dato del servidor, y perderla en cada recarga convierte el selector en un estorbo. Si la
 * guardada ya no existe —organización borrada, o alguien que ha cambiado de permisos— se cae a la
 * primera disponible en vez de quedarse en un id fantasma que no resuelve nada.
 *
 * Se lee con el hook que ya existía para listar organizaciones, así que no añade una petición:
 * react-query devuelve la consulta cacheada.
 */
export function useOrganizacionElegida(): EleccionDeOrganizacion {
  const { data } = useListOrganizacionesApiV1HubOrganizacionesGet()
  const organizaciones: OrganizacionBreve[] = ((data ?? []) as { id: string; name: string }[]).map(
    (o) => ({ id: String(o.id), name: o.name }),
  )

  const [elegida, setElegida] = useState<string>(() => {
    try {
      return localStorage.getItem(CLAVE_GUARDADA) ?? ''
    } catch {
      // Un navegador con el almacenamiento bloqueado no es motivo para no funcionar.
      return ''
    }
  })

  const elegir = useCallback((id: string) => {
    setElegida(id)
    try {
      localStorage.setItem(CLAVE_GUARDADA, id)
    } catch {
      /* sin persistencia, pero con elección */
    }
  }, [])

  useEffect(() => {
    if (organizaciones.length === 0) return
    const sigueExistiendo = organizaciones.some((o) => o.id === elegida)
    if (!sigueExistiendo) elegir(organizaciones[0].id)
  }, [organizaciones, elegida, elegir])

  return {
    organizaciones,
    elegida: organizaciones.some((o) => o.id === elegida) ? elegida : '',
    elegir,
    hayVarias: organizaciones.length > 1,
  }
}
