import { describe, it, expect } from 'vitest'
import { existsSync, readdirSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'

/**
 * Ninguna imagen entra en el bundle de la interfaz.
 *
 * `AppLayout` importaba `@/assets/logo-uji.png` y lo pintaba en la barra lateral de
 * cualquier despliegue. El fichero no estaba ahí por descuido: había una excepción en
 * `.gitignore` (`!frontend/src/assets/*.png`) y un guardarraíl en integración continua
 * —`assetsVersionados.test.ts`— cuyo efecto conjunto era **garantizar** que la marca de
 * una institución concreta viajara al repositorio principal.
 *
 * Una imagen importada desde `src/` es la misma para todos los despliegues por
 * definición: se compila dentro del bundle. La identidad visual de una organización tiene
 * que llegar por la cascada del servidor (plataforma → organización → asistente), igual
 * que los colores, y por eso este directorio queda vacío de imágenes.
 *
 * Si alguna vez hace falta una ilustración genérica de la plataforma, su sitio es
 * `frontend/public/` —donde ya viven `favicon.svg` e `icons.svg`—, no un `import`.
 */
const SRC = resolve(__dirname, '..')
const ASSETS = join(SRC, 'assets')
const EXTENSIONES = /\.(png|jpe?g|gif|webp|avif|ico|svg)$/i

/** Ficheros de código de la interfaz, recorriendo `src` completo. */
function ficherosDeCodigo(directorio: string): string[] {
  return readdirSync(directorio).flatMap((entrada) => {
    const ruta = join(directorio, entrada)
    if (statSync(ruta).isDirectory()) {
      return entrada === 'generated' ? [] : ficherosDeCodigo(ruta)
    }
    return /\.(tsx?|css)$/.test(entrada) ? [ruta] : []
  })
}

describe('la marca institucional no viaja en el código', () => {
  it('should_not_keep_any_image_under_src_assets', () => {
    if (!existsSync(ASSETS)) return

    const imagenes = readdirSync(ASSETS).filter((f) => EXTENSIONES.test(f))

    expect(
      imagenes,
      'una imagen aquí se compila dentro del bundle y es la misma para todos los ' +
        'despliegues: la marca de una organización va por la cascada del servidor',
    ).toEqual([])
  })

  it('should_not_import_an_image_from_the_interface_code', async () => {
    const { readFileSync } = await import('node:fs')
    const { codigoSinComentarios } = await import('@/test-utils/codigoSinComentarios')
    const culpables: string[] = []

    for (const fichero of ficherosDeCodigo(SRC)) {
      // Sin comentarios: este mismo test explica arriba qué import se retiró.
      const contenido = codigoSinComentarios(readFileSync(fichero, 'utf8'))
      for (const encontrado of contenido.matchAll(/from\s+['"]([^'"]+)['"]/g)) {
        if (EXTENSIONES.test(encontrado[1])) {
          culpables.push(`${encontrado[1]} (desde ${fichero.replace(SRC, 'src')})`)
        }
      }
    }

    expect(culpables).toEqual([])
  })
})
