import { describe, it, expect } from 'vitest'
import es from '@/shared/i18n/locales/es/curation.json'
import ca from '@/shared/i18n/locales/ca/curation.json'
import en from '@/shared/i18n/locales/en/curation.json'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/**
 * Un hallazgo que la pantalla no sabe nombrar ni filtrar no existe para quien cura (RAS.5).
 *
 * El backend emite dos tipos nuevos —`needs_javascript` (RAS.2) y `content_updated` (RAS.5)— y la
 * pantalla de hallazgos tenía la lista de tipos **escrita a mano**: no estaban en el filtro y su
 * columna «Tipo» habría salido con la clave de traducción en crudo. Es el mismo patrón que ya
 * apareció con los tipos de gráfico y las operaciones de ETL en el bloque GUI: una lista a mano que
 * se separa del contrato.
 */

const TIPOS_QUE_EMITE_EL_BACKEND = [
  'superseded',
  'duplicate',
  'contradiction',
  'empty',
  'thin',
  'stale',
  'crawl_error',
  'orphan_page',
  'needs_javascript',
  'content_updated',
]

describe('los tipos de hallazgo de la pantalla', () => {
  it('el filtro ofrece todos los que el backend puede emitir', () => {
    const fuente = readFileSync(
      resolve(__dirname, '../FindingsPage.tsx'),
      'utf8',
    )

    for (const tipo of TIPOS_QUE_EMITE_EL_BACKEND) {
      expect(fuente, `falta «${tipo}» en el filtro de tipos`).toContain(`'${tipo}'`)
    }
  })

  it.each([
    ['es', es],
    ['ca', ca],
    ['en', en],
  ])('en %s cada tipo tiene su nombre', (_idioma, traducciones) => {
    for (const tipo of TIPOS_QUE_EMITE_EL_BACKEND) {
      expect(
        (traducciones as Record<string, string>)[`type_${tipo}`],
        `falta type_${tipo}`,
      ).toBeTruthy()
    }
  })
})
