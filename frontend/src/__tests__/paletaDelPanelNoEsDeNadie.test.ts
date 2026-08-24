import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/**
 * La paleta del panel es del **proyecto**, no de una institución, y es **una** en los dos modos.
 *
 * Hermano de `marcaNoViajaEnElRepo.test.ts`: aquél saca las imágenes del bundle, éste saca la
 * marca institucional de los tokens de color. Nace de la auditoría del 2026-08-24, que señaló la
 * paleta de `index.css` como lo único que **bloquea de facto** que otra administración use el
 * repositorio principal tal cual.
 *
 * **Dos cosas de esa auditoría estaban desactualizadas, y conviene dejarlo escrito para que nadie
 * vuelva a "arreglar" lo que ya está bien.** Decía que la cascada de temas no alcanza el cromo del
 * panel, porque `injectThemeCSS` escribe `--color-*` y las utilidades resuelven contra `--*`. Eso
 * era cierto **hasta REV.9**, un día antes de la auditoría: `aplicarColoresDelPanel`
 * (`shared/marca/coloresDelPanel.ts`) escribe los `--*` de la capa shadcn directamente en `:root`
 * como estilo en línea, que gana a cualquier hoja de estilos —incluido el bloque `.dark`—. Los dos
 * sistemas ya están puenteados, y `index.css` es **a propósito** el valor de reserva: lo que se ve
 * mientras la cascada está en vuelo y cuando no hay ningún tema.
 *
 * Lo que sí quedaba, y es lo que fija este fichero:
 *
 * 1. El bloque `.dark` estaba rotulado literalmente `UJI brand` y llevaba el turquesa (hue 211) y
 *    el azul marino (hue 244) de esa institución.
 * 2. **La marca cambiaba al cambiar de modo.** El bloque claro lo pasó UX.5 al azul del proyecto
 *    (`#0b5394`, hue ~255) y el oscuro se quedó con el turquesa: pasar a modo oscuro no oscurecía
 *    la identidad, la **sustituía por otra**. Eso no es una preferencia estética, es un defecto.
 * 3. No había nada que impidiera que volviera a entrar.
 *
 * Por eso el arreglo declara la marca **una sola vez** (`--marca*`) y deriva el modo oscuro de
 * ella con `color-mix`, en vez de escribir dos paletas a mano que nadie garantiza que sean la
 * misma. Un fork que quiera otra marca no debería tocar esto en absoluto —su sitio es la cascada
 * del servidor—, pero si lo toca, toca un valor y no catorce.
 */
const INDEX_CSS = resolve(__dirname, '..', 'index.css')

/** Instituciones y marcas concretas que no pintan nada en el repositorio principal. */
const INSTITUCIONES = /\b(uji|jaume|castell[oó]|innovap|generalitat)\b/i

/** Los tokens de color de marca: los que `VARIABLE_POR_COLOR` (REV.9) puede sobrescribir. */
const TOKENS_DE_MARCA = [
  '--primary',
  '--primary-foreground',
  '--accent',
  '--accent-foreground',
  '--ring',
  '--sidebar',
  '--sidebar-foreground',
  '--sidebar-primary',
  '--sidebar-accent',
  '--sidebar-accent-foreground',
  '--sidebar-border',
]

function css(): string {
  return readFileSync(INDEX_CSS, 'utf8')
}

/** El cuerpo de un bloque de nivel superior (`:root` o `.dark`). */
function bloque(fuente: string, selector: string): string {
  const inicio = fuente.indexOf(`${selector} {`)
  expect(inicio, `no se encuentra el bloque ${selector} en index.css`).toBeGreaterThan(-1)
  const desde = fuente.slice(inicio)
  return desde.slice(0, desde.indexOf('\n}'))
}

