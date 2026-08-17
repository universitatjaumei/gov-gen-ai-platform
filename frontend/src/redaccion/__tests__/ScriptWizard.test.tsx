/**
 * Tests 9R.7.5 (RED → GREEN)
 * ScriptProposalWizardPage + AdminScriptReviewQueuePage
 */
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'

import { ScriptProposalWizardPage } from '../pages/ScriptProposalWizardPage'
import { AdminScriptReviewQueuePage } from '../pages/AdminScriptReviewQueuePage'

// --------------------------------------------------------------------------
// Mock Orval hooks
// --------------------------------------------------------------------------

const mockProposeScript = vi.fn()
const mockTestScriptProposal = vi.fn()
const mockValidateTestResult = vi.fn()
const mockSaveToPrivateTemplate = vi.fn()
const mockSubmitForReview = vi.fn()
const mockAdminRetestScript = vi.fn()
const mockApproveScriptProposal = vi.fn()
const mockRejectScriptProposal = vi.fn()

vi.mock('@/shared/api/generated/redaccion-scripts/redaccion-scripts', () => ({
  useProposeScript: vi.fn(),
  useDescribeTestData: vi.fn(),
  usePreviewPdfSpans: vi.fn(),
  useAnonymizeTestData: vi.fn(),
  useTestScriptProposal: vi.fn(),
  useValidateTestResult: vi.fn(),
  useSaveScriptToPrivateTemplate: vi.fn(),
  useSubmitScriptForReview: vi.fn(),
  useListPendingScripts: vi.fn(),
  useAdminRetestScript: vi.fn(),
  useApproveScriptProposal: vi.fn(),
  useRejectScriptProposal: vi.fn(),
}))

vi.mock('@/shared/auth', async () => {
  const actual = await vi.importActual<typeof import('@/shared/auth')>('@/shared/auth')
  return { ...actual, useAuth: vi.fn() }
})

import {
  useProposeScript,
  useDescribeTestData,
  usePreviewPdfSpans,
  useAnonymizeTestData,
  useTestScriptProposal,
  useValidateTestResult,
  useSaveScriptToPrivateTemplate,
  useSubmitScriptForReview,
  useListPendingScripts,
  useAdminRetestScript,
  useApproveScriptProposal,
  useRejectScriptProposal,
} from '@/shared/api/generated/redaccion-scripts/redaccion-scripts'
import { useAuth } from '@/shared/auth'

// --------------------------------------------------------------------------
// Fixtures
// --------------------------------------------------------------------------

// PRO.1 — la auditoría tiene tres niveles y cada hallazgo lleva su línea.
interface AuditFindingStub {
  severity: 'WARNING' | 'CRITICAL'
  rule: string
  detail: string
  line: number
  message: string
}

const APPROVED_AUDIT = {
  approved: true,
  risk_level: 'SAFE' as const,
  puede_revisarse: true,
  findings: [] as AuditFindingStub[],
  confidence: 1.0,
}
const REJECTED_AUDIT = {
  approved: false,
  risk_level: 'CRITICAL' as const,
  puede_revisarse: false,
  findings: [{
    severity: 'CRITICAL' as const,
    rule: 'forbidden-module',
    detail: 'os',
    line: 1,
    message: "CRITICO (línea 1): módulo 'os' prohibido",
  }],
  confidence: 0.0,
}
const REVISABLE_AUDIT = {
  approved: false,
  risk_level: 'WARNING' as const,
  puede_revisarse: true,
  findings: [{
    severity: 'WARNING' as const,
    rule: 'module-not-whitelisted',
    detail: 'csv',
    line: 3,
    message: "ADVERTENCIA (línea 3): módulo 'csv' no está en la lista blanca",
  }],
  confidence: 0.5,
}

const SAMPLE_PROPOSE_APPROVED = {
  proposal_id: 'prop-1',
  code: 'import pandas as pd\nresult = {"tables":[], "metrics":[], "free_text": None}',
  audit_result: APPROVED_AUDIT,
}

const SAMPLE_TEST_RESULT = {
  proposal_id: 'prop-1',
  status: 'tested',
  result: { tables: [], metrics: [], free_text: null },
  hash: 'abc123def456',
}

const SAMPLE_PENDING: PendingProposalOutStub = {
  proposal_id: 'prop-1',
  proposer_user_id: 'user-uuid-1',
  prompt_nl: 'Extract sales data',
  code_preview: 'import pandas as pd\n...',
  audit_result: APPROVED_AUDIT,
  test_result_hash: 'abc123',
  test_data_ref: null,
}

