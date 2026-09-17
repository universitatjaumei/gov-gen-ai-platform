import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RunsPanel } from '../RunsPanel'

/**
 * DIN.6 — el diario de pasadas, en la pantalla de curación.
 *
 * Con DIN.4 y DIN.5 detrás, esta tabla es el único sitio donde se ve que la salvaguarda paró una
 * retirada entera o que la puerta de calidad dejó páginas fuera. Dos cosas que tiene que hacer
 * bien: **construirse de la respuesta del hook** —los contadores los calcula el servidor— y
 * **mostrar el ámbito de cada pasada**, porque una tabla de pasadas que no diga qué cubrió cada
 * una no se puede leer.
 */

const PASADAS = {
  total: 2,
  items: [
    {
      id: 'pasada-1',
      site_id: 'sitio-1',
      section_id: 'sec-jornadas',
      scope_label: 'Jornadas',
      started_at: '2026-09-17T10:00:00Z',
      finished_at: '2026-09-17T10:02:00Z',
      pages_total: 14,
      pages_new: 2,
      pages_changed: 1,
      pages_gone: 1,
      pages_error: 0,
      documents_auto_ingested: 2,
      documents_reingested: 1,
      documents_auto_retired: 1,
      pages_blocked_by_findings: 3,
      findings_retired: 0,
      truncated: true,
      stop_reason: 'max_pages',
      errors: ['auto-ingest https://www.uji.es/jornadas/x: revento'],
    },
    {
      id: 'pasada-2',
      site_id: 'sitio-1',
      section_id: null,
      scope_label: 'sitio',
      started_at: '2026-09-16T10:00:00Z',
      finished_at: '2026-09-16T10:05:00Z',
      pages_total: 100,
      pages_new: 0,
      pages_changed: 0,
      pages_gone: 0,
      pages_error: 0,
      documents_auto_ingested: 0,
      documents_reingested: 0,
      documents_auto_retired: 0,
      pages_blocked_by_findings: 0,
      findings_retired: 5,
      truncated: false,
      stop_reason: null,
      errors: [],
    },
  ],
}

let respuesta: unknown = PASADAS

vi.mock('@/shared/api/generated/hub-sites/hub-sites', () => ({
  useListSiteRuns: () => ({ data: respuesta, isLoading: false }),
}))

function renderizar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <RunsPanel siteId="sitio-1" />
    </QueryClientProvider>,
  )
}

describe('el diario de pasadas', () => {
  beforeEach(() => {
    respuesta = PASADAS
  })

  it('construye la tabla de la respuesta del hook', () => {
    renderizar()

    expect(screen.getByTestId('pasada-pasada-1')).toBeInTheDocument()
    expect(screen.getByTestId('pasada-pasada-2')).toBeInTheDocument()
  })

  it('muestra el ámbito de cada pasada', () => {
    renderizar()

    expect(screen.getByTestId('pasada-pasada-1')).toHaveAttribute(
      'data-ambito',
      'Jornadas',
    )
    // La del sitio entero se distingue de la de una sección: es lo que permite leer la tabla.
    expect(screen.getByTestId('pasada-pasada-2')).toHaveAttribute('data-ambito', 'sitio')
  })

  it('el detalle de errores y bloqueos se despliega, y sólo donde hay algo que contar', () => {
    renderizar()

    // La segunda pasada no tuvo errores, ni bloqueos, ni páginas fallidas, ni se truncó: no
    // ofrece detalle.
    expect(screen.queryByTestId('detalle-pasada-2')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('detalle-pasada-1'))

    expect(screen.getByTestId('truncada-pasada-1')).toBeInTheDocument()
    expect(
      screen.getByText(/auto-ingest https:\/\/www\.uji\.es\/jornadas\/x/),
    ).toBeInTheDocument()
  })

  it('una pasada con páginas que no se pudieron descargar también ofrece detalle', () => {
    /* Lo pidió la verificación en navegador: la pasada real tenía una página fallida, la tabla
       no la mencionaba y el botón de detalle no aparecía — «una página falló» es la pregunta más
       común de quien mira el diario. */
    respuesta = {
      total: 1,
      items: [
        {
          ...PASADAS.items[1],
          id: 'pasada-3',
          pages_error: 1,
          truncated: false,
          stop_reason: null,
          errors: [],
        },
      ],
    }
    renderizar()

    fireEvent.click(screen.getByTestId('detalle-pasada-3'))

    expect(screen.getByTestId('errores-de-pagina-pasada-3')).toBeInTheDocument()
  })

  it('dice cuando todavía no hay pasadas, en vez de una tabla vacía', () => {
    respuesta = { total: 0, items: [] }
    renderizar()

    expect(screen.getByTestId('sin-pasadas')).toBeInTheDocument()
  })
})
