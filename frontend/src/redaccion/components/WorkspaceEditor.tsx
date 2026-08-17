import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { BlockStateAnnouncer } from './BlockStateAnnouncer'
import { StatusBadge } from '@/shared/components/StatusBadge'
import { mapBlockStatusToUserLabel } from '../utils/statusLabels'
import type { BlockStateOut } from '@/shared/api/generated/model'

/** El bloque es el del contrato, no una copia a mano.
 *
 * Había aquí una interfaz propia con `[key: string]: unknown`, y ese comodín hacía que
 * `BlockStateOut` —una `interface` generada, sin firma de índice— **no fuera asignable**:
 * `tsc` daba TS2322 en `WorkspacePage` en cuanto se regeneraba el cliente desde
 * `openapi.json`. Usar el tipo generado lo arregla y cumple la regla de contrato: el tipo
 * del componente no puede divergir del servidor porque sale de él. */
export interface WorkspaceData {
  blocks: BlockStateOut[]
  status?: string
}

interface Props {
  workspace: WorkspaceData
}

const ANNOUNCED_STATES = new Set(['extracted', 'ai_generated', 'approved', 'rejected'])

export function WorkspaceEditor({ workspace }: Props) {
  const { t: tR } = useTranslation('redaccion')
  const [announcement, setAnnouncement] = useState('')
  const prevStatusRef = useRef<Map<string, string>>(new Map())

  useEffect(() => {
    const prev = prevStatusRef.current
    let newAnnouncement = ''

    for (const block of workspace.blocks) {
      const blockId = block.block_id
      const currentStatus = block.status
      const prevStatus = prev.get(blockId)

      if (
        prevStatus !== undefined &&
        prevStatus !== currentStatus &&
        ANNOUNCED_STATES.has(currentStatus)
      ) {
        newAnnouncement = tR(`announcer.${currentStatus}`, { label: blockId })
      }
      prev.set(blockId, currentStatus)
    }

    if (newAnnouncement) {
      setAnnouncement(newAnnouncement)
    }
  }, [workspace, tR])

  return (
    <div data-testid="workspace-editor">
      <BlockStateAnnouncer announcement={announcement} />
      <div className="space-y-2">
        {workspace.blocks.map(block => {
          const { labelKey, tone } = mapBlockStatusToUserLabel(
            block.status,
            block.failure_kind ?? null,
          )
          const statusDescId = `block-status-desc-${block.block_id}`
          return (
            <div
              key={block.block_id}
              role="region"
              aria-label={tR('editor.block_region', { type: block.kind, id: block.block_id })}
              aria-describedby={statusDescId}
              data-testid={`block-${block.block_id}`}
              className="flex flex-col px-4 py-3 border rounded-md bg-card"
            >
              <span id={statusDescId} className="sr-only">
                {tR(labelKey)}
              </span>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium">{block.block_id}</span>
                  <span className="text-xs text-muted-foreground">{block.kind}</span>
                </div>
                <StatusBadge label={tR(labelKey)} tone={tone} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
