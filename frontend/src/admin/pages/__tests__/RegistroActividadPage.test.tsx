import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { expectNoA11yViolations } from '@/test/a11y'
import { RegistroActividadPage } from '../RegistroActividadPage'

/**
 * REG.6 — la vista del registro de actividad IA.
 *
 * Lo que estos tests defienden, y por qué merece test en una tabla que «solo pinta datos»:
 *
 * **Las filas salen de la respuesta, no de una lista escrita aquí.** Es la regla de la
 * arquitectura contract-first del proyecto: el frontend no sabe qué herramientas existen ni qué
 * categorías de datos hay. Se comprueba con datos que ningún catálogo del frontend contiene.
 *
 * **Los filtros llegan al servidor.** Un filtro que filtrara en el cliente daría resultados
 * distintos según la página en la que estuvieras, y sobre un registro que alguien audita eso es
 * una respuesta falsa, no una molestia.
 *
 * **La descarga va por el cliente autorizado.** Un `<a href download>` a la API es una
 * navegación del navegador, y una navegación no lleva la cabecera de autorización: el servidor
 * responde 401 y Chrome enseña un error de descarga que no lo menciona. Ya pasó con los botones
 * de DOCX y PDF del informe de auditoría, y de ahí `descargarConAutorizacion`.
 */

const hooks = vi.hoisted(() => ({
  parametros: [] as unknown[],
  descargar: vi.fn(),
  categorias: [
    { codigo: 'datos_identificativos', nombre: 'Datos identificativos', nombre_secundario: null, vigente: true, sustituida_por: null },
    { codigo: 'datos_de_contacto', nombre: 'Datos de contacto', nombre_secundario: null, vigente: true, sustituida_por: null },
  ] as object[],
  pagina: {
    items: [
      {
        id: '11111111-1111-1111-1111-111111111111',
        ocurrido_en: '2026-09-01T08:00:00Z',
        registrado_en: '2026-09-01T08:00:05Z',
        actor: 'u-7f3a1c',
        herramienta: 'claude-cowork',
        agente: 'revisor-de-contratos',
        finalidad: 'Revisión previa de un pliego',
        modelo_usado: 'claude-opus-5',
        categorias_datos: ['datos_identificativos', 'datos_de_contacto'],
        payload_hash: null,
      },
      {
        id: '22222222-2222-2222-2222-222222222222',
        ocurrido_en: '2026-08-30T17:20:00Z',
        registrado_en: '2026-08-30T17:20:02Z',
        actor: 'u-0091ab',
        herramienta: 'copilot',
        agente: null,
        finalidad: 'Generación de una consulta SQL',
        modelo_usado: null,
        categorias_datos: [],
        payload_hash: null,
      },
    ],
    total: 2,
    page: 1,
    size: 25,
  },
}))

vi.mock('@/shared/api/generated/actividad/actividad', () => ({
  useListarActividad: vi.fn((params: unknown) => {
    hooks.parametros.push(params)
    return { data: hooks.pagina, isLoading: false, isError: false }
  }),
  useCategoriasDeDatos: vi.fn(() => ({ data: hooks.categorias, isLoading: false })),
}))

vi.mock('@/shared/api/download', () => ({
  descargarConAutorizacion: (...args: unknown[]) => hooks.descargar(...args),
}))

const ADMIN_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_') +
  '.sig'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

afterEach(() => {
  hooks.parametros = []
  hooks.descargar.mockClear()
  localStorage.clear()
  vi.restoreAllMocks()
})

