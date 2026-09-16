import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { ContentGapsPanel } from '../ContentGapsPanel'

/** RAG.14 — la cola de huecos existe y se lee. Sin esta pantalla el detector escribiría
 *  hallazgos que no vería nadie. */

const { mockAnalyze, mockData } = vi.hoisted(() => ({
  mockAnalyze: vi.fn(),
  mockData: { chatbots: [] as object[], gaps: [] as object[] },
}))

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useOpcionesDeGrafoApiV1HubChatbotsOpcionesDeGrafoGet: () => ({ data: { perfiles: [{ nombre: 'PUBLIC_KB_RICH', configurable: true }], modos: [{ nombre: 'RAG' }, { nombre: 'MD_LONG_CONTEXT' }, { nombre: 'MD_AGENT_SELECTOR' }], estrategias: { retrieval: [], merge: [], template: [], language: [] }, ejes: ['retrieval', 'merge', 'template', 'language'] } }),
  useListChatbotsApiV1HubChatbotsGet: vi.fn(() => ({ data: mockData.chatbots })),
}))

vi.mock('@/shared/api/generated/hub-content-quality/hub-content-quality', () => ({
  useListContentGaps: vi.fn(() => ({ data: mockData.gaps })),
  useAnalyzeContentGaps: vi.fn(() => ({ mutate: mockAnalyze, isPending: false })),
  getListContentGapsQueryKey: vi.fn(() => ['gaps']),
}))

const CHATBOT_ID = '00000000-0000-0000-0000-000000000100'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

afterEach(() => {
  vi.clearAllMocks()
  mockData.chatbots = []
  mockData.gaps = []
})

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <ContentGapsPanel />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function elegirChatbot() {
  fireEvent.change(screen.getByLabelText('Chatbot'), { target: { value: CHATBOT_ID } })
}

describe('ContentGapsPanel', () => {
  it('muestra los huecos con sus consultas y términos', async () => {
    mockData.chatbots = [{ id: CHATBOT_ID, name: 'Assistent normatiu' }]
    mockData.gaps = [
      {
        id: 'g1',
        severity: 'warning',
        status: 'new',
        count: 9,
        queries: ['dieta a l estranger', 'dieta internacional'],
        top_terms: ['dieta', 'estranger'],
        first_seen: '2026-07-10T00:00:00+00:00',
        last_seen: '2026-07-30T00:00:00+00:00',
      },
    ]

    renderPanel()
    elegirChatbot()

    await waitFor(() => expect(screen.getByText('9')).toBeInTheDocument())
    expect(screen.getByText('dieta a l estranger')).toBeInTheDocument()
    expect(screen.getByText(/dieta, estranger/)).toBeInTheDocument()
    expect(screen.getByText('warning')).toBeInTheDocument()
  })

  it('dispara el analisis para el chatbot elegido', async () => {
    mockData.chatbots = [{ id: CHATBOT_ID, name: 'Assistent normatiu' }]

    renderPanel()
    elegirChatbot()

    await waitFor(() => expect(screen.getByTestId('analyze-gaps')).toBeInTheDocument())
    fireEvent.click(screen.getByTestId('analyze-gaps'))

    expect(mockAnalyze).toHaveBeenCalledWith({ params: { chatbot_id: CHATBOT_ID } })
  })

  it('dice que no hay huecos en vez de dejar la lista vacia sin explicacion', async () => {
    mockData.chatbots = [{ id: CHATBOT_ID, name: 'Assistent normatiu' }]

    renderPanel()
    elegirChatbot()

    await waitFor(() =>
      expect(screen.getByText(/No hay huecos detectados/)).toBeInTheDocument()
    )
  })

  it('no deja ninguna cadena sin traducir', async () => {
    renderPanel()
    await waitFor(() => {
      expect(screen.queryByText(/^gaps_/)).not.toBeInTheDocument()
    })
  })
})
