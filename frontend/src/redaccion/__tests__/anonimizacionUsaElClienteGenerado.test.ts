import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'

/**
 * AIS.4 — El panel de anonimización llamaba sin credencial, y por eso no funcionaba.
 *
 * `useAnonymizationApi.ts` era un módulo de API escrito a mano cuyo `fetchJson` **no mandaba la
 * cabecera `Authorization`**. Sus tres hooks pegan a endpoints que exigen sesión y módulo
 * (`anonymization_router.py`: `require_module("informes")` + `get_current_user`), así que los
 * tres devolvían **401**. El panel de auditoría NER no ha funcionado nunca desde el navegador.
 *
 * **Tres cosas lo mantuvieron invisible**, y las tres son el hallazgo de método:
 *
 * 1. El cliente correcto **ya estaba generado** —`generated/redaccion-anonymization` expone los
 *    mismos tres nombres— y el panel importaba el manual.
 * 2. El test del panel hace `vi.mock('../hooks/useAnonymizationApi')`, así que la capa de red no
 *    se ejercitaba nunca.
 * 3. El guardarraíl de CAL.2 (`contractFirstApi.test.ts`) lista **seis** módulos manuales por
 *    nombre, y éste no estaba; y su comprobación de credencial busca ficheros que *mencionen*
 *    `Authorization` — o sea que éste pasaba **precisamente porque no la construía**.
 *
 * Lo que este fichero fija no es «usa Orval» como norma de estilo: es que ninguna llamada
 * autenticada salga de un módulo escrito a mano, porque el fallo de esa clase no se ve al
 * escribirlo, se ve cuando alguien abre la pantalla.
 */
const SRC = resolve(__dirname, '..', '..')
const REDACCION = join(SRC, 'redaccion')

/** Ficheros de código bajo `src/`, sin el cliente generado. */
function ficheros(directorio: string): string[] {
  return readdirSync(directorio).flatMap((entrada) => {
    const ruta = join(directorio, entrada)
    if (statSync(ruta).isDirectory()) {
      return entrada === 'generated' || entrada === '__tests__' ? [] : ficheros(ruta)
    }
    return /\.tsx?$/.test(entrada) ? [ruta] : []
  })
}

describe('la anonimización habla por el cliente generado', () => {
  it('should_not_keep_a_manual_api_module_in_redaccion', () => {
    expect(
      existsSync(join(REDACCION, 'hooks', 'useAnonymizationApi.ts')),
      'useAnonymizationApi.ts es un módulo de API a mano cuyo fetch no manda Authorization: ' +
        'sus tres endpoints exigen sesión, así que devuelven 401. El cliente generado ya expone ' +
        'los mismos tres hooks.',
    ).toBe(false)
  })

  it('should_import_the_generated_hooks_in_the_panel', () => {
    const panel = readFileSync(
      join(REDACCION, 'components', 'WorkspaceAnonymizationPanel.tsx'),
      'utf8',
    )

    expect(panel).toMatch(/generated\/redaccion-anonymization/)
    expect(panel).not.toMatch(/useAnonymizationApi/)
  })

  it('should_not_call_the_api_by_hand_from_redaccion', () => {
    // El widget tiene su exención documentada (SSE), y no vive aquí.
    const culpables: string[] = []
    for (const fichero of ficheros(REDACCION)) {
      const contenido = readFileSync(fichero, 'utf8')
      if (/\bfetch\s*\(/.test(contenido) && !/generated/.test(fichero)) {
        culpables.push(fichero.replace(SRC, 'src'))
      }
    }

    expect(
      culpables,
      'llamadas con `fetch` crudo en el módulo de Informes: la credencial la pone el ' +
        'interceptor de `shared/api/client.ts`, y un fetch a mano se la salta sin avisar',
    ).toEqual([])
  })
})
