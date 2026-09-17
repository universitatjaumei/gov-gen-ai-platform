import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SectionsPanel } from '../SectionsPanel'

/**
 * DIN.3 — parametrizar los apartados como secciones, desde la curación.
 *
 * Tres cosas que la pantalla tiene que hacer bien, y ninguna es CRUD:
 *
 * 1. **Construirse del contrato.** La cadencia efectiva y la bandera de si es heredada las
 *    calcula el servidor (`parametros_efectivos`, DIN.1). Si el frontend las dedujera —«si
 *    `crawl_interval_hours` es nulo, pon la del sitio»— tendría una copia de la regla de herencia,
 *    y la copia se quedaría atrás en cuanto el servidor cambiara de criterio.
 * 2. **Distinguir la cadencia heredada de la propia.** Sin decirlo, cambiar la del sitio parecería
 *    no hacer nada en las secciones que la heredan.
 * 3. **Probar el patrón antes de guardar**, y decirlo alto cuando no casa nada: un regex que
 *    compila y no selecciona ninguna página se descubriría, si no, cuando la pasada siguiente no
 *    ingiere nada.
 */

const crear = vi.fn()
const editar = vi.fn()
const borrar = vi.fn()
const probar = vi.fn()

const SECCIONES = [
  {
    id: 'sec-jornadas',
    site_id: 'sitio-1',
    name: 'Jornadas',
    pattern: '/jornadas',
    pattern_kind: 'path_prefix',
    crawl_interval_hours: null,
    crawl_interval_hours_effective: 168,
    crawl_interval_inherited: true,
    mode: 'manual',
    criteria_json: null,
    owner: 'Secretaría General',
    last_crawled_at: null,
    is_active: true,
    created_at: '2026-09-17T10:00:00Z',
  },
  {
    id: 'sec-eventos',
    site_id: 'sitio-1',
    name: 'Eventos',
    pattern: '/eventos',
    pattern_kind: 'path_prefix',
    crawl_interval_hours: 6,
    crawl_interval_hours_effective: 6,
    crawl_interval_inherited: false,
    mode: 'automatic',
    criteria_json: null,
    owner: null,
    last_crawled_at: '2026-09-17T09:00:00Z',
    is_active: true,
    created_at: '2026-09-17T10:00:00Z',
  },
]

let secciones = SECCIONES

vi.mock('@/shared/api/generated/hub-sites/hub-sites', () => ({
  useListSiteSections: () => ({ data: secciones, isLoading: false }),
  useCreateSiteSection: () => ({ mutate: crear, isPending: false }),
  usePatchSiteSection: () => ({ mutate: editar, isPending: false }),
  useDeleteSiteSection: () => ({ mutate: borrar, isPending: false }),
  useTestSectionPattern: () => ({ mutateAsync: probar, isPending: false }),
  getListSiteSectionsQueryKey: () => ['sections'],
}))

function renderizar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <SectionsPanel siteId="sitio-1" />
    </QueryClientProvider>,
  )
}

