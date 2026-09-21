// **`/vitest`, no la entrada por omisión.** La entrada `.` de `jest-dom` sólo hace
// `/// <reference path="jest.d.ts" />`: amplía el espacio de nombres de **Jest**. La que declara
// `declare module 'vitest'` es `@testing-library/jest-dom/vitest`.
//
// Con vitest 4 el import por omisión funcionaba **por casualidad**, porque su `Assertion`
// heredaba de los tipos de Jest. Vitest 5 dejó de hacerlo y aparecieron **288 errores `TS2339`
// en 31 ficheros**, todos «Property 'toBeInTheDocument' does not exist». No es que `jest-dom`
// cambiara: es que este import nunca fue el correcto para vitest, y se notó al quitarse la
// coincidencia que lo sostenía.
import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

/**
 * Desmontar lo renderizado después de cada test.
 *
 * `@testing-library/react` lo registra solo cuando detecta los globales de test, y con esta
 * configuración no siempre llega a hacerlo: el síntoma es un `getByText` que encuentra **dos**
 * botones «Nuevo sitio» —el del test anterior sigue en el documento— y falla por una razón que no
 * tiene nada que ver con lo que prueba. Aparecía sólo al correr varios ficheros juntos, o sea justo
 * en CI y no al depurar el fichero suelto.
 *
 * Registrarlo aquí es inofensivo si la librería ya lo hizo (desmontar dos veces no rompe) y quita
 * una clase entera de fallos intermitentes.
 */
afterEach(() => {
  cleanup()
})
