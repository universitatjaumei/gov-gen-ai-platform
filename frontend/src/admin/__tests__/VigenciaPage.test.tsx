import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { VigenciaPage } from '../pages/VigenciaPage'
import { useListChatbotsApiV1HubChatbotsGet } from '@/shared/api/generated/hub-chatbots/hub-chatbots'
import { useListPendingVigenciaApiV1HubIngestionChatbotIdVigenciaGet } from '@/shared/api/generated/hub-ingestion/hub-ingestion'

/**
 * Pantalla de la cola de validación de vigencia (A7).
 *
 * El asistente advierte de cada documento cuya vigencia nadie ha comprobado, pero hasta
 * ahora no había forma de ver *cuáles* son ni cuántos quedan: el aviso se repetía sin que
 * hubiera un sitio donde ir tachándolos.
 *
 * Los hooks se doblan, no `fetch`: la página habla por el cliente de Orval.
 */
vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useListChatbotsApiV1HubChatbotsGet: vi.fn(),
}))
vi.mock('@/shared/api/generated/hub-ingestion/hub-ingestion', () => ({
  useListPendingVigenciaApiV1HubIngestionChatbotIdVigenciaGet: vi.fn(),
}))

const TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

const CHATBOTS = [
  { id: 'cb-1', name: 'Normativa UJI' },
  { id: 'cb-2', name: 'Gerència' },
]

const PENDIENTES = {
  total: 297,
  pendents: 2,
  documents: [
    {
      id: 'doc-1',
      title: 'Reglament de la Sindicatura de Greuges',
      language: 'va',
      canonical_url: 'https://www.uji.es/sindicatura.pdf',
      id_publicacio: 'REG-042',
      estat_vigencia: 'vigent',
      vigencia_validada_el: null,
      data_revisio_prevista: '2026-03-01',
      revisat_per: null,
      motiu: 'sense_validar',
    },
    {
      id: 'doc-2',
      title: 'Instrucció de contractes menors',
      language: 'va',
      canonical_url: 'https://www.uji.es/contractes.pdf',
      id_publicacio: 'INS-004',
      estat_vigencia: 'derogat',
      vigencia_validada_el: '2026-01-01T00:00:00Z',
      data_revisio_prevista: null,
      revisat_per: 'secretaria',
      motiu: 'estat_no_vigent',
    },
  ],
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useListChatbotsApiV1HubChatbotsGet).mockReturnValue({
    data: CHATBOTS,
    isLoading: false,
  } as any)
})

function renderPage(data: object | undefined = PENDIENTES, isLoading = false) {
  vi.mocked(useListPendingVigenciaApiV1HubIngestionChatbotIdVigenciaGet).mockReturnValue({
    data,
    isLoading,
  } as any)

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <VigenciaPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('VigenciaPage', () => {
  it('should_list_the_documents_pending_validation', async () => {
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Reglament de la Sindicatura de Greuges')).toBeDefined()
      expect(screen.getByText('Instrucció de contractes menors')).toBeDefined()
    })
  })

  it('should_show_how_many_are_pending_out_of_the_whole_corpus', async () => {
    renderPage()

    // Sin el total, «2 pendientes» no dice si el corpus está bien o fatal.
    const resumen = await screen.findByTestId('vigencia-resumen')
    expect(resumen.textContent).toContain('2')
    expect(resumen.textContent).toContain('297')
  })

  it('should_say_why_each_document_is_pending', async () => {
    renderPage()

    // Dentro de la tabla: los mismos textos son también las opciones del filtro, y los dos
    // motivos piden trabajo distinto —uno es revisar, el otro retirar o marcar—.
    const tabla = await screen.findByRole('table')
    await waitFor(() => {
      expect(within(tabla).getByText('Sin validar')).toBeDefined()
      expect(within(tabla).getByText('Estado no vigente')).toBeDefined()
    })
  })

  it('should_link_each_document_to_its_source_so_it_can_be_checked', async () => {
    renderPage()

    const enlace = await screen.findByRole('link', {
      name: /Reglament de la Sindicatura de Greuges/i,
    })
    expect(enlace.getAttribute('href')).toBe('https://www.uji.es/sindicatura.pdf')
  })

  it('should_filter_by_reason', async () => {
    renderPage()

    await screen.findByText('Instrucció de contractes menors')
    fireEvent.change(screen.getByTestId('vigencia-filtro-motiu'), {
      target: { value: 'estat_no_vigent' },
    })

    expect(screen.queryByText('Reglament de la Sindicatura de Greuges')).toBeNull()
    expect(screen.getByText('Instrucció de contractes menors')).toBeDefined()
  })

  it('should_say_the_corpus_is_clean_instead_of_showing_an_empty_table', async () => {
    renderPage({ total: 297, pendents: 0, documents: [] })

    expect(await screen.findByTestId('vigencia-todo-validado')).toBeDefined()
  })

  it('should_let_the_user_pick_which_chatbot_corpus_to_review', async () => {
    renderPage()

    const selector = await screen.findByTestId('vigencia-chatbot')
    expect(selector.textContent).toContain('Normativa UJI')
    expect(selector.textContent).toContain('Gerència')
  })
})

/**
 * REV.5 — el enlace del documento llevaba a Informes.
 *
 * `canonical_url` no siempre es una URL: para los documentos del corpus normativo cargados
 * desde carpeta es el nombre del fichero (`20260203_UJI_REC_Resolucio....md`). Como es
 * relativo, el navegador lo resolvía contra la ruta actual y abría una pestaña en
 * `/hub/20260203_....md`; ninguna ruta casaba, caía en el comodín `*` y `Aterrizaje` redirigía
 * al primer módulo concedido — que en `RUTA_DEL_MODULO` es `informes`.
 *
 * La pantalla no puede saber a qué URL externa apuntar cuando no hay ninguna, así que deja de
 * fingir que la hay.
 */
const CON_RUTA_LOCAL = {
  total: 10,
  pendents: 1,
  documents: [
    {
      id: 'doc-3',
      title: 'Resolució d’assimilació de càrrecs',
      language: 'va',
      canonical_url: '20260203_UJI_REC_Resolucio_assimilacio_carrecs.md',
      id_publicacio: null,
      estat_vigencia: 'vigent',
      vigencia_validada_el: null,
      data_revisio_prevista: null,
      revisat_per: null,
      motiu: 'sense_validar',
    },
  ],
}

describe('REV.5 — sólo se enlaza lo que de verdad es un enlace', () => {
  it('should_not_link_a_document_whose_canonical_url_is_a_file_name', async () => {
    renderPage(CON_RUTA_LOCAL)

    const titulo = await screen.findByText(/Resolució d’assimilació/)
    expect(titulo.closest('a')).toBeNull()
  })

  it('should_still_show_which_file_it_is', async () => {
    // Dejar de enlazar no puede significar esconder el dato: sin el nombre del fichero no hay
    // forma de ir a buscarlo.
    renderPage(CON_RUTA_LOCAL)

    expect(
      await screen.findByText(/20260203_UJI_REC_Resolucio_assimilacio_carrecs\.md/)
    ).toBeDefined()
  })

  it('should_keep_linking_a_real_external_url', async () => {
    renderPage()

    const titulo = await screen.findByText(/Reglament de la Sindicatura/)
    const enlace = titulo.closest('a')
    expect(enlace).not.toBeNull()
    expect(enlace?.getAttribute('href')).toBe('https://www.uji.es/sindicatura.pdf')
  })
})