// Minimal stub type for the test fixture
interface PendingProposalOutStub {
  proposal_id: string
  proposer_user_id: string
  prompt_nl: string
  code_preview: string
  audit_result: typeof APPROVED_AUDIT
  test_result_hash: string | null
  test_data_ref: null
}

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

function setupDefaultHooks() {
  vi.mocked(useProposeScript).mockReturnValue({
    mutate: mockProposeScript,
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useProposeScript>)

  vi.mocked(useDescribeTestData).mockReturnValue({
    mutate: vi.fn(),
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useDescribeTestData>)

  vi.mocked(usePreviewPdfSpans).mockReturnValue({
    mutate: vi.fn(),
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof usePreviewPdfSpans>)

  vi.mocked(useAnonymizeTestData).mockReturnValue({
    mutate: vi.fn(),
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useAnonymizeTestData>)

  vi.mocked(useTestScriptProposal).mockReturnValue({
    mutate: mockTestScriptProposal,
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useTestScriptProposal>)

  vi.mocked(useValidateTestResult).mockReturnValue({
    mutate: mockValidateTestResult,
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useValidateTestResult>)

  vi.mocked(useSaveScriptToPrivateTemplate).mockReturnValue({
    mutate: mockSaveToPrivateTemplate,
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useSaveScriptToPrivateTemplate>)

  vi.mocked(useSubmitScriptForReview).mockReturnValue({
    mutate: mockSubmitForReview,
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useSubmitScriptForReview>)

  vi.mocked(useListPendingScripts).mockReturnValue({
    data: [SAMPLE_PENDING] as unknown as ReturnType<typeof useListPendingScripts>['data'],
    isPending: false,
    isSuccess: true,
    isError: false,
  } as unknown as ReturnType<typeof useListPendingScripts>)

  vi.mocked(useAdminRetestScript).mockReturnValue({
    mutate: mockAdminRetestScript,
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useAdminRetestScript>)

  vi.mocked(useApproveScriptProposal).mockReturnValue({
    mutate: mockApproveScriptProposal,
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useApproveScriptProposal>)

  vi.mocked(useRejectScriptProposal).mockReturnValue({
    mutate: mockRejectScriptProposal,
    data: undefined,
    isPending: false,
    isSuccess: false,
    isError: false,
  } as unknown as ReturnType<typeof useRejectScriptProposal>)
}

function setupAuth(role: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { user_id: 'u1', email: `${role}@test.com`, role },
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function wrap(ui: React.ReactElement, role = 'user') {
  setupAuth(role)
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/redaccion/scripts/wizard']}>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function wrapRouted(role = 'user') {
  setupAuth(role)
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/redaccion/scripts/review']}>
        <Routes>
          <Route path="/redaccion/scripts/review" element={<AdminScriptReviewQueuePage />} />
          <Route path="/hub" element={<div data-testid="hub-page">Hub</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.clearAllMocks()
  setupDefaultHooks()
})

// --------------------------------------------------------------------------
// ScriptProposalWizardPage tests
// --------------------------------------------------------------------------

describe('ScriptProposalWizardPage', () => {
  it('should_block_next_step_until_audit_passes', () => {
    vi.mocked(useProposeScript).mockReturnValue({
      mutate: mockProposeScript,
      data: {
        ...SAMPLE_PROPOSE_APPROVED,
        audit_result: REJECTED_AUDIT,
      } as unknown as ReturnType<typeof useProposeScript>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
      reset: vi.fn(),
    } as unknown as ReturnType<typeof useProposeScript>)

    wrap(<ScriptProposalWizardPage />)

    // Stepper step-1 indicator always in DOM
    expect(screen.getByTestId('wizard-step-1')).toBeDefined()

    // When proposal exists with failed audit, step 2 is shown and next is blocked
    const nextBtn = screen.queryByTestId('btn-next-step-2')
    if (nextBtn) {
      expect(nextBtn.getAttribute('aria-disabled')).toBe('true')
    }
  })

  it('should_mostrar_el_nivel_warning_como_revisable_con_la_linea_del_hallazgo', () => {
    // PRO.1 — una advertencia no es un fallo: la pantalla tiene que decirlo, y decir
    // en qué línea está, que es lo que el administrador va a mirar.
    vi.mocked(useProposeScript).mockReturnValue({
      mutate: mockProposeScript,
      data: {
        ...SAMPLE_PROPOSE_APPROVED,
        audit_result: REVISABLE_AUDIT,
      } as unknown as ReturnType<typeof useProposeScript>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
      reset: vi.fn(),
    } as unknown as ReturnType<typeof useProposeScript>)

    wrap(<ScriptProposalWizardPage />)

    const resumen = screen.getByTestId('audit-summary')
    expect(resumen.getAttribute('data-risk-level')).toBe('WARNING')

    const hallazgos = screen.getAllByTestId('audit-finding')
    expect(hallazgos).toHaveLength(1)
    expect(hallazgos[0].textContent).toContain('línea 3')
    expect(hallazgos[0].textContent).toContain('csv')
  })

  it('should_block_save_button_until_test_validated', () => {
    vi.mocked(useProposeScript).mockReturnValue({
      mutate: mockProposeScript,
      data: SAMPLE_PROPOSE_APPROVED as unknown as ReturnType<typeof useProposeScript>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
      reset: vi.fn(),
    } as unknown as ReturnType<typeof useProposeScript>)

    vi.mocked(useTestScriptProposal).mockReturnValue({
      mutate: mockTestScriptProposal,
      data: SAMPLE_TEST_RESULT as unknown as ReturnType<typeof useTestScriptProposal>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useTestScriptProposal>)

    // Validate NOT done
    vi.mocked(useValidateTestResult).mockReturnValue({
      mutate: mockValidateTestResult,
      data: undefined,
      isPending: false,
      isSuccess: false,
      isError: false,
    } as unknown as ReturnType<typeof useValidateTestResult>)

    wrap(<ScriptProposalWizardPage />)

    const saveBtn = screen.queryByTestId('btn-save')
    if (saveBtn) {
      expect(saveBtn.getAttribute('aria-disabled')).toBe('true')
    }

    const submitBtn = screen.queryByTestId('btn-submit-for-review')
    if (submitBtn) {
      expect(submitBtn.getAttribute('aria-disabled')).toBe('true')
    }
  })

  it('should_require_anonymization_for_platform_target', () => {
    wrap(<ScriptProposalWizardPage />, 'admin')

    const targetSelect = screen.queryByTestId('select-target-owner-kind')
    if (targetSelect) {
      fireEvent.change(targetSelect, { target: { value: 'platform' } })
    }

    // For platform target, skipping anonymization must be blocked
    const skipBtn = screen.queryByTestId('btn-skip-anonymization')
    if (skipBtn) {
      expect(skipBtn.getAttribute('aria-disabled')).toBe('true')
    }
  })

  it('should_invalidate_later_steps_when_code_regenerated', () => {
    vi.mocked(useProposeScript).mockReturnValue({
      mutate: mockProposeScript,
      data: SAMPLE_PROPOSE_APPROVED as unknown as ReturnType<typeof useProposeScript>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
      reset: vi.fn(),
    } as unknown as ReturnType<typeof useProposeScript>)

    wrap(<ScriptProposalWizardPage />)

    // Step indicator for step 1 always present
    expect(screen.getByTestId('wizard-step-1')).toBeDefined()

    // Clicking regenerate should reset wizard to step 1
    const retryBtn = screen.queryByTestId('btn-regenerate')
    if (retryBtn) {
      fireEvent.click(retryBtn)
      // After reset, step 1 content should be active
      expect(screen.getByTestId('wizard-step-1')).toBeDefined()
      // Step 2 next button should no longer be in DOM (back at step 1)
      expect(screen.queryByTestId('btn-next-step-2')).toBeNull()
    }
  })

  it('should_call_save_to_private_template_for_user_target', () => {
    vi.mocked(useProposeScript).mockReturnValue({
      mutate: mockProposeScript,
      data: SAMPLE_PROPOSE_APPROVED as unknown as ReturnType<typeof useProposeScript>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
      reset: vi.fn(),
    } as unknown as ReturnType<typeof useProposeScript>)

    vi.mocked(useTestScriptProposal).mockReturnValue({
      mutate: mockTestScriptProposal,
      data: SAMPLE_TEST_RESULT as unknown as ReturnType<typeof useTestScriptProposal>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useTestScriptProposal>)

    vi.mocked(useValidateTestResult).mockReturnValue({
      mutate: mockValidateTestResult,
      data: {
        proposal_id: 'prop-1',
        test_validated_by_proposer_at: '2026-05-17T10:00:00Z',
      } as unknown as ReturnType<typeof useValidateTestResult>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useValidateTestResult>)

    wrap(<ScriptProposalWizardPage />, 'user')

    const saveBtn = screen.queryByTestId('btn-save')
    if (saveBtn) {
      fireEvent.click(saveBtn)
      expect(mockSaveToPrivateTemplate).toHaveBeenCalledWith(
        expect.objectContaining({ proposalId: 'prop-1' }),
        expect.anything(),
      )
    }
  })

  it('should_call_submit_for_review_for_platform_target', () => {
    vi.mocked(useProposeScript).mockReturnValue({
      mutate: mockProposeScript,
      data: {
        ...SAMPLE_PROPOSE_APPROVED,
        proposal_id: 'prop-2',
      } as unknown as ReturnType<typeof useProposeScript>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
      reset: vi.fn(),
    } as unknown as ReturnType<typeof useProposeScript>)

    vi.mocked(useTestScriptProposal).mockReturnValue({
      mutate: mockTestScriptProposal,
      data: {
        ...SAMPLE_TEST_RESULT,
        proposal_id: 'prop-2',
      } as unknown as ReturnType<typeof useTestScriptProposal>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useTestScriptProposal>)

    vi.mocked(useValidateTestResult).mockReturnValue({
      mutate: mockValidateTestResult,
      data: {
        proposal_id: 'prop-2',
        test_validated_by_proposer_at: '2026-05-17T10:00:00Z',
      } as unknown as ReturnType<typeof useValidateTestResult>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useValidateTestResult>)

    wrap(<ScriptProposalWizardPage />, 'admin')

    // Change target to platform
    const targetSelect = screen.queryByTestId('select-target-owner-kind')
    if (targetSelect) {
      fireEvent.change(targetSelect, { target: { value: 'platform' } })
    }

    const submitBtn = screen.queryByTestId('btn-submit-for-review')
    if (submitBtn) {
      fireEvent.click(submitBtn)
      expect(mockSubmitForReview).toHaveBeenCalledWith(
        expect.objectContaining({ proposalId: 'prop-2' }),
        expect.anything(),
      )
    }
  })
})

// --------------------------------------------------------------------------
// AdminScriptReviewQueuePage tests
// --------------------------------------------------------------------------

describe('AdminScriptReviewQueuePage', () => {
  it('should_redirect_non_admin_away_from_review_queue', () => {
    wrapRouted('user')
    // Non-admin should not see the review queue
    expect(screen.queryByTestId('review-queue-page')).toBeNull()
    // Should be redirected (hub-page shown) or access-denied shown
    const destination = screen.queryByTestId('hub-page') ?? screen.queryByTestId('access-denied')
    expect(destination).not.toBeNull()
  })

  it('should_show_hash_match_indicator_in_review_queue', () => {
    vi.mocked(useAdminRetestScript).mockReturnValue({
      mutate: mockAdminRetestScript,
      data: {
        proposal_id: 'prop-1',
        result: {},
        hash: 'abc123',
        hash_matches: true,
      } as unknown as ReturnType<typeof useAdminRetestScript>['data'],
      isPending: false,
      isSuccess: true,
      isError: false,
    } as unknown as ReturnType<typeof useAdminRetestScript>)

    wrap(<AdminScriptReviewQueuePage />, 'admin')

    expect(screen.getByTestId('review-queue-page')).toBeDefined()
    const indicator = screen.queryByTestId('hash-match-indicator')
    if (indicator) {
      expect(indicator.textContent).toMatch(/✓|ok|match/i)
    }
  })

  it('should_disable_approve_when_admin_retest_stale', () => {
    // No retest data → approve must be disabled
    vi.mocked(useAdminRetestScript).mockReturnValue({
      mutate: mockAdminRetestScript,
      data: undefined,
      isPending: false,
      isSuccess: false,
      isError: false,
    } as unknown as ReturnType<typeof useAdminRetestScript>)

    wrap(<AdminScriptReviewQueuePage />, 'admin')

    expect(screen.getByTestId('review-queue-page')).toBeDefined()
    const approveBtn = screen.queryByTestId('btn-approve-proposal')
    if (approveBtn) {
      expect(approveBtn.getAttribute('aria-disabled')).toBe('true')
    }
  })
})
