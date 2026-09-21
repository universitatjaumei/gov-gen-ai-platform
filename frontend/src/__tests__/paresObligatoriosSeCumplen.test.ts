import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { satisfies } from 'semver'

/**
 * Ninguna dependencia instalada incumple un `peerDependency` declarado como obligatorio.
 *
 * **Lo que lo destapó.** Dependabot abrió la PR #65, «typescript de 6.0.3 a 7.0.2», y parecía
 * una subida más. Al medirla resultó que ocho paquetes de `typescript-eslint` declaran
 * `typescript >=4.8.4 <6.1.0` como par **obligatorio**, y que la 7.0.2 no lo cumple.
 *
 * **Y nada se ponía rojo.** `npm install` **no falla**: avisa `ERESOLVE overriding peer
 * dependency` y devuelve 0. Con la 7 instalada, `tsc` pasaba limpio, `tsc -b` construía, la
 * suite entera pasaba y `vite build` generaba el paquete. Lo único que moría era `eslint`, con
 * un error explícito —«typescript-eslint does not support TS 7.0»—, y **este repositorio no
 * ejecuta ESLint en integración continua**: es justamente la issue #47. O sea que la subida
 * habría entrado en verde y habría dejado el linter inservible **sin una sola señal**.
 *
 * Ese es el modo de fallo que vigila este fichero, y no es de `typescript`: es de cualquier
 * paquete cuyo par obligatorio se incumpla mientras la herramienta que lo nota **no corre en
 * CI**. El aviso de npm se pierde entre cientos de líneas de instalación; una aserción no.
 *
 * Se compara con `semver` y no con una comprobación escrita a mano a propósito: rangos como
 * `>=4.8.4 <6.1.0` o `^5 || ^6 || ^7` se parsean mal con facilidad, y un guardarraíl que
 * los parsea mal da verde con autoridad.
 */

const LOCK = resolve(__dirname, '../../package-lock.json')

interface PaqueteDelLock {
  version?: string
  peerDependencies?: Record<string, string>
  peerDependenciesMeta?: Record<string, { optional?: boolean }>
}

interface Incumplido {
  quien: string
  par: string
  exige: string
  instalado: string
}

/** El nombre del paquete tal y como se declara, a partir de su ruta en el lock. */
function nombreDesdeRuta(ruta: string): string {
  const corte = ruta.lastIndexOf('node_modules/')
  return corte === -1 ? ruta : ruta.slice(corte + 'node_modules/'.length)
}

/**
 * Los pares obligatorios que no cumple la versión instalada.
 *
 * Es una función sobre los datos del lock, y no un comando, para poder probarla **en los dos
 * sentidos**: contra el lock de verdad, que tiene que salir vacía, y contra un lock de mentira
 * con el caso de la PR #65 dentro, que tiene que salir con él.
 */
export function paresObligatoriosIncumplidos(
  paquetes: Record<string, PaqueteDelLock>,
): Incumplido[] {
  // La versión que de verdad hay para cada nombre. Un paquete anidado
  // (`a/node_modules/b`) gana sobre el de arriba para quien lo tenga dentro, pero para lo que
  // aquí se vigila basta la de primer nivel: es la que resuelven las herramientas del proyecto.
  const instaladas = new Map<string, string>()
  for (const [ruta, paquete] of Object.entries(paquetes)) {
    if (!ruta.startsWith('node_modules/') || ruta.slice('node_modules/'.length).includes('/node_modules/')) {
      continue
    }
    if (paquete.version) instaladas.set(nombreDesdeRuta(ruta), paquete.version)
  }

  const incumplidos: Incumplido[] = []
  for (const [ruta, paquete] of Object.entries(paquetes)) {
    for (const [par, rango] of Object.entries(paquete.peerDependencies ?? {})) {
      if (paquete.peerDependenciesMeta?.[par]?.optional) continue
      const instalado = instaladas.get(par)
      // Un par obligatorio que no está instalado es otro problema —y lo grita npm al
      // instalar—; aquí se vigila el que está y no encaja, que es el que pasa callado.
      if (!instalado) continue
      if (!satisfies(instalado, rango, { includePrerelease: true })) {
        incumplidos.push({ quien: nombreDesdeRuta(ruta), par, exige: rango, instalado })
      }
    }
  }
  return incumplidos
}

function lockDelProyecto(): Record<string, PaqueteDelLock> {
  return JSON.parse(readFileSync(LOCK, 'utf8')).packages ?? {}
}

describe('los pares obligatorios se cumplen', () => {
  it('el medidor ve pares declarados', () => {
    // Un guardarraíl que no encuentra ningún par obligatorio pasa en verde sin comprobar nada.
    const conPar = Object.values(lockDelProyecto()).filter((p) => {
      const pares = Object.entries(p.peerDependencies ?? {})
      return pares.some(([nombre]) => !p.peerDependenciesMeta?.[nombre]?.optional)
    })
    expect(conPar.length).toBeGreaterThan(5)
  })

  it('ninguna dependencia instalada incumple un par obligatorio', () => {
    const incumplidos = paresObligatoriosIncumplidos(lockDelProyecto())
    expect(
      incumplidos.map((i) => `${i.quien} exige ${i.par}@${i.exige} y hay ${i.instalado}`),
    ).toEqual([])
  })

  it('caza el caso de la PR #65, con los rangos reales', () => {
    // El mismo par que declara `typescript-eslint` 8.70.0, con `typescript` 7.0.2 instalado.
    // `npm install` sólo lo avisa; esto lo afirma.
    const incumplidos = paresObligatoriosIncumplidos({
      'node_modules/typescript': { version: '7.0.2' },
      'node_modules/typescript-eslint': {
        version: '8.70.0',
        peerDependencies: { typescript: '>=4.8.4 <6.1.0' },
      },
    })
    expect(incumplidos).toEqual([
      {
        quien: 'typescript-eslint',
        par: 'typescript',
        exige: '>=4.8.4 <6.1.0',
        instalado: '7.0.2',
      },
    ])
  })

  it('no confunde un par opcional con uno obligatorio', () => {
    // `i18next` declara `typescript` como par **opcional**: que no encaje no es un problema.
    const incumplidos = paresObligatoriosIncumplidos({
      'node_modules/typescript': { version: '7.0.2' },
      'node_modules/i18next': {
        version: '25.0.0',
        peerDependencies: { typescript: '^5 || ^6' },
        peerDependenciesMeta: { typescript: { optional: true } },
      },
    })
    expect(incumplidos).toEqual([])
  })
})
