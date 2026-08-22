import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { codigoSinComentarios } from '@/test-utils/codigoSinComentarios'

/**
 * PLAT.2 — las tres pantallas transversales no vuelven a `/hub`.
 *
 * `/hub` entero está montado bajo `<RutaDeModulo modulo="chatbots">`, así que cualquier ruta que
 * cuelgue de ahí exige el módulo Chatbots. Para «Modelos LLM» eso era una contradicción con el
 * propio backend, que ya declara `require_module("plataforma")` en `hub_llm_configs_router`.
 *
 * **Sin redirecciones desde las rutas viejas**, a propósito: `AGENTS.md` prohíbe los shims de
 * compatibilidad y este panel es interno y anterior al primer despliegue. El test lo fija, para
 * que nadie las reintroduzca «por comodidad» y deje dos URL para la misma pantalla.
 *
 * Se leen los ficheros sin comentarios porque esta explicación menciona las rutas retiradas, y
 * buscarlas en el texto completo convertiría la explicación en un falso positivo — la misma
 * trampa que ya documentó `assetsVersionados.test.ts`.
 */
const SRC = resolve(__dirname, '..')

function sinComentarios(relativa: string): string {
  return codigoSinComentarios(readFileSync(resolve(SRC, relativa), 'utf8'))
}

const RUTAS_RETIRADAS = ['/hub/llm-configs', '/hub/activity-prompts', '/hub/access-tokens'] as const

describe('PLAT.2 — las rutas de plataforma', () => {
  it('should_not_keep_the_three_screens_under_hub', () => {
    const app = sinComentarios('App.tsx')
    const hub = sinComentarios('admin/HubLayout.tsx')

    for (const ruta of RUTAS_RETIRADAS) {
      expect(hub, `${ruta} sigue en la subnavegación de Chatbots`).not.toContain(ruta)
    }
    // En `App.tsx` las rutas hijas se escriben sin el prefijo, así que se buscan los segmentos.
    for (const segmento of ['"llm-configs"', '"activity-prompts"', '"access-tokens"']) {
      expect(app, `${segmento} sigue montado dentro de /hub`).not.toContain(segmento)
    }
  })

  it('should_mount_the_three_screens_under_plataforma', () => {
    const app = sinComentarios('App.tsx')

    expect(app).toContain('/plataforma')
    for (const segmento of ['"modelos"', '"prompts-actividad"', '"tokens"']) {
      expect(app).toContain(segmento)
    }
  })

  it('should_gate_the_section_with_its_own_module', () => {
    const app = sinComentarios('App.tsx')

    expect(app).toMatch(/RutaDeModulo\s+modulo="plataforma"/)
  })

  it('should_not_add_redirects_from_the_old_routes', () => {
    const app = sinComentarios('App.tsx')

    for (const ruta of RUTAS_RETIRADAS) {
      expect(app, `hay una redirección desde ${ruta}: AGENTS.md prohíbe los shims`).not.toContain(
        ruta
      )
    }
  })
})
