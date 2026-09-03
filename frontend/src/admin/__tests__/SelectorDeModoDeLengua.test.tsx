import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import i18n from '@/shared/i18n'
import { SelectorDeModoDeLengua } from '../components/SelectorDeModoDeLengua'
import { useOpcionesDeLengua } from '@/shared/api/generated/hub-opciones/hub-opciones'

/**
 * LANG.2 — el modo de lengua, elegido desde el contrato y no desde una lista escrita en React.
 *
 * **Dos cosas que el panel decía y no eran verdad**, encontradas al escribir esto:
 *
 * - `ChatbotsPage` ofrecía **`strict`**, y la factoría del grafo no compuso nunca
 *   `StrictLanguagePolicy`: era una opción que no hacía nada. Después de LANG.1 es peor, porque
 *   además el servidor la rechaza con 422.
 * - `ValoresPorDefectoPage` sugería **`neutral`**, que no es ningún valor válido —es el nombre de
 *   la clase, y el modo se llama `none`—.
 *
 * Las dos son el mismo defecto que PLAT.2 documentó como «el menú promete lo que la API niega», y
 * las dos desaparecen por construcción cuando la lista viene del servidor.
 *
 * **Y el catálogo trae la lengua en el código del corpus**, que es `val` y no `ca`: si el panel
 * enviara `fixed:ca` la validación lo aceptaría —la forma es correcta— y la preferencia no
 * casaría con ninguna versión de ninguna norma, en silencio.
 */
vi.mock('@/shared/api/generated/hub-opciones/hub-opciones', () => ({
  useOpcionesDeLengua: vi.fn(),
}))

const CATALOGO = {
  modos: [
    { valor: 'prefer', requiere_lengua: false, es_por_defecto: true },
    { valor: 'none', requiere_lengua: false, es_por_defecto: false },
    { valor: 'fixed', requiere_lengua: true, es_por_defecto: false },
  ],
  lenguas: [
    { codigo: 'val', etiqueta: 'Valencià' },
    { codigo: 'es', etiqueta: 'Castellano' },
    { codigo: 'en', etiqueta: 'English' },
  ],
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.mocked(useOpcionesDeLengua).mockReturnValue({
    data: CATALOGO,
    isLoading: false,
  } as never)
})

function pintar(valor: string, onChange = vi.fn()) {
  render(<SelectorDeModoDeLengua valor={valor} onChange={onChange} />)
  return onChange
}

const modo = () => screen.getByLabelText(/modo de idioma/i) as HTMLSelectElement
const lengua = () => screen.getByLabelText(/idioma de la respuesta/i) as HTMLSelectElement

describe('LANG.2 — el desplegable se construye desde el contrato', () => {
  it('should_offer_exactly_the_modes_the_server_sent', () => {
    pintar('prefer')

    const valores = Array.from(modo().options).map((o) => o.value)
    expect(valores).toEqual(['prefer', 'none', 'fixed'])
  })

  it('should_not_offer_the_modes_that_never_worked', () => {
    /** `strict` no lo compone la factoría y `neutral` no es un valor: ninguno puede aparecer. */
    pintar('prefer')

    const valores = Array.from(modo().options).map((o) => o.value)
    expect(valores).not.toContain('strict')
    expect(valores).not.toContain('neutral')
  })

  it('should_use_the_corpus_code_for_the_languages', () => {
    pintar('fixed:val')

    const valores = Array.from(lengua().options).map((o) => o.value)
    expect(valores).toEqual(['val', 'es', 'en'])
    expect(valores).not.toContain('ca')
  })
})

describe('LANG.2 — el valor actual se muestra', () => {
  it('should_show_prefer_as_the_selected_mode', () => {
    pintar('prefer')
    expect(modo().value).toBe('prefer')
  })

  it('should_split_a_fixed_value_into_mode_and_language', () => {
    pintar('fixed:es')

    expect(modo().value).toBe('fixed')
    expect(lengua().value).toBe('es')
  })

  it('should_not_show_the_language_selector_for_a_mode_that_does_not_need_it', () => {
    /** `requiere_lengua` lo dice el servidor; el panel no lo deduce de que el valor sea «fixed». */
    pintar('none')

    expect(modo().value).toBe('none')
    expect(screen.queryByLabelText(/idioma de la respuesta/i)).toBeNull()
  })
})

describe('LANG.2 — lo que se guarda', () => {
  it('should_send_the_plain_mode_when_no_language_is_needed', () => {
    const onChange = pintar('prefer')

    fireEvent.change(modo(), { target: { value: 'none' } })

    expect(onChange).toHaveBeenCalledWith('none')
  })

  it('should_compose_the_fixed_value_with_the_chosen_language', () => {
    const onChange = pintar('fixed:val')

    fireEvent.change(lengua(), { target: { value: 'es' } })

    expect(onChange).toHaveBeenCalledWith('fixed:es')
  })

  it('should_compose_a_valid_value_the_moment_fixed_is_chosen', () => {
    /** Sin esto, elegir «fijar» y guardar mandaría `fixed:` a secas, que es un 422. */
    const onChange = pintar('prefer')

    fireEvent.change(modo(), { target: { value: 'fixed' } })

    expect(onChange).toHaveBeenCalledWith('fixed:val')
  })
})

describe('LANG.2 — mientras el catálogo no ha llegado', () => {
  it('should_not_invent_options_of_its_own', () => {
    vi.mocked(useOpcionesDeLengua).mockReturnValue({ data: undefined, isLoading: true } as never)

    pintar('prefer')

    // Ni desplegable con opciones inventadas ni un `onChange` que pise el valor guardado.
    expect(screen.queryByLabelText(/modo de idioma/i)).toBeNull()
  })
})