describe('las secciones de un sitio, en la pantalla de curación', () => {
  beforeEach(() => {
    secciones = SECCIONES
    crear.mockClear()
    editar.mockClear()
    borrar.mockClear()
    probar.mockClear()
  })

  it('construye la lista de lo que devuelve el hook, sin deducir nada', () => {
    renderizar()

    expect(screen.getByTestId('seccion-sec-jornadas')).toBeInTheDocument()
    expect(screen.getByTestId('seccion-sec-eventos')).toBeInTheDocument()
    expect(screen.getByText('/jornadas')).toBeInTheDocument()
  })

  it('distingue la cadencia heredada de la propia', () => {
    /* Se comprueban los datos y no el texto: en los tests i18next no tiene recursos cargados y
       `t()` devuelve la clave, así que afirmar sobre la traducción probaría el idioma y no la
       pantalla. Lo que importa es que la cifra y su procedencia lleguen desde el contrato. */
    renderizar()

    const heredada = screen.getByTestId('cadencia-sec-jornadas')
    const propia = screen.getByTestId('cadencia-sec-eventos')

    expect(heredada).toHaveAttribute('data-horas', '168')
    expect(heredada).toHaveAttribute('data-heredada', 'true')
    expect(propia).toHaveAttribute('data-horas', '6')
    expect(propia).toHaveAttribute('data-heredada', 'false')
  })

  it('dice que un sitio sin secciones se rastrea entero, como hasta ahora', () => {
    secciones = []
    renderizar()

    expect(screen.getByTestId('sin-secciones')).toBeInTheDocument()
  })

  it('«Probar patrón» pinta el recuento y la muestra antes de guardar', async () => {
    probar.mockResolvedValue({
      matched: 14,
      total: 349,
      sample: ['https://www.uji.es/jornadas/uno', 'https://www.uji.es/jornadas/dos'],
    })
    renderizar()
    fireEvent.click(screen.getByTestId('btn-nueva-seccion'))
    fireEvent.change(screen.getByTestId('campo-seccion-patron'), {
      target: { value: '/jornadas' },
    })

    fireEvent.click(screen.getByTestId('btn-probar-patron'))

    await waitFor(() =>
      expect(screen.getByTestId('resultado-patron')).toBeInTheDocument(),
    )
    const resultado = screen.getByTestId('resultado-patron')
    expect(resultado).toHaveAttribute('data-casan', '14')
    expect(resultado).toHaveAttribute('data-total', '349')
    expect(resultado.textContent).toContain('https://www.uji.es/jornadas/uno')
  })

  it('avisa cuando el patrón no casa ninguna página', async () => {
    probar.mockResolvedValue({ matched: 0, total: 349, sample: [] })
    renderizar()
    fireEvent.click(screen.getByTestId('btn-nueva-seccion'))
    fireEvent.change(screen.getByTestId('campo-seccion-patron'), {
      target: { value: '/jornades' },
    })

    fireEvent.click(screen.getByTestId('btn-probar-patron'))

    await waitFor(() =>
      expect(screen.getByTestId('patron-no-casa-nada')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('resultado-patron')).toHaveAttribute('data-casan', '0')
  })

  it('el botón de probar está desactivado mientras no hay patrón', () => {
    renderizar()
    fireEvent.click(screen.getByTestId('btn-nueva-seccion'))

    expect(screen.getByTestId('btn-probar-patron')).toBeDisabled()
  })

  it('guarda la sección sin cadencia cuando el campo se deja vacío: hereda la del sitio', async () => {
    renderizar()
    fireEvent.click(screen.getByTestId('btn-nueva-seccion'))
    fireEvent.change(screen.getByTestId('campo-seccion-nombre'), {
      target: { value: 'Becas' },
    })
    fireEvent.change(screen.getByTestId('campo-seccion-patron'), {
      target: { value: '/becas' },
    })

    fireEvent.click(screen.getByTestId('btn-guardar-seccion'))

    await waitFor(() => expect(crear).toHaveBeenCalled())
    const enviado = crear.mock.calls[0][0].data
    expect(enviado.name).toBe('Becas')
    expect(enviado.pattern).toBe('/becas')
    // Nada de un 24 inventado por la pantalla: vacío es heredar, y eso lo resuelve el servidor.
    expect(enviado.crawl_interval_hours).toBeUndefined()
    // Y nace en manual: la primera pasada la revisa una persona.
    expect(enviado.mode).toBe('manual')
  })

  it('cambiar el modo de una sección manda sólo el modo', async () => {
    renderizar()

    fireEvent.change(screen.getByTestId('modo-sec-jornadas'), {
      target: { value: 'automatic' },
    })

    await waitFor(() => expect(editar).toHaveBeenCalled())
    expect(editar.mock.calls[0][0]).toMatchObject({
      sectionId: 'sec-jornadas',
      data: { mode: 'automatic' },
    })
  })
})
