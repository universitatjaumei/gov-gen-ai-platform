/**
 * CAL.5 — Las páginas se cargan por ruta, no todas de golpe.
 *
 * Se comprueba sobre el fuente de `App.tsx` y no sobre `dist/`: el build está en `.gitignore`,
 * así que un test que lo inspeccionara pasaría o fallaría según si alguien había compilado
 * antes, que es la peor propiedad que puede tener un guardarraíl. Lo que se garantiza aquí es
 * la **precondición**: cada página entra por un `import()` dinámico, y Rollup emite un chunk
 * por cada uno.
 *
 * La medida real del reparto está en `planificacion/HISTORIAL.md`.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const APP = readFileSync(resolve(__dirname, '../App.tsx'), 'utf-8')

/** Envoltorios presentes en todas las rutas: partirlos añade espera y no ahorra nada. */
const ESTATICOS_ESPERADOS = [
  'AppLayout',
  'HubLayout',
  'CurationLayout',
  'PrivateRoute',
  // INF.7 — `Aterrizaje` decide a qué módulo entra cada persona y está en la ruta índice **y**
  // en el comodín, o sea que corre en practicamente toda entrada en frío: cargar por separado
  // el componente que decide a dónde vas añade un viaje al servidor antes de poder ir a ningún
  // sitio. `SinAcceso` son diez líneas de texto y vive al lado. Los dos caen en la misma razón
  // que los envoltorios de arriba.
  'Aterrizaje',
  'SinAcceso',
]

describe('CAL.5 — carga por ruta', () => {
  it('should_lazy_load_route_chunks', () => {
    // Ninguna página entra ya por import estático.
    const importsEstaticosDePagina = [
      ...APP.matchAll(/^import\s+\{[^}]*\}\s+from\s+'@\/(admin\/pages|redaccion\/pages|redaccion\/preview)\/[^']+'/gm),
    ].map((m) => m[0])

    expect(
      importsEstaticosDePagina,
      `Estas páginas siguen entrando en el bundle inicial:\n  ${importsEstaticosDePagina.join('\n  ')}`,
    ).toEqual([])

    // Y cada una entra por un import() dinámico envuelto en lazy().
    const perezosas = [...APP.matchAll(/const\s+(\w+)\s*=\s*lazy\(\s*\(\)\s*=>\s*import\(/g)].map((m) => m[1])
    expect(perezosas.length).toBeGreaterThanOrEqual(15)

    // Toda ruta con `element={<X />}` apunta a algo perezoso o a un envoltorio conocido.
    const enRutas = [...APP.matchAll(/element=\{<(\w+)\s*[^>]*\/>\}/g)].map((m) => m[1])
    const sinPartir = [...new Set(enRutas)].filter(
      (c) => !perezosas.includes(c) && !ESTATICOS_ESPERADOS.includes(c) && c !== 'Navigate',
    )
    expect(
      sinPartir,
      `Componentes de ruta que no se cargan por separado: ${sinPartir.join(', ')}`,
    ).toEqual([])
  })

  it('should_not_bundle_all_pages_in_single_chunk', () => {
    // Un `import()` por página es lo que hace que Rollup emita un chunk por página; con los
    // imports estáticos que había, las 17 pantallas caían en un bundle único de 1,18 MB.
    const puntosDeCorte = [...APP.matchAll(/\(\)\s*=>\s*import\('@\//g)].length
    expect(
      puntosDeCorte,
      'App.tsx no tiene suficientes puntos de corte: las páginas volverían a un solo chunk.',
    ).toBeGreaterThanOrEqual(15)

    // El fallback no puede ser `null`: con carga por ruta eso es una pantalla en blanco
    // durante la descarga, indistinguible de una aplicación colgada.
    expect(APP).not.toMatch(/<Suspense\s+fallback=\{null\}/)
    expect(APP).toMatch(/<Suspense\s+fallback=\{<\w+\s*\/>\}/)
  })
})
