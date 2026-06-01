import { describe, it, beforeAll, afterEach, vi } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { ChatbotsPage } from '@/admin/pages/ChatbotsPage'
import { expectNoA11yViolations } from '@/test/a11y'

vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useCreateChatbotApiV1HubChatbotsPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false, reset: vi.fn() })),
  useUpdateChatbotApiV1HubChatbotsChatbotIdPatch: vi.fn(() => ({ mutate: vi.fn(), isPending: false, reset: vi.fn() })),
  useDeleteChatbotApiV1HubChatbotsChatbotIdDelete: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useListChatbotsApiV1HubChatbotsGet: vi.fn(() => ({ data: [], isLoading: false })),
  useGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGet: vi.fn(() => ({ data: undefined })),
  useListChildrenApiV1HubChatbotsChatbotIdChildrenGet: vi.fn(() => ({ data: [] })),
  useRegenerateChunksApiV1HubChatbotsChatbotIdRegenerateChunksPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useAssignChildApiV1HubChatbotsChatbotIdChildrenPost: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  getListChatbotsApiV1HubChatbotsGetQueryKey: vi.fn(() => ['/api/v1/hub/chatbots']),
  getListChildrenApiV1HubChatbotsChatbotIdChildrenGetQueryKey: vi.fn(() => ['children']),
  getGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGetQueryKey: vi.fn(() => ['corpus-stats']),
}))

const TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'admin@test.com', role: 'admin', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ChatbotsPage — WCAG 2.2 AA baseline', () => {
  it('should_have_no_critical_a11y_violations', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }))
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <ChatbotsPage />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await expectNoA11yViolations(container)
  })
})
