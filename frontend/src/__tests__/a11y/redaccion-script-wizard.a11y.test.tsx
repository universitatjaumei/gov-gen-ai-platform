import { describe, it, beforeAll, vi } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { ScriptProposalWizardPage } from '@/redaccion/pages/ScriptProposalWizardPage'
import { expectNoA11yViolations } from '@/test/a11y'

vi.mock('@/shared/api/generated/redaccion-scripts/redaccion-scripts', () => ({
  useProposeScript: vi.fn(() => ({ mutate: vi.fn(), data: undefined, isPending: false, isSuccess: false })),
  useDescribeTestData: vi.fn(() => ({ mutate: vi.fn(), data: undefined, isPending: false })),
  usePreviewPdfSpans: vi.fn(() => ({ mutate: vi.fn(), data: undefined, isPending: false })),
  useAnonymizeTestData: vi.fn(() => ({ mutate: vi.fn(), data: undefined, isPending: false })),
  useTestScriptProposal: vi.fn(() => ({ mutate: vi.fn(), data: undefined, isPending: false, isSuccess: false })),
  useValidateTestResult: vi.fn(() => ({ mutate: vi.fn(), data: undefined, isPending: false })),
  useSaveScriptToPrivateTemplate: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useSubmitScriptForReview: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

const TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  btoa(JSON.stringify({ sub: '1', email: 'user@test.com', role: 'user', exp: 9999999999 }))
    .replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_') +
  '.signature'

beforeAll(async () => {
  await i18n.changeLanguage('es')
  localStorage.setItem('access_token', TOKEN)
})

describe('ScriptProposalWizardPage — WCAG 2.2 AA baseline', () => {
  it('should_have_no_critical_a11y_violations_on_step_1', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <ScriptProposalWizardPage />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await expectNoA11yViolations(container)
  })
})
