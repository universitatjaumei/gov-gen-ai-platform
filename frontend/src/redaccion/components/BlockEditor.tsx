import { useTranslation } from 'react-i18next'
import { useGetWorkspaceById } from '@/shared/api/generated/hub-redaccion/hub-redaccion'
import type { WorkspaceOut } from '@/shared/api/generated/model'
import { StatusBadge } from '@/shared/components/StatusBadge'
import { mapBlockStatusToUserLabel, mapFailureKindToKey } from '../utils/statusLabels'
import { BlockDebugPanel } from './BlockDebugPanel'

interface Props {
  workspaceId: string
}

export function BlockEditor({ workspaceId }: Props) {
  const { t } = useTranslation('common')
  const { t: tR } = useTranslation('redaccion')
  const { data: workspaceRaw, isLoading } = useGetWorkspaceById(workspaceId)
  const workspace = workspaceRaw as unknown as WorkspaceOut | undefined

  if (isLoading) return <div>{t('loading')}</div>
  if (!workspace) return null

  return (
    <div className="space-y-2">
      {workspace.blocks.map(block => {
        const { labelKey, tone } = mapBlockStatusToUserLabel(
          block.status,
          block.failure_kind,
        )
        const statusDescId = `block-status-desc-${block.block_id}`
        return (
          <div
            key={block.block_id}
            role="region"
            aria-label={tR('editor.block_region', { type: block.kind, id: block.block_id })}
            aria-describedby={statusDescId}
            data-testid={`block-${block.block_id}`}
            className="flex flex-col px-4 py-3 border rounded-md bg-card hover:bg-accent/20 transition-colors gap-2"
          >
            <span id={statusDescId} className="sr-only">{tR(labelKey)}</span>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium">{block.block_id}</span>
                <span className="text-xs text-muted-foreground">{block.kind}</span>
              </div>
              <StatusBadge
                label={tR(labelKey)}
                tone={tone}
                data-testid={`status-badge-${block.block_id}`}
              />
            </div>

            {block.status === 'failed' && block.failure_kind && (
              <p
                data-testid={`failure-friendly-message-${block.block_id}`}
                className="text-xs text-destructive"
              >
                {tR(mapFailureKindToKey(block.failure_kind))}
              </p>
            )}

            <BlockDebugPanel block={block} />
          </div>
        )
      })}
    </div>
  )
}
