import { describe, it, expect } from 'vitest'
import { execFileSync } from 'node:child_process'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { codigoSinComentarios } from '@/test-utils/codigoSinComentarios'

/**
 * Los assets que importa la interfaz tienen que estar en git.
 *
 * Encontrado en integración continua: `AppLayout` importa `@/assets/logo-uji.png`, el fichero
 * está en el disco del desarrollador y **`.gitignore` lo excluía** con un `*.png` pensado para
 * capturas de pantalla. Resultado: en local compila y pasa todo, y en CI —donde solo existe lo
 * versionado— falla la resolución del import y se cae la suite entera.
 *
 * Es un fallo que por definición no se ve donde se programa, así que el guardarraíl no puede
 * limitarse a comprobar que el fichero existe: tiene que comprobar que **está versionado**.
 */

const RAIZ_REPO = resolve(__dirname, '../../..')
const SRC = resolve(__dirname, '..')
const EXTENSIONES = /\.(png|jpe?g|gif|webp|svg|avif|ico)$/i

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

/** Rutas de asset referenciadas con el alias `@/`, que es como se importan aquí. */
function assetsReferenciados(): { desde: string; asset: string }[] {
  const referencias: { desde: string; asset: string }[] = []
  for (const fichero of ficherosDeCodigo(SRC)) {
    // Sin comentarios: la explicación de por qué se retiró un asset menciona su ruta, y
    // buscarla en el fichero entero convertía esa explicación en un falso positivo.
    const contenido = codigoSinComentarios(readFileSync(fichero, 'utf8'))
    for (const encontrado of contenido.matchAll(/['"]@\/([^'"]+)['"]/g)) {
      const asset = encontrado[1]
      if (EXTENSIONES.test(asset)) referencias.push({ desde: fichero, asset })
    }
  }
  return referencias
}

const versionados = new Set(
  execFileSync('git', ['ls-files', 'frontend/src'], { cwd: RAIZ_REPO, encoding: 'utf8' })
    .split('\n')
    .filter(Boolean),
)

describe('assets de la interfaz', () => {
  it('should_referenciar_solo_assets_que_existen_en_el_disco', () => {
    const inexistentes = assetsReferenciados().filter(
      ({ asset }) => !existsSync(join(SRC, asset)),
    )
    expect(inexistentes).toEqual([])
  })

  it('should_referenciar_solo_assets_versionados_en_git', () => {
    const sinVersionar = assetsReferenciados()
      .filter(({ asset }) => !versionados.has(`frontend/src/${asset}`))
      .map(({ desde, asset }) => `${asset} (importado desde ${desde.replace(RAIZ_REPO, '')})`)

    expect(
      sinVersionar,
      'estos assets no están en git: en integración continua el import no resuelve y la ' +
        'compilación falla, aunque en local funcione',
    ).toEqual([])
  })
})
