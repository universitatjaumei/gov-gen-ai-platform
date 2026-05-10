// CF.4.1 (RED) — Tests del formulario Chatbot Create/Edit
//
// Describen el comportamiento DESEADO:
// - el formulario usa hooks generados por Orval (no fetch manual)
// - los errores 422 del backend se mapean a campos del formulario
//
// Estado inicial: RED — los tests (a)(b)(c)(e) FALLAN porque ChatbotsPage usa
// fetch manual desde @/shared/api/chatbots.ts, no los hooks generados.
// Pasarán tras el refactor en CF.4.2 (GREEN).

import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
// (f) Type-level contract: si ChatbotCreate cambia en openapi.json, tsc --noEmit fallará aquí
import type { ChatbotCreate } from '@/shared/api/generated/model'
import { ChatbotsPage } from '@/admin/pages/ChatbotsPage'

// vi.hoisted garantiza que los mocks se crean antes del hoisting de vi.mock()
const { mockCreateMutate, mockUpdateMutate, capturedCreateOptions, mockChatbotsList } = vi.hoisted(() => ({
  mockCreateMutate: vi.fn(),
  mockUpdateMutate: vi.fn(),
  capturedCreateOptions: { onError: undefined as ((e: unknown) => void) | undefined },
  mockChatbotsList: { value: [] as object[] },
}))

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useListChatbotsApiV1HubChatbotsGet: vi.fn(() => ({ data: mockChatbotsList.value, isLoading: false })),
  useCreateChatbotApiV1HubChatbotsPost: vi.fn((opts?: { mutation?: { onSuccess?: () => void; onError?: (e: unknown) => void } }) => {
    // Capture the latest onError on every render so test (e) can trigger it manually
    capturedCreateOptions.onError = opts?.mutation?.onError
    return {
      mutate: mockCreateMutate,
      isPending: false,
      reset: vi.fn(),
    }
  }),
  useUpdateChatbotApiV1HubChatbotsChatbotIdPatch: vi.fn(() => ({
    mutate: mockUpdateMutate,
    isPending: false,
    reset: vi.fn(),
  })),
  useDeleteChatbotApiV1HubChatbotsChatbotIdDelete: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    reset: vi.fn(),
  })),
  useListChildrenApiV1HubChatbotsChatbotIdChildrenGet: vi.fn(() => ({ data: undefined, isLoading: false })),
  useGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGet: vi.fn(() => ({ data: undefined })),
  useAssignChildApiV1HubChatbotsChatbotIdChildrenPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRegenerateChunksApiV1HubChatbotsChatbotIdRegenerateChunksPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  getListChatbotsApiV1HubChatbotsGetQueryKey: vi.fn(() => ['/api/v1/hub/chatbots']),
  getListChildrenApiV1HubChatbotsChatbotIdChildrenGetQueryKey: vi.fn((id: string) => [`/api/v1/hub/chatbots/${id}/children`]),
  getGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGetQueryKey: vi.fn((id: string) => [`/api/v1/hub/chatbots/${id}/corpus-stats`]),
}))

// (f) Verificación de contrato en tiempo de compilación.
// Si cambia la forma de ChatbotCreate (renombran 'name', añaden campo requerido, etc.),
// tsc --noEmit fallará en esta línea antes de que se ejecute ningún test.
const _contractCheck: ChatbotCreate = {
  name: 'Test Bot',
  client_id: '00000000-0000-0000-0000-000000000010',
  llm_config_id: '00000000-0000-0000-0000-000000000001',
  system_prompt: 'You are a helpful assistant.',
}

const TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_') +
  '.signature'

const DEMO_CHATBOT: ChatbotCreate & { id: string; is_active: boolean; created_at: string; updated_at: string; sources: string[]; retrieval_top_k: number; use_prompt_caching: boolean; cache_ttl: number; kind: string; parent_chatbot_id: null; public_graph_profile: string; language_mode: string; quality_threshold: number; min_retrieval_results: number; min_retrieval_score: number; reranker_enabled: boolean; answer_template: string } = {
  id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  name: 'Bot Demo',
  client_id: '00000000-0000-0000-0000-000000000010',
  llm_config_id: '00000000-0000-0000-0000-000000000001',
  system_prompt: 'Eres útil.',
  sources: [],
  is_active: true,
  retrieval_mode: 'RAG',
  retrieval_top_k: 8,
  use_prompt_caching: false,
  cache_ttl: 3600,
  kind: 'atomic',
  parent_chatbot_id: null,
  public_graph_profile: 'PUBLIC_KB_RICH',
  language_mode: 'prefer',
  quality_threshold: 0.6,
  min_retrieval_results: 2,
  min_retrieval_score: 0.25,
  reranker_enabled: true,
  answer_template: 'generic',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
})

afterEach(() => {
  vi.clearAllMocks()
  vi.unstubAllGlobals()
  capturedCreateOptions.onError = undefined
  mockChatbotsList.value = []
})

type FetchResponse = { ok: boolean; status?: number; json: () => Promise<unknown> }

