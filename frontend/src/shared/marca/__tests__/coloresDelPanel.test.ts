import { readFileSync } from 'node:fs'
import { describe, it, expect, beforeEach } from 'vitest'

import { VARIABLE_POR_COLOR, aplicarColoresDelPanel } from '../coloresDelPanel'

/**
 * REV.9 — la cascada de color llega al panel.
 *
 * El hallazgo no era «falta un color»: eran **dos fuentes de verdad que no se hablaban**. La
 * paleta del contrato servía al widget, el panel se pintaba con las variables de `index.css`
 * escritas a mano, y el único consumidor de la cascada era el logotipo. Se podía cambiar
 * cualquier color en «Identidad visual» y no cambiaba nada.
 */
describe('REV.9 — aplicar la paleta al panel', () => {
  let raiz: HTMLElement

  beforeEach(() => {
    raiz = document.createElement('div')
  })

  it('should_write_the_sidebar_colour_the_user_could_not_find', () => {
    // Es el color por el que se destapó todo: `#0b5394` estaba en `index.css` y no aparecía en
    // ninguna parte de la pantalla de identidad visual.
    aplicarColoresDelPanel({ sidebar: '#123456' }, raiz)

    expect(raiz.style.getPropertyValue('--sidebar')).toBe('#123456')
  })

  it('should_write_every_token_the_theme_defines', () => {
    const colores = Object.fromEntries(
      Object.keys(VARIABLE_POR_COLOR).map((campo, i) => [campo, `#00000${i % 10}`]),
    )

    const escritas = aplicarColoresDelPanel(colores, raiz)

    expect(escritas.sort()).toEqual(Object.values(VARIABLE_POR_COLOR).sort())
  })

  it('should_leave_alone_what_the_theme_does_not_define', () => {
    // La diferencia entre «este nivel no lo configura» —y manda `index.css`— y «este nivel lo
    // pone vacío», que dejaría el panel sin color.
    raiz.style.setProperty('--sidebar', '#0b5394')

    aplicarColoresDelPanel({ primary: '#ff0000' }, raiz)

    expect(raiz.style.getPropertyValue('--sidebar')).toBe('#0b5394')
    expect(raiz.style.getPropertyValue('--primary')).toBe('#ff0000')
  })

  it('should_ignore_a_value_that_is_not_a_colour_string', () => {
    aplicarColoresDelPanel({ sidebar: null, primary: '   ', ring: 42 } as never, raiz)

    expect(raiz.style.getPropertyValue('--sidebar')).toBe('')
    expect(raiz.style.getPropertyValue('--primary')).toBe('')
    expect(raiz.style.getPropertyValue('--ring')).toBe('')
  })

  it('should_do_nothing_without_a_palette', () => {
    expect(aplicarColoresDelPanel(undefined, raiz)).toEqual([])
  })

  it('should_only_map_fields_the_contract_declares', () => {
    // El mapa es la única lista de campos que queda escrita en el frontend, así que se
    // comprueba contra el contrato generado: si el servidor renombra un color, esto se pone
    // rojo en vez de dejar de aplicarlo en silencio.
    const contrato = readFileSync('src/shared/api/generated/model/themeColors.ts', 'utf-8')
    const declarados = [...contrato.matchAll(/^\s{2}(\w+)\??:/gm)].map(m => m[1])

    expect(declarados.length).toBeGreaterThan(15)
    expect(Object.keys(VARIABLE_POR_COLOR).filter(c => !declarados.includes(c))).toEqual([])
  })
})
