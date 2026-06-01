import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useProposeScript,
  useDescribeTestData,
  usePreviewPdfSpans,
  useAnonymizeTestData,
  useTestScriptProposal,
  useValidateTestResult,
  useSaveScriptToPrivateTemplate,
  useSubmitScriptForReview,
} from '@/shared/api/generated/redaccion-scripts/redaccion-scripts'
import type { ProposeResponse, TestProposalResponse, ValidateTestResultResponse } from '@/shared/api/generated/model'
import { ScriptCodePreview } from '../components/ScriptCodePreview'
import { TestDataAnonymizerForm } from '../components/TestDataAnonymizerForm'
import { SandboxTestResultViewer } from '../components/SandboxTestResultViewer'

type TargetOwnerKind = 'user' | 'platform'
type WizardStep = 1 | 2 | 3 | 4 | 5 | 6 | 7

const STEP_COUNT = 7

export function ScriptProposalWizardPage() {
  const { t } = useTranslation('scripts')

  const [step, setStep] = useState<WizardStep>(1)
  const [targetOwnerKind, setTargetOwnerKind] = useState<TargetOwnerKind>('user')
  const [promptNl, setPromptNl] = useState('')
  const [activeProposalId, setActiveProposalId] = useState<string | null>(null)

  const proposeHook = useProposeScript()
  const describeHook = useDescribeTestData()
  const previewHook = usePreviewPdfSpans()
  const anonymizeHook = useAnonymizeTestData()
  const testHook = useTestScriptProposal()
  const validateHook = useValidateTestResult()
  const saveHook = useSaveScriptToPrivateTemplate()
  const submitHook = useSubmitScriptForReview()

  const proposal = proposeHook.data as unknown as ProposeResponse | undefined
  const testResult = testHook.data as unknown as TestProposalResponse | undefined
  const validated = validateHook.data as unknown as ValidateTestResultResponse | undefined

  const auditPassed = proposal?.audit_result?.approved === true
  const canSave = !!validated

  // Auto-advance from step 1 → 2 when proposal arrives
  useEffect(() => {
    if (proposeHook.isSuccess && proposal) {
      setActiveProposalId(proposal.proposal_id)
      setStep(prev => (prev === 1 ? 2 : prev))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proposeHook.isSuccess])

  // Auto-advance to step 7 (save/submit) when test result arrives
  useEffect(() => {
    if (testHook.isSuccess && testResult && activeProposalId) {
      setStep(7)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [testHook.isSuccess, activeProposalId])

  function handlePropose() {
    if (!promptNl) return
    proposeHook.mutate({ data: { prompt_nl: promptNl, target_owner_kind: targetOwnerKind } })
  }

  function handleRegenerate() {
    proposeHook.reset()
    setActiveProposalId(null)
    setStep(1)
  }

  function handleTest() {
    if (!activeProposalId) return
    testHook.mutate({
      proposalId: activeProposalId,
      data: { test_data_ref: { bucket: '', key: '' } },
    })
  }

  function handleValidate() {
    if (!activeProposalId) return
    validateHook.mutate({ proposalId: activeProposalId })
  }

  function handleSave() {
    if (!activeProposalId || !canSave) return
    saveHook.mutate({ proposalId: activeProposalId }, {})
  }

  function handleSubmitForReview() {
    if (!activeProposalId || !canSave) return
    submitHook.mutate({ proposalId: activeProposalId }, {})
  }

  return (
    <div className="space-y-6 p-4 max-w-2xl">
      {/* Stepper — always in DOM */}
      <div className="flex items-center gap-1">
        {Array.from({ length: STEP_COUNT }, (_, i) => {
          const n = (i + 1) as WizardStep
          return (
            <div
              key={n}
              data-testid={`wizard-step-${n}`}
              className={`flex-1 h-1.5 rounded-full transition-colors ${
                n < step ? 'bg-primary' : n === step ? 'bg-primary/60' : 'bg-muted'
              }`}
            />
          )
        })}
      </div>

      {/* Persistent target selector */}
      <div className="flex items-center gap-3">
        <label htmlFor="target-owner-kind" className="text-sm font-medium shrink-0">
          {t('target.label')}
        </label>
        <select
          id="target-owner-kind"
          data-testid="select-target-owner-kind"
          value={targetOwnerKind}
          onChange={e => setTargetOwnerKind(e.target.value as TargetOwnerKind)}
          className="text-sm border rounded px-2 py-1"
        >
          <option value="user">{t('target.user')}</option>
          <option value="platform">{t('target.platform')}</option>
        </select>
      </div>

      {/* Step 1: Describe */}
      {step === 1 && (
        <div className="space-y-3">
          <textarea
            data-testid="input-prompt-nl"
            value={promptNl}
            onChange={e => setPromptNl(e.target.value)}
            rows={4}
            placeholder="Describe what the script should extract…"
            className="w-full border rounded p-2 text-sm resize-none"
          />
          <button
            type="button"
            data-testid="btn-propose"
            disabled={proposeHook.isPending || !promptNl}
            onClick={handlePropose}
            className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded disabled:opacity-50"
          >
            {proposeHook.isPending ? t('btn.propose') + '…' : t('btn.propose')}
          </button>
        </div>
      )}

      {/* Step 2: Code review */}
      {step === 2 && proposal && (
        <div className="space-y-4">
          <ScriptCodePreview code={proposal.code} auditResult={proposal.audit_result} />
          <div className="flex gap-2">
            <button
              type="button"
              data-testid="btn-regenerate"
              onClick={handleRegenerate}
              className="px-3 py-1.5 text-sm border rounded hover:bg-accent/30"
            >
              {t('btn.regenerate')}
            </button>
            <button
              type="button"
              data-testid="btn-next-step-2"
              aria-disabled={!auditPassed}
              disabled={!auditPassed}
              onClick={() => auditPassed && setStep(3)}
              className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded disabled:opacity-50"
            >
              {t('btn.next')}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Upload test data */}
      {step === 3 && (
        <div className="space-y-3">
          <input
            type="file"
            data-testid="input-test-data-file"
            accept=".csv,.xlsx,.json"
            onChange={() => {
              if (!activeProposalId) return
              describeHook.mutate({
                proposalId: activeProposalId,
                data: { file: new Blob() },
              })
            }}
            className="text-sm"
          />
          <button
            type="button"
            data-testid="btn-next-step-3"
            onClick={() => setStep(4)}
            className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded"
          >
            {t('btn.next')}
          </button>
        </div>
      )}

      {/* Step 4: Anonymize */}
      {step === 4 && (
        <div className="space-y-4">
          <TestDataAnonymizerForm columns={[]} onChange={() => {}} />
          <div className="flex gap-2">
            <button
              type="button"
              data-testid="btn-skip-anonymization"
              aria-disabled={targetOwnerKind === 'platform'}
              disabled={targetOwnerKind === 'platform'}
              onClick={() => targetOwnerKind !== 'platform' && setStep(5)}
              className="px-3 py-1.5 text-sm border rounded disabled:opacity-50"
            >
              {t('btn.skip_anonymization')}
            </button>
            <button
              type="button"
              data-testid="btn-next-step-4"
              onClick={() => {
                if (activeProposalId) {
                  anonymizeHook.mutate({
                    proposalId: activeProposalId,
                    data: { file_ref: { bucket: '', key: '' }, kind: 'csv' },
                  })
                }
                setStep(5)
              }}
              className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded"
            >
              {t('btn.next')}
            </button>
          </div>
        </div>
      )}

      {/* Step 5: PDF preview (optional) */}
      {step === 5 && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {t('wizard.step5')}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              data-testid="btn-preview-pdf"
              onClick={() => {
                if (activeProposalId) {
                  previewHook.mutate({
                    proposalId: activeProposalId,
                    data: { file: new Blob() },
                  })
                }
              }}
              className="px-3 py-1.5 text-sm border rounded"
            >
              {t('wizard.step5')}
            </button>
            <button
              type="button"
              data-testid="btn-next-step-5"
              onClick={() => setStep(6)}
              className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded"
            >
              {t('btn.next')}
            </button>
          </div>
        </div>
      )}

      {/* Step 6: Run test */}
      {step === 6 && (
        <div className="space-y-3">
          <button
            type="button"
            data-testid="btn-run-test"
            disabled={testHook.isPending || !activeProposalId}
            onClick={handleTest}
            className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded disabled:opacity-50"
          >
            {testHook.isPending ? t('btn.test') + '…' : t('btn.test')}
          </button>
        </div>
      )}

      {/* Step 7: Validate + save/submit */}
      {step === 7 && (
        <div className="space-y-4">
          {testResult && <SandboxTestResultViewer result={testResult} />}

          <button
            type="button"
            data-testid="btn-validate"
            disabled={validateHook.isPending || !testResult || !!validated}
            onClick={handleValidate}
            className="px-3 py-1.5 text-sm border rounded disabled:opacity-50"
          >
            {t('btn.validate')}
          </button>

          {targetOwnerKind === 'user' && (
            <button
              type="button"
              data-testid="btn-save"
              aria-disabled={!canSave}
              disabled={!canSave || saveHook.isPending}
              onClick={handleSave}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded disabled:opacity-50"
            >
              {t('btn.save')}
            </button>
          )}

          {targetOwnerKind === 'platform' && (
            <button
              type="button"
              data-testid="btn-submit-for-review"
              aria-disabled={!canSave}
              disabled={!canSave || submitHook.isPending}
              onClick={handleSubmitForReview}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded disabled:opacity-50"
            >
              {t('btn.submit_for_review')}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
