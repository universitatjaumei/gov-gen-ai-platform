import { useTranslation } from 'react-i18next'
import { useGetWorkspaceById } from '@/shared/api/generated/hub-redaccion/hub-redaccion'
import type { WorkspaceOut } from '@/shared/api/generated/model'

const STATUS_BADGE: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600',
  extracted: 'bg-blue-100 text-blue-700',
  ai_generated: 'bg-purple-100 text-purple-700',
  needs_review: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  failed: 'bg-destructive/10 text-destructive',
  locked: 'bg-gray-100 text-gray-500',
}

interface Props {
  workspaceId: string
}

export function BlockEditor({ workspaceId }: Props) {
  const { t } = useTranslation('common')
  const { data: workspaceRaw, isLoading } = useGetWorkspaceById(workspaceId)
  const workspace = workspaceRaw as unknown as WorkspaceOut | undefined

  if (isLoading) return <div>{t('loading')}</div>
  if (!workspace) return null

  return (
    <div className="space-y-2">
      {workspace.blocks.map(block => (
        <div
          key={block.block_id}
          data-testid={`block-${block.block_id}`}
          className="flex items-center justify-between px-4 py-3 border rounded-md bg-card hover:bg-accent/20 transition-colors"
        >
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">{block.block_id}</span>
            <span className="text-xs text-muted-foreground">{block.kind}</span>
          </div>
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${STATUS_BADGE[block.status] ?? 'bg-gray-100 text-gray-600'}`}
          >
            {block.status}
          </span>
        </div>
      ))}
    </div>
  )
}
