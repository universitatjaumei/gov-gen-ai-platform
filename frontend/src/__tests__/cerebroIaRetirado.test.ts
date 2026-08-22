import { describe, it, expect } from 'vitest'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { codigoSinComentarios } from '@/test-utils/codigoSinComentarios'

/**
 * PLAT.4 — «Cerebro IA» se retira: tres pantallas sobre dos recursos.
 *
 * `AIBrainPage` importaba plantillas de prompt **y** configuraciones LLM, y no tenía recurso
 * propio: todo lo que editaba lo editan ya `PromptsPage` (9 referencias a la edición de
 * plantillas) y `LLMConfigsPage` (8 a `is_default`, 2 al test de conexión). Leída entera, no
 * aporta ninguna vista que las otras dos no den.
 *
 * **Y además engañaba.** Su selector de chatbot estaba al lado del botón «poner por defecto»,
 * lo que sugiere que se elige el modelo *de ese chatbot*. No: `is_default` es global, la
 * mutación no manda el `chatbot_id` a ninguna parte. Una pantalla que insinúa una relación que
 * no existe es peor que no tenerla — alguien la usa creyendo que configuró un chatbot.
 *
 * Caso B del checklist de `AGENTS.md`: código huérfano sin migración activa, borrado directo.
 * El historial de git es la fuente de verdad del pasado.
 */
const SRC = resolve(__dirname, '..')
const IGNORADOS = new Set(['generated', 'node_modules'])

function ficherosDeCodigo(directorio: string): string[] {
  return readdirSync(directorio).flatMap((entrada) => {
    const ruta = join(directorio, entrada)
    if (statSync(ruta).isDirectory()) {
      return IGNORADOS.has(entrada) ? [] : ficherosDeCodigo(ruta)
    }
    return /\.(tsx?|css)$/.test(entrada) ? [ruta] : []
  })
}

describe('PLAT.4 — «Cerebro IA» no vuelve', () => {
  it('should_not_keep_the_page_file', () => {
    expect(existsSync(join(SRC, 'admin/pages/AIBrainPage.tsx'))).toBe(false)
  })

  it('should_not_be_referenced_from_any_code', () => {
    // Sin comentarios, y sin este fichero. Lo primero porque la explicación de arriba menciona
    // lo retirado; lo segundo porque **un guardarraíl que busca una cadena la contiene por
    // necesidad**, en su propio código y no solo en sus comentarios. Excluirse a sí mismo no
    // deja ningún hueco: si alguien reintrodujera la pantalla, la reintroduciría en otro sitio.
    const culpables: string[] = []
    for (const fichero of ficherosDeCodigo(SRC)) {
      if (fichero === __filename) continue
      const contenido = codigoSinComentarios(readFileSync(fichero, 'utf8'))
      if (/AIBrainPage|\/hub\/brain/.test(contenido)) {
        culpables.push(fichero.replace(SRC, 'src'))
      }
    }
    expect(culpables).toEqual([])
  })

  it('should_not_leave_its_route_mounted', () => {
    const app = codigoSinComentarios(readFileSync(join(SRC, 'App.tsx'), 'utf8'))
    expect(app).not.toContain('"brain"')
  })

  it('should_not_leave_its_tab_in_the_chatbots_subnav', () => {
    const hub = codigoSinComentarios(readFileSync(join(SRC, 'admin/HubLayout.tsx'), 'utf8'))
    expect(hub).not.toContain('ai_brain')
  })
})
