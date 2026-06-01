import { describe, it, beforeAll, vi } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { LLMDraftPreviewPage } from '@/redaccion/pages/LLMDraftPreviewPage'
import { expectNoA11yViolations } from '@/test/a11y'

vi.mock('@/shared/api/generated/redaccion-llm-drafts/redaccion-llm-drafts', () => ({
  useProposeLlmDraft: vi.fn(() => ({ mutate: vi.fn(), data: undefined, isPending: false })),
  useValidateLlmDraft: vi.fn(() => ({ mutate: vi.fn(), data: undefined, isPending: false })),
  useApproveAsTemplate: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useApproveAsWorkspace: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
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

describe('LLMDraftPreviewPage — WCAG 2.2 AA baseline', () => {
  it('should_have_no_critical_a11y_violations_on_initial_state', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <LLMDraftPreviewPage />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await expectNoA11yViolations(container)
  })
})