function buildFetchStub(chatbots: object[] = [], postStatus = 200): (input: RequestInfo | URL, init?: RequestInit) => Promise<FetchResponse> {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<FetchResponse> => {
    const url = String(input)
    const method = init?.method ?? 'GET'

    if (url.includes('/corpus-stats')) {
      return {
        ok: true,
        json: async () => ({
          total_documents: 0,
          total_tokens: 0,
          by_language: {},
          recommended_mode: 'RAG',
          recommendation_reason: '',
        }),
      }
    }

    if (method === 'GET' && url.includes('/api/v1/hub/chatbots')) {
      return { ok: true, json: async () => chatbots }
    }

    if (method === 'POST' || method === 'PATCH') {
      if (postStatus >= 400) {
        return {
          ok: false,
          status: postStatus,
          json: async () => ({
            detail: [
              { loc: ['body', 'name'], msg: 'Name already in use', type: 'value_error' },
            ],
          }),
        }
      }
      return { ok: true, json: async () => DEMO_CHATBOT }
    }

    return { ok: true, json: async () => ({}) }
  })
}

function renderPage(chatbots: object[] = [], postStatus = 200) {
  vi.stubGlobal('fetch', buildFetchStub(chatbots, postStatus))
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>
          <ChatbotsPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

async function openCreateDialog() {
  renderPage([])
  await waitFor(() => screen.getByRole('button', { name: /nuevo chatbot/i }))
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /nuevo chatbot/i }))
  })
  await waitFor(() => screen.getByRole('dialog'))
}

async function openEditDialog() {
  mockChatbotsList.value = [DEMO_CHATBOT]
  renderPage([])
  await waitFor(() => screen.getByText('Bot Demo'))
  await act(async () => {
    fireEvent.click(screen.getByText('Bot Demo'))
  })
  await waitFor(() => screen.getByRole('dialog'))
}

describe('ChatbotForm — CF.4.1 (RED)', () => {

  // (a) + (b) — submit en modo creación llama a la mutation de Orval, no a fetch()
  //
  // FALLA en RED: ChatbotsPage usa useMutation({ mutationFn: createChatbot }) con fetch manual.
  // No llama a useCreateChatbotApiV1HubChatbotsPost del código generado.
  // PASARÁ en CF.4.2 cuando el componente use el hook de Orval.
  it('create_submit_calls_orval_create_mutation', async () => {
    await openCreateDialog()

    const textboxes = screen.getAllByRole('textbox')
    fireEvent.change(textboxes[0], { target: { value: 'Nuevo Bot' } })    // name input
    fireEvent.change(textboxes[1], { target: { value: 'Eres útil.' } })   // system_prompt

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    })

    // El contrato: el submit debe llamar al hook generado con { data: ChatbotCreate }.
    // La variante de Orval espera { data: ... } como argumento del mutate.
    expect(mockCreateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining<Partial<ChatbotCreate>>({ name: 'Nuevo Bot' }),
      })
    )
  })

  // (c) — submit en modo edición llama a la mutation de Orval para update
  //
  // FALLA en RED: ChatbotsPage usa useMutation({ mutationFn: updateChatbot }) con fetch manual.
  // No llama a useUpdateChatbotApiV1HubChatbotsChatbotIdPatch.
  // PASARÁ en CF.4.2.
  it('edit_submit_calls_orval_update_mutation', async () => {
    await openEditDialog()

    // El formulario ya tiene los valores del chatbot. Guardamos sin cambios.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    })

    // El contrato: el submit de edición debe llamar al hook generado con chatbotId y data.
    expect(mockUpdateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        chatbotId: DEMO_CHATBOT.id,
        data: expect.objectContaining({ name: 'Bot Demo' }),
      })
    )
  })

  // (d) — campo required "name" muestra error de validación si se envía vacío
  //
  // Puede PASAR ya con la implementación actual (react-hook-form + zodResolver ya instalados).
  // Se incluye para documentar el comportamiento esperado y como regresión.
  it('name_required_shows_validation_error', async () => {
    await openCreateDialog()

    // name ya está vacío por defecto. Enviamos sin rellenarlo.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    })

    // zodResolver con z.string().min(1) en Zod v4 genera "Too small: expected string to have >=1 characters"
    await waitFor(() => {
      expect(
        screen.getAllByText(/Too small/i)[0]
      ).toBeInTheDocument()
    })
  })

  // (e) — error 422 del backend se mapea al campo "name" del formulario
  //
  // El hook de Orval está mockeado, por lo que no hay llamada HTTP real.
  // El test captura el onError registrado por el componente al montar y lo
  // invoca manualmente con un error 422 simulado. Esto ejercita mapApiErrorsToFormErrors
  // de @/shared/utils/formErrors y verifica que el mensaje aparece en el campo.
  it('backend_422_maps_field_error_to_name_input', async () => {
    renderPage([])

    await waitFor(() => screen.getByRole('button', { name: /nuevo chatbot/i }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /nuevo chatbot/i }))
    })
    await waitFor(() => screen.getByRole('dialog'))

    const textboxes = screen.getAllByRole('textbox')
    fireEvent.change(textboxes[0], { target: { value: 'Bot Existente' } })
    fireEvent.change(textboxes[1], { target: { value: 'Descripción del bot.' } })

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    })

    // Simula la respuesta 422 del servidor llamando al onError capturado del hook.
    await act(async () => {
      capturedCreateOptions.onError?.({
        response: {
          data: {
            detail: [{ loc: ['body', 'name'], msg: 'Name already in use', type: 'value_error' }],
          },
        },
      })
    })

    await waitFor(() => {
      expect(screen.getByText('Name already in use')).toBeInTheDocument()
    })
  })
})
