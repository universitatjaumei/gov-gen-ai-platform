import { Navigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  useListPendingScripts,
  useAdminRetestScript,
  useApproveScriptProposal,
  useRejectScriptProposal,
} from '@/shared/api/generated/redaccion-scripts/redaccion-scripts'
import type {
  PendingProposalOut,
  AdminRetestResponse,
} from '@/shared/api/generated/model'
import { useAuth } from '@/shared/auth'

interface ProposalCardProps {
  proposal: PendingProposalOut
}

function ProposalCard({ proposal }: ProposalCardProps) {
  const { t } = useTranslation('scripts')
  const retestHook = useAdminRetestScript()
  const approveHook = useApproveScriptProposal()
  const rejectHook = useRejectScriptProposal()

  const retestResult = retestHook.data as unknown as AdminRetestResponse | undefined
  const canApprove = !!retestResult

  function handleRetest() {
    retestHook.mutate({ proposalId: proposal.proposal_id })
  }

  function handleApprove() {
    if (!canApprove) return
    approveHook.mutate({
      proposalId: proposal.proposal_id,
      data: { target_global_template_id: '' },
    })
  }

  function handleReject() {
    rejectHook.mutate({
      proposalId: proposal.proposal_id,
      data: { review_note: '' },
    })
  }

  return (
    <div className="border rounded p-4 space-y-3 bg-card">
      <div className="space-y-1">
        <p className="text-xs text-muted-foreground">
          {t('admin.proposer')}: {proposal.proposer_user_id}
        </p>
        <p className="text-sm font-medium">{proposal.prompt_nl}</p>
        <pre className="text-xs bg-muted rounded p-2 overflow-auto max-h-32">
          {proposal.code_preview}
        </pre>
      </div>

      {/* Retest result */}
      {retestResult && (
        <div className="flex items-center gap-2 text-xs">
          <span
            data-testid="hash-match-indicator"
            className={retestResult.hash_matches ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}
          >
            {retestResult.hash_matches ? '✓' : '✗'}
          </span>
          <span className="text-muted-foreground">{t('test_result.hash')}: {retestResult.hash}</span>
        </div>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          data-testid="btn-retest"
          disabled={retestHook.isPending}
          onClick={handleRetest}
          className="px-3 py-1 text-xs border rounded hover:bg-accent/30 disabled:opacity-50"
        >
          {t('btn.retest')}
        </button>
        <button
          type="button"
          data-testid="btn-approve-proposal"
          aria-disabled={!canApprove}
          disabled={!canApprove || approveHook.isPending}
          onClick={handleApprove}
          className="px-3 py-1 text-xs bg-green-600 text-white rounded disabled:opacity-50"
        >
          {t('btn.approve')}
        </button>
        <button
          type="button"
          data-testid="btn-reject-proposal"
          disabled={rejectHook.isPending}
          onClick={handleReject}
          className="px-3 py-1 text-xs bg-red-600 text-white rounded disabled:opacity-50"
        >
          {t('btn.reject')}
        </button>
      </div>
    </div>
  )
}

export function AdminScriptReviewQueuePage() {
  const { t } = useTranslation('scripts')
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'partner'

  const listHook = useListPendingScripts()
  const proposals = listHook.data as unknown as PendingProposalOut[] | undefined

  if (!isAdmin) {
    return <Navigate to="/hub" replace />
  }

  return (
    <div data-testid="review-queue-page" className="space-y-4 p-4">
      <h1 className="text-lg font-semibold">{t('admin.queue_title')}</h1>

      {listHook.isPending && (
        <p className="text-sm text-muted-foreground">{t('btn.retest')}…</p>
      )}

      {!listHook.isPending && (!proposals || proposals.length === 0) && (
        <p className="text-sm text-muted-foreground">{t('admin.no_proposals')}</p>
      )}

      {proposals?.map(proposal => (
        <ProposalCard key={proposal.proposal_id} proposal={proposal} />
      ))}
    </div>
  )
}
