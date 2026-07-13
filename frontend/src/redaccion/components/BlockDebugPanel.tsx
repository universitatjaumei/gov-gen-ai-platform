import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/shared/auth'
import { WorkspaceAnonymizationPanel } from './WorkspaceAnonymizationPanel'

interface BlockDebugPanelProps {
  block: {
    block_id: string
    status: string
    failure_kind?: string | null
    last_error_message?: string | null
    retry_attempts?: number | null
    updated_at?: string | null
  }
  workspaceId?: string
  workspaceStatus?: string
}

type DebugTab = 'debug' | 'anonymization'

export function BlockDebugPanel({ block, workspaceId, workspaceStatus }: BlockDebugPanelProps) {
  const { t } = useTranslation('redaccion')
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<DebugTab>('debug')

  const isAdmin = user?.role === 'superadmin' || user?.role === 'admin'
  if (!isAdmin) return null

  const canShowAnon =
    workspaceId &&
    workspaceStatus &&
    !['drafting', 'in_review'].includes(workspaceStatus)

  return (
    <div data-testid="block-debug-panel" className="mt-2 border-t pt-2">
      <button
        type="button"
        data-testid="btn-toggle-debug"
        onClick={() => setOpen(prev => !prev)}
        className="text-xs text-muted-foreground hover:underline"
      >
        {t('debug.title')}
      </button>

      {open && (
        <div className="mt-1">
          {/* Tab bar */}
          <div className="flex gap-2 border-b mb-2">
            <button
              type="button"
              onClick={() => setActiveTab('debug')}
              className={`text-xs px-2 py-1 ${activeTab === 'debug' ? 'border-b-2 border-primary font-semibold' : 'text-muted-foreground'}`}
            >
              {t('debug.title')}
            </button>
            {canShowAnon && (
              <button
                type="button"
                data-testid="tab-anonymization"
                onClick={() => setActiveTab('anonymization')}
                className={`text-xs px-2 py-1 ${activeTab === 'anonymization' ? 'border-b-2 border-primary font-semibold' : 'text-muted-foreground'}`}
              >
                {t('anonymization.tab')}
              </button>
            )}
          </div>

          {activeTab === 'debug' && (
            <div className="space-y-0.5 text-xs font-mono bg-muted rounded p-2">
              <div>{t('debug.status')}: {block.status}</div>
              {block.failure_kind && (
                <div>{t('debug.failure_kind')}: {block.failure_kind}</div>
              )}
              {block.last_error_message && (
                <div data-testid="debug-last-error">
                  <span>{t('debug.last_error')}: </span>
                  <span>{block.last_error_message}</span>
                </div>
              )}
              <div>{t('debug.retry_attempts')}: {block.retry_attempts ?? 0}</div>
              {block.updated_at && (
                <div>{t('debug.updated_at')}: {block.updated_at}</div>
              )}
            </div>
          )}

          {activeTab === 'anonymization' && canShowAnon && (
            <WorkspaceAnonymizationPanel
              workspaceId={workspaceId}
              workspaceStatus={workspaceStatus}
            />
          )}
        </div>
      )}
    </div>
  )
}
