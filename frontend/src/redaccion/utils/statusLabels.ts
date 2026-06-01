export type StatusTone = 'neutral' | 'info' | 'warning' | 'success' | 'error'

export interface UserStatusLabel {
  labelKey: string
  tone: StatusTone
}

export function mapBlockStatusToUserLabel(
  status: string,
  _failure_kind?: string | null,
): UserStatusLabel {
  switch (status) {
    case 'draft':
    case 'missing_input':
      return { labelKey: 'status.missing_data', tone: 'warning' }
    case 'extracted':
      return { labelKey: 'status.data_loaded', tone: 'info' }
    case 'ai_generated':
    case 'needs_review':
      return { labelKey: 'status.needs_review', tone: 'info' }
    case 'approved':
    case 'locked':
      return { labelKey: 'status.approved', tone: 'success' }
    case 'failed':
      return { labelKey: 'status.error_recoverable', tone: 'error' }
    case 'rejected':
      return { labelKey: 'status.rejected_retry', tone: 'warning' }
    default:
      return { labelKey: 'status.missing_data', tone: 'neutral' }
  }
}

export function mapWorkspaceStatusToUserLabel(status: string): UserStatusLabel {
  switch (status) {
    case 'draft':
    case 'ingesting':
      return { labelKey: 'workspace_status.preparing', tone: 'neutral' }
    case 'extracting':
      return { labelKey: 'workspace_status.extracting', tone: 'info' }
    case 'drafting':
      return { labelKey: 'workspace_status.drafting', tone: 'info' }
    case 'in_review':
      return { labelKey: 'workspace_status.in_review', tone: 'warning' }
    case 'assembled':
      return { labelKey: 'workspace_status.ready_to_export', tone: 'success' }
    case 'exported':
      return { labelKey: 'workspace_status.exported', tone: 'success' }
    default:
      return { labelKey: 'workspace_status.preparing', tone: 'neutral' }
  }
}

export function mapFailureKindToKey(failure_kind: string | null | undefined): string {
  switch (failure_kind) {
    case 'ai_failed': return 'failure.ai_failed'
    case 'extraction_failed': return 'failure.extraction_failed'
    case 'script_failed': return 'failure.script_failed'
    case 'validation_failed': return 'failure.validation_failed'
    default: return 'failure.unknown'
  }
}