describe('la paleta del panel no es de ninguna institución', () => {
  it('should_not_name_an_institution_in_the_stylesheet', () => {
    // Se mira el fichero entero, **comentarios incluidos**, al contrario que
    // `marcaNoViajaEnElRepo.test.ts`, que los quita para poder explicar en su propio código el
    // import que retiró. Aquí no hace falta la excepción y sí conviene la severidad: este
    // fichero se compila dentro del bundle de todos los despliegues, así que la historia de qué
    // marca había vive en este test —que no se sirve a nadie— y no en la hoja de estilos.
    const culpables = css()
      .split('\n')
      .map((linea, i) => ({ linea: linea.trim(), n: i + 1 }))
      .filter(({ linea }) => INSTITUCIONES.test(linea))
      .map(({ linea, n }) => `index.css:${n} → ${linea}`)

    expect(
      culpables,
      'la paleta del panel viaja en el bundle, así que es la misma para todos los ' +
        'despliegues: nombrar una institución aquí es exactamente lo que impide que otra ' +
        'administración use el principal tal cual. La identidad va por la cascada del servidor.',
    ).toEqual([])
  })

  it('should_declare_a_single_brand_seed_the_dark_mode_derives_from', () => {
    const fuente = css()
    expect(
      fuente,
      'la marca del proyecto se declara en `--marca` y el modo oscuro sale de ahí: dos ' +
        'paletas escritas a mano acaban siendo dos marcas distintas, que es lo que pasó',
    ).toMatch(/--marca:\s*#[0-9a-f]{6}/i)

    // Y vale el mismo valor que el `--primary` claro. Que estén los dos escritos **no** es
    // redundancia por descuido: REV.9 ata los literales de `:root` al contrato del servidor con
    // `test_rev9_la_paleta_es_una.py`, que los compara como texto — poner `var(--marca)` ahí
    // dejaría a ese test comparando «var(--marca)» contra un hexadecimal. Resolver funciones CSS
    // desde un test de Python no vale lo que cuesta, así que el literal claro se queda donde el
    // contrato lo espera y este test comprueba que los dos no se separen.
    const claro = bloque(fuente, ':root')
    const semilla = fuente.match(/--marca:\s*(#[0-9a-f]{6})/i)?.[1].toLowerCase()
    const primario = claro.match(/--primary:\s*([^;]+);/)?.[1].trim().toLowerCase()
    expect(
      semilla,
      '`--marca` y el `--primary` del modo claro son la misma decisión: si se separan, el ' +
        'modo oscuro deriva de un color que el panel no pinta en ningún sitio',
    ).toBe(primario)
  })

  it('should_derive_the_dark_palette_from_the_same_brand', () => {
    const oscuro = bloque(css(), '.dark')
    const literales = TOKENS_DE_MARCA.flatMap((token) => {
      const encaje = oscuro.match(new RegExp(`${token}:\\s*([^;]+);`))
      if (!encaje) return []
      const valor = encaje[1].trim()
      // Vale referenciar la marca (o mezclarla), y vale un neutro puro —blanco, negro o un gris
      // sin croma—, que no es identidad de nadie. Lo que no vale es un color de marca escrito
      // a mano: es así como el modo oscuro acabó con la marca de otra institución.
      const referenciaLaMarca = valor.includes('--marca')
      const esNeutro = /^(#fff(fff)?|#000(000)?|oklch\([\d.]+\s+0\s+0(\s*\/\s*[^)]+)?\))$/i.test(valor)
      return referenciaLaMarca || esNeutro ? [] : [`${token}: ${valor}`]
    })

    expect(
      literales,
      'el modo oscuro escribía su propia paleta a mano, y con otra tonalidad que la clara: ' +
        'cambiar de modo no oscurecía la identidad, la sustituía por otra. Deriva de `--marca`.',
    ).toEqual([])
  })

  it('should_declare_every_brand_token_in_both_modes', () => {
    const fuente = css()
    const claro = bloque(fuente, ':root')
    const oscuro = bloque(fuente, '.dark')

    const faltan = TOKENS_DE_MARCA.filter(
      (token) => claro.includes(`${token}:`) !== oscuro.includes(`${token}:`),
    )

    expect(
      faltan,
      'un token de marca declarado en un solo modo hereda del otro sin que nadie lo decida, ' +
        `y el resultado depende de si el usuario tiene el modo oscuro puesto: ${faltan.join(', ')}`,
    ).toEqual([])
  })
})