function renderPage() {
  localStorage.setItem('access_token', ADMIN_TOKEN)
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <RegistroActividadPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

/** Los parámetros del último render, que es el que refleja los filtros ya aplicados. */
function ultimosParametros(): Record<string, unknown> {
  return (hooks.parametros.at(-1) ?? {}) as Record<string, unknown>
}

describe('RegistroActividadPage', () => {
  it('should_build_the_table_from_the_response', () => {
    renderPage()

    expect(screen.getByText('claude-cowork')).toBeInTheDocument()
    expect(screen.getByText('copilot')).toBeInTheDocument()
    expect(screen.getByText('Revisión previa de un pliego')).toBeInTheDocument()
    expect(screen.getByText('revisor-de-contratos')).toBeInTheDocument()
  })

  it('should_label_the_data_categories_from_the_catalogue', () => {
    /* REG.8 — la etiqueta la da el catálogo del servidor, no un diccionario del frontend.
     * Con los códigos escritos aquí, dar de alta una categoría exigiría desplegar el panel. */
    renderPage()

    expect(screen.getByText(/Datos identificativos/)).toBeInTheDocument()
    expect(screen.getByText(/Datos de contacto/)).toBeInTheDocument()
  })

  it('should_show_an_uncatalogued_code_as_it_arrived', () => {
    /* La otra mitad de «se anuncia, no se impone».
     *
     * El servidor acepta cualquier código, así que llegarán algunos que no están en el
     * catálogo. Esconderlos o pintarlos como «—» ocultaría precisamente la señal de que al
     * catálogo le falta una entrada, y entonces nadie lo curaría nunca. Se enseña el código
     * crudo, que es donde alguien lo va a ver. */
    hooks.pagina = {
      ...hooks.pagina,
      items: [{ ...(hooks.pagina.items[0] as object), categorias_datos: ['codigo_sin_catalogar'] }],
    }
    renderPage()

    expect(screen.getByText(/codigo_sin_catalogar/)).toBeInTheDocument()
  })

  it('should_send_the_tool_filter_to_the_server', async () => {
    renderPage()

    await act(async () => {
      fireEvent.change(screen.getByLabelText('Herramienta'), {
        target: { value: 'copilot' },
      })
    })

    expect(ultimosParametros().herramienta).toBe('copilot')
  })

  it('should_send_the_date_range_to_the_server', async () => {
    renderPage()

    await act(async () => {
      fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-09-01' } })
    })
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-09-03' } })
    })

    /* Que los dos extremos viajan, y que van como instante ISO y no como el `AAAA-MM-DD` del
       selector: el servidor filtra por instantes. Cuál es el instante exacto lo fija el test
       siguiente, que es donde está la sutileza de la zona horaria. */
    const params = ultimosParametros()
    expect(params.desde).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/)
    expect(params.hasta).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/)
    expect(new Date(String(params.desde)).getTime()).toBeLessThan(
      new Date(String(params.hasta)).getTime(),
    )
  })

  it('should_take_the_day_boundaries_from_the_viewers_own_calendar', async () => {
    /* El selector da un día del calendario y el servidor filtra por instantes.
     *
     * Componer `${fecha}T00:00:00Z` a mano fija el límite en UTC: para alguien en Madrid,
     * «desde el 1 de septiembre» empezaría a las dos de la madrugada del 1 y dejaría fuera,
     * sin decirlo, las dos primeras horas del día que pidió. Sobre un registro que alguien
     * audita, una omisión que no se ve es peor que un error que se ve.
     *
     * El test compara con lo que da el propio motor de fechas del entorno, así que vale en
     * cualquier zona en la que se ejecute la suite —incluida UTC, donde ambas formas coinciden
     * y la comparación sigue siendo cierta. */
    renderPage()

    await act(async () => {
      fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-09-01' } })
    })
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-09-03' } })
    })

    const params = ultimosParametros()
    expect(params.desde).toBe(new Date('2026-09-01T00:00:00.000').toISOString())
    expect(params.hasta).toBe(new Date('2026-09-03T23:59:59.999').toISOString())
  })

  it('should_not_send_an_empty_filter_as_a_parameter', async () => {
    renderPage()

    await act(async () => {
      fireEvent.change(screen.getByLabelText('Herramienta'), { target: { value: 'copilot' } })
    })
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Herramienta'), { target: { value: '' } })
    })

    // Un `herramienta=` vacío es un filtro que el servidor tiene que decidir ignorar. Mejor no
    // mandarlo: la petición dice lo que se pide y no lo que se dejó de pedir.
    expect(ultimosParametros().herramienta).toBeUndefined()
  })

  it('should_download_the_csv_through_the_authorised_client', async () => {
    renderPage()

    await act(async () => {
      fireEvent.change(screen.getByLabelText('Herramienta'), { target: { value: 'copilot' } })
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Exportar/ }))
    })

    expect(hooks.descargar).toHaveBeenCalledTimes(1)
    const [ruta] = hooks.descargar.mock.calls[0] as [string]
    expect(ruta).toContain('/actividad/export')
    expect(ruta).toContain('herramienta=copilot')
  })

  it('should_page_through_the_results', async () => {
    hooks.pagina = { ...hooks.pagina, total: 60 }
    renderPage()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Siguiente/ }))
    })

    expect(ultimosParametros().page).toBe(2)
  })

  it('should_not_offer_a_next_page_when_there_is_none', () => {
    hooks.pagina = { ...hooks.pagina, total: 2 }
    renderPage()

    expect(screen.getByRole('button', { name: /Siguiente/ })).toBeDisabled()
  })

  it('should_explain_an_empty_register_instead_of_showing_an_empty_table', () => {
    hooks.pagina = { items: [], total: 0, page: 1, size: 25 }
    renderPage()

    // Un registro vacío es el estado normal antes de que nadie haya conectado una herramienta.
    // Una tabla con cabeceras y nada debajo parece una avería.
    expect(screen.getByText(/Todavía no hay/)).toBeInTheDocument()
  })

  it('should_not_claim_the_register_is_empty_when_a_filter_matched_nothing', async () => {
    /* El defecto que salió verificando en el navegador.
     *
     * Con un filtro puesto y cero coincidencias se enseñaba «todavía no hay actividad
     * registrada. Aparecerá aquí cuando una herramienta externa empiece a declararla», que es
     * falso: hay actividad, pero no ésa. Quien lo lee concluye que el registro no funciona en
     * vez de que su filtro no acierta. */
    hooks.pagina = { items: [], total: 0, page: 1, size: 25 }
    renderPage()

    await act(async () => {
      fireEvent.change(screen.getByLabelText('Herramienta'), {
        target: { value: 'no-existe' },
      })
    })

    expect(screen.queryByText(/Todavía no hay/)).not.toBeInTheDocument()
    expect(screen.getByText(/coincide con el filtro/)).toBeInTheDocument()
  })

  it('should_have_no_hardcoded_strings', async () => {
    renderPage()
    const conEspanol = screen.getByText('Registro de actividad IA')

    await i18n.changeLanguage('en')
    expect(conEspanol.textContent).not.toBe('Registro de actividad IA')
    await i18n.changeLanguage('es')
  })

  it('should_be_accessible', async () => {
    const { container } = renderPage()
    await expectNoA11yViolations(container)
  })
})
