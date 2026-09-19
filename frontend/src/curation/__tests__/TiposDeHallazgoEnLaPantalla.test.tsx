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

/**
 * DIN.4 — la lista se **lee del contrato**, no se escribe aquí.
 *
 * Estaba a mano, y eso convertía este guardarraíl en la misma cosa contra la que existe: al
 * añadir `page_gone` y `retirada_masiva_detenida` el test habría seguido verde con la pantalla
 * incapaz de nombrarlos. Los tipos que cuelgan de un chatbot (`content_gap`, `revisio_vencuda`,
 * `copia_divergent`) se excluyen: no salen de auditar páginas y no se listan en esta pantalla,
 * que filtra hallazgos de sitio.
 */
const TIPOS_DE_CHATBOT = ['content_gap', 'revisio_vencuda', 'copia_divergent']

function tiposQueEmiteElBackend(): string[] {
  const contrato = readFileSync(
    resolve(__dirname, '../../../../server/app/modules/curation/contracts.py'),
    'utf8',
  )
  const literal = contrato.match(/FindingType = Literal\[([\s\S]*?)\n\]/)
  if (!literal) throw new Error('no se encontró FindingType en contracts.py')

  return [...literal[1].matchAll(/^\s*"([a-z_]+)",/gm)]
    .map((m) => m[1])
    .filter((tipo) => !TIPOS_DE_CHATBOT.includes(tipo))
}

const TIPOS_QUE_EMITE_EL_BACKEND = tiposQueEmiteElBackend()

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
