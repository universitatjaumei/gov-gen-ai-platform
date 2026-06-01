import { useTranslation } from 'react-i18next'
import {
  useGetWorkspaceById,
  usePatchWorkspaceBlock,
} from '@/shared/api/generated/hub-redaccion/hub-redaccion'
import type { WorkspaceOut } from '@/shared/api/generated/model'
import { StatusBadge } from '@/shared/components/StatusBadge'
import { mapBlockStatusToUserLabel } from '../utils/statusLabels'

interface Props {
  workspaceId: string
}

export function AIBlockReviewPanel({ workspaceId }: Props) {
  const { t } = useTranslation('common')
  const { t: tR } = useTranslation('redaccion')
  const { data: workspaceRaw, isLoading } = useGetWorkspaceById(workspaceId)
  const workspace = workspaceRaw as unknown as WorkspaceOut | undefined
  const { mutate: patchBlock, isPending } = usePatchWorkspaceBlock()

  if (isLoading) return <div>{t('loading')}</div>
  if (!workspace) return null

  const pendingBlocks = workspace.blocks.filter(b => b.status === 'needs_review')
  const allApproved = pendingBlocks.length === 0

  function handleAction(blockId: string, action: 'approve' | 'reject' | 'regenerate') {
    patchBlock({ workspaceId, blockId, data: { action } })
  }

  return (
    <div className="space-y-3 p-4">
      {!allApproved && (
        <p
          data-testid="pending-review-count"
          className="text-sm text-muted-foreground"
        >
          {pendingBlocks.length} bloque{pendingBlocks.length !== 1 ? 's' : ''} pendiente{pendingBlocks.length !== 1 ? 's' : ''} de revisión
        </p>
      )}

      {allApproved && (
        <p
          data-testid="ready-for-assembly"
          className="text-sm text-green-700 font-medium"
        >
          Todos los bloques aprobados — listo para ensamblar
        </p>
      )}

      {pendingBlocks.map(block => (
        <div
          key={block.block_id}
          data-testid={`review-block-${block.block_id}`}
          className="border rounded-md p-3 space-y-2 bg-card"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{block.block_id}</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{block.kind}</span>
              <StatusBadge
                label={tR(mapBlockStatusToUserLabel(block.status).labelKey)}
                tone={mapBlockStatusToUserLabel(block.status).tone}
              />
            </div>
          </div>

          {typeof block.content?.text === 'string' && (
            <p className="text-sm text-muted-foreground line-clamp-3">
              {block.content.text as string}
            </p>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              data-testid={`btn-approve-${block.block_id}`}
              disabled={isPending}
              onClick={() => handleAction(block.block_id, 'approve')}
              className="px-2 py-1 text-xs bg-green-600 text-white rounded disabled:opacity-50"
            >
              Aprobar
            </button>
            <button
              type="button"
              data-testid={`btn-reject-${block.block_id}`}
              disabled={isPending}
              onClick={() => handleAction(block.block_id, 'reject')}
              className="px-2 py-1 text-xs bg-destructive text-destructive-foreground rounded disabled:opacity-50"
            >
              Rechazar
            </button>
            <button
              type="button"
              data-testid={`btn-regenerate-${block.block_id}`}
              disabled={isPending}
              onClick={() => handleAction(block.block_id, 'regenerate')}
              className="px-2 py-1 text-xs border rounded disabled:opacity-50"
            >
              Regenerar
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
