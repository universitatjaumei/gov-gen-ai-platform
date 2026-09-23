import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { satisfies } from 'semver'

/**
 * Node va fijado a la misma versión en todas partes, y a una que el motor de tests admite.
 *
 * **De dónde sale.** Dependabot abrió la PR #52, «node de 24-alpine a 25-alpine», que toca
 * **sólo** `frontend/Dockerfile`. Node está fijado en **cinco** sitios: tres `node-version` en
 * `ci.yml`, uno en `deploy.yml` y el `FROM` del Dockerfile. Mezclarla habría dejado el
 * repositorio construyendo la imagen con la 25 y comprobando y desplegando con la 24 — el mismo
 * descuido que tuvimos un mes con `actions/checkout` en v7 en seis sitios y en v4 en el del
 * despliegue, y que está en `test_las_acciones_no_van_a_dos_versiones.py`.
 *
 * **Y la 25 además no valía.** Dos razones medidas, no supuestas:
 *
 * 1. El índice oficial (`nodejs.org/dist/index.json`) marca la **24 como LTS (Krypton)**; la 25
 *    es línea *current* y **no llega a LTS nunca**, porque sólo las pares lo hacen.
 * 2. `vitest` 5 declara `engines.node: "^22.12.0 || ^24.0.0 || >=26.0.0"`, que **salta la 25 a
 *    propósito** y admite la 26. El ecosistema ya tomó esa decisión.
 *
 * El segundo test lee esos `engines` **del lock**, así que no hay red ni versión copiada a mano:
 * el día que `vitest` amplíe su rango, el guardarraíl deja de estorbar por sí solo.
 */

const RAIZ = resolve(__dirname, '../../..')
const LOCK = resolve(__dirname, '../../package-lock.json')

const FIJACIONES = [
  '.github/workflows/ci.yml',
  '.github/workflows/deploy.yml',
  'frontend/Dockerfile',
]

interface Fijacion {
  fichero: string
  version: string
}

/** Cada sitio donde este repositorio dice qué node usar. */
function fijacionesDeNode(): Fijacion[] {
  const encontradas: Fijacion[] = []
  for (const relativo of FIJACIONES) {
    const contenido = readFileSync(resolve(RAIZ, relativo), 'utf8')
    // `node-version: "24"` en los workflows y `FROM node:24-alpine` en el Dockerfile.
    for (const m of contenido.matchAll(/node-version:\s*["']?(\d+(?:\.\d+)*)/g)) {
      encontradas.push({ fichero: relativo, version: m[1] })
    }
    for (const m of contenido.matchAll(/FROM\s+node:(\d+(?:\.\d+)*)/g)) {
      encontradas.push({ fichero: relativo, version: m[1] })
    }
  }
  return encontradas
}

function engineDeVitest(): string {
  const lock = JSON.parse(readFileSync(LOCK, 'utf8'))
  const vitest = lock.packages?.['node_modules/vitest']
  const engine = vitest?.engines?.node
  if (!engine) throw new Error('el lock no registra `engines.node` de vitest')
  return engine
}

describe('node va a una sola versión', () => {
  it('el medidor encuentra las fijaciones', () => {
    // Si el patrón deja de reconocer la forma de `node-version:` o de `FROM node:`, este
    // fichero pasaría en verde sin comprobar nada.
    const fijaciones = fijacionesDeNode()
    expect(fijaciones.length).toBeGreaterThanOrEqual(4)
    expect(fijaciones.some((f) => f.fichero === 'frontend/Dockerfile')).toBe(true)
    expect(fijaciones.some((f) => f.fichero.endsWith('deploy.yml'))).toBe(true)
  })

  it('no hay dos majors de node a la vez', () => {
    const porMajor = new Map<string, string[]>()
    for (const { fichero, version } of fijacionesDeNode()) {
      const major = version.split('.')[0]
      porMajor.set(major, [...(porMajor.get(major) ?? []), fichero])
    }
    expect(
      [...porMajor.entries()].map(([major, ficheros]) => `${major}: ${[...new Set(ficheros)].join(', ')}`),
      'node está fijado a dos majors distintas. No rompe nada hasta que rompe, y el que se ' +
        'queda atrás suele ser el que menos corre — el del despliegue—, que es el peor sitio ' +
        'para una diferencia que nadie mira.',
    ).toHaveLength(1)
  })

  it('`@types/node` va a la misma major que el node que se ejecuta', () => {
    // Dependabot abre esto una y otra vez —#78 primero, #106 después— y la respuesta es
    // siempre la misma, así que se mecaniza en vez de repetirla a mano.
    //
    // Los tipos describen las APIs de una línea de Node. Con `@types/node` en 26 y Node 24 en
    // marcha, TypeScript **da por buena** una API que en tiempo de ejecución no existe: el
    // error aparece al ejecutar, no al compilar, que es justo el orden que un sistema de tipos
    // viene a invertir.
    //
    // Y no se retira aunque no lo importe nadie: TypeScript carga `node_modules/@types/*`
    // automáticamente. Eso es lo que lo hace un falso positivo de cualquier barrido de
    // dependencias sin usar.
    const pkg = JSON.parse(readFileSync(resolve(__dirname, '../../package.json'), 'utf8'))
    const declarado = pkg.devDependencies?.['@types/node']
    expect(declarado, '`@types/node` no está declarado').toBeTruthy()

    const majorDeLosTipos = declarado.replace(/^[^\d]*/, '').split('.')[0]
    const majoresDeNode = [...new Set(fijacionesDeNode().map((f) => f.version.split('.')[0]))]

    expect(
      majoresDeNode,
      `\`@types/node\` está en ${majorDeLosTipos} y node se fija en ${majoresDeNode.join(', ')}. ` +
        'Los tipos siguen al node que se ejecuta: se suben cuando suba él, no antes.',
    ).toEqual([majorDeLosTipos])
  })

  it('la versión de node que se fija la admite `vitest`', () => {
    const engine = engineDeVitest()
    const incumplen = fijacionesDeNode().filter(
      // `24` se compara como `24.0.0`: lo que se fija es la línea, no un parche.
      ({ version }) => !satisfies(`${version.split('.')[0]}.0.0`, engine),
    )
    expect(
      incumplen.map((f) => `${f.fichero} fija node ${f.version}`),
      `vitest declara \`engines.node: "${engine}"\`. Una línea de node fuera de ese rango ` +
        'deja el motor de tests corriendo donde su autor dice que no lo soporta, y npm sólo ' +
        'avisa con `EBADENGINE`.',
    ).toEqual([])
  })
})
