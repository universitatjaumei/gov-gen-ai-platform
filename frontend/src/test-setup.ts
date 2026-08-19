import '@testing-library/jest-dom'
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
