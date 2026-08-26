import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { EnlaceAlFuente } from '../EnlaceAlFuente'

/**
 * AIS.6 — El enlace al fuente que exige el §13 de la AGPL.
 *
 * El README lo tenía como «pendiente de implementar» y fijaba tres condiciones que no son
 * opcionales. Este fichero comprueba las tres:
 *
 * 1. **Va en la interfaz del despliegue**, no en el README. La obligación es de quien ejecuta
 *    la versión modificada, frente a los usuarios de **esa** instancia.
 * 2. **Apunta al fuente de esa versión** —el fork, en el commit desplegado—, así que tiene que
 *    ser configuración (`SOURCE_URL`). Una URL fija al principal haría que cualquier despliegue
 *    modificado incumpliera creyendo que cumple.
 * 3. **Tiene que verse donde están los usuarios**, y eso incluye el **widget público**: la
 *    ciudadanía que usa el chatbot también interactúa remotamente con el programa. Es el caso
 *    que el propio README señala como el que se olvida.
 *
 * Y una cuarta que no está en el README pero se deduce: el §13 se activa **si se modifica** el
 * programa. Quien despliegue el código tal cual no queda sujeto, así que con `SOURCE_URL` vacía
 * no se pinta nada — forzar un enlace ahí sería inventarse un requisito que la licencia no pone.
 */
const SRC = resolve(__dirname, '..', '..', '..')

function respondeCon(cuerpo: unknown, ok = true) {
  return vi.fn().mockResolvedValue({ ok, json: async () => cuerpo })
}

beforeEach(() => {
  vi.unstubAllGlobals()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('EnlaceAlFuente', () => {
  it('should_render_the_link_when_the_deployment_declares_it', async () => {
    vi.stubGlobal('fetch', respondeCon({ source_url: 'https://git.example.org/fork' }))

    render(<EnlaceAlFuente />)

    const enlace = await screen.findByTestId('enlace-al-fuente')
    expect(enlace).toHaveAttribute('href', 'https://git.example.org/fork')
    // Abre fuera y sin arrastrar la sesión al destino.
    expect(enlace).toHaveAttribute('target', '_blank')
    expect(enlace.getAttribute('rel')).toContain('noopener')
  })

  it('should_render_nothing_when_source_url_is_empty', async () => {
    vi.stubGlobal('fetch', respondeCon({ source_url: null }))

    const { container } = render(<EnlaceAlFuente />)

    await waitFor(() => expect(screen.queryByTestId('enlace-al-fuente')).toBeNull())
    expect(container.textContent).toBe('')
  })

  it('should_not_break_the_screen_when_the_endpoint_fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('sin red')))

    const { container } = render(<EnlaceAlFuente />)

    await waitFor(() => expect(container.textContent).toBe(''))
  })

  it('should_not_hardcode_the_upstream_url', () => {
    /**
     * La comprobación que de verdad importa para la gobernanza: si la URL estuviera escrita
     * aquí apuntaría al principal, y **cualquier despliegue modificado estaría incumpliendo**
     * mientras enseña un enlace que parece cumplir. Por eso sale de configuración.
     */
    const fuente = readFileSync(resolve(SRC, 'shared/licencia/EnlaceAlFuente.tsx'), 'utf8')
    const urls = fuente.match(/https?:\/\/[^\s'"`)]+/g) ?? []

    expect(
      urls,
      `el componente trae URLs escritas a mano (${urls.join(', ')}): el §13 pide el fuente de ` +
        'ESA versión, no el del proyecto de origen',
    ).toEqual([])
  })
})

describe('el §13 llega a los dos sitios donde hay usuarios', () => {
  it('should_show_the_link_in_the_admin_panel', () => {
    const layout = readFileSync(resolve(SRC, 'admin/AppLayout.tsx'), 'utf8')
    expect(layout).toMatch(/EnlaceAlFuente/)
  })

  it('should_show_the_link_in_the_public_widget', () => {
    /** El caso que el README llama «el que se olvida». */
    const widget = readFileSync(resolve(SRC, 'widget/components/ChatWidget.tsx'), 'utf8')
    expect(
      widget,
      'el widget público no enseña el enlace al fuente: la ciudadanía que lo usa también son ' +
        'usuarios que interactúan remotamente con el programa, y son los más numerosos',
    ).toMatch(/EnlaceAlFuente/)
  })
})

describe('cuando el fetch del sitio anfitrion no se comporta', () => {
  /**
   * **Esto rompió 25 tests del widget en CI y habría roto el widget en producción.**
   *
   * El componente encadenaba `fetch(...).then(...)` directamente. En una web ajena —que es
   * donde vive el widget— `fetch` puede estar parcheado, restringido por CSP o devolver algo
   * que no es una promesa, y entonces el `.then()` lanza **de forma síncrona dentro del
   * efecto**: se lleva por delante el árbol de React entero en vez de dejar el enlace sin
   * pintar.
   *
   * La regla ya estaba escrita en el componente —«que no se pueda leer no rompe la pantalla»—;
   * lo que fallaba era que la forma del código no la cumplía en todos los casos.
   */
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('should_not_crash_when_fetch_returns_something_that_is_not_a_promise', () => {
    // `vi.fn()` sin implementación devuelve `undefined`: exactamente el caso de CI.
    expect(() => render(<EnlaceAlFuente />)).not.toThrow()
    expect(screen.queryByTestId('enlace-al-fuente')).toBeNull()
  })

  it('should_not_crash_when_fetch_rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('bloqueado por CSP')))

    render(<EnlaceAlFuente />)

    await waitFor(() => {
      expect(screen.queryByTestId('enlace-al-fuente')).toBeNull()
    })
  })
})
