import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import {
  useGetWorkspaceById,
  usePatchWorkspaceBlock,
  getGetWorkspaceByIdQueryKey,
} from '@/shared/api/generated/hub-redaccion/hub-redaccion'
import { useEditBlock } from '@/shared/api/generated/redaccion-workspaces/redaccion-workspaces'
import type { WorkspaceOut } from '@/shared/api/generated/model'
import { StatusBadge } from '@/shared/components/StatusBadge'
import { mapBlockStatusToUserLabel } from '../utils/statusLabels'

interface Props {
  workspaceId: string
}

/**
 * Revisión de los apartados escritos por la IA (SEG.4).
 *
 * Antes sólo se podía aprobar, rechazar o regenerar. Editar **ya existía en el backend** —el
 * endpoint sobreescribe el contenido y guarda el original en un evento de auditoría con su
 * actor— y el hook generado no lo llamaba ninguna pantalla, así que la supervisión se reducía a
 * un sí o un no sobre un texto que además se mostraba recortado a tres líneas.
 *
 * Tres cosas que esta pantalla enseña y antes no: el texto completo, **de qué tabla se apoya la
 * valoración** (lo que SEG.1 dejó en el bloque) y quién editó, si alguien editó.
 */
export function AIBlockReviewPanel({ workspaceId }: Props) {
  const { t } = useTranslation('common')
  const { t: tR } = useTranslation('redaccion')
  const qc = useQueryClient()

  const [editando, setEditando] = useState<string | null>(null)
  const [borrador, setBorrador] = useState('')

  const { data: workspaceRaw, isLoading } = useGetWorkspaceById(workspaceId)
  const workspace = workspaceRaw as unknown as WorkspaceOut | undefined
  const { mutate: patchBlock, isPending } = usePatchWorkspaceBlock()
  const { mutate: editarBloque, isPending: guardando } = useEditBlock()

  if (isLoading) return <div>{t('loading')}</div>
  if (!workspace) return null

  const pendientes = workspace.blocks.filter((b) => b.status === 'needs_review')
  const todoAprobado = pendientes.length === 0
  const refrescar = {
    onSuccess: () => qc.invalidateQueries({ queryKey: getGetWorkspaceByIdQueryKey(workspaceId) }),
  }

  function actuar(blockId: string, action: 'approve' | 'reject' | 'regenerate') {
    patchBlock({ workspaceId, blockId, data: { action } }, refrescar)
  }

  function empezarAEditar(blockId: string, texto: string) {
    setEditando(blockId)
    setBorrador(texto)
  }

  function guardar(blockId: string) {
    editarBloque(
      { workspaceId, blockId, data: { content: { text: borrador.trim() } } },
      { ...refrescar, onSettled: () => setEditando(null) },
    )
  }

  return (
    <div className="space-y-3 p-4">
      {!todoAprobado && (
        <p data-testid="pending-review-count" className="text-sm text-muted-foreground">
          {tR('review.pending', { count: pendientes.length })}
        </p>
      )}

      {todoAprobado && (
        <p data-testid="ready-for-assembly" className="text-sm text-green-700 font-medium">
          {tR('review.all_approved')}
        </p>
      )}

      {pendientes.map((block) => {
        const contenido = (block.content ?? {}) as Record<string, unknown>
        const texto = typeof contenido.text === 'string' ? contenido.text : ''
        const originalIA =
          typeof contenido.original_ai_text === 'string' ? contenido.original_ai_text : null
        const editadoPor = typeof contenido.edited_by === 'string' ? contenido.edited_by : null
        const fuentes = Array.isArray(contenido.context_block_ids)
          ? (contenido.context_block_ids as string[])
          : []
        const anclado = contenido.context_scope === 'anchored' && fuentes.length > 0

        return (
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

            {/* De qué se apoyó la valoración. Sin esto, quien revisa no sabe qué debería decir
                el texto — y un apartado que leyó todo el informe merece un aviso, porque es el
                caso que produce resúmenes que omiten. */}
            <p data-testid={`fuente-${block.block_id}`} className="text-xs text-muted-foreground">
              {anclado
                ? tR('review.source_anchored', { tables: fuentes.join(', ') })
                : tR('review.source_full')}
            </p>

            {editando === block.block_id ? (
              <div className="space-y-2">
                <textarea
                  data-testid={`editor-${block.block_id}`}
                  value={borrador}
                  onChange={(e) => setBorrador(e.target.value)}
                  rows={8}
                  aria-label={tR('review.edit_label')}
                  className="w-full border rounded p-2 text-sm resize-y font-serif"
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    data-testid={`btn-guardar-${block.block_id}`}
                    disabled={!borrador.trim() || guardando}
                    onClick={() => guardar(block.block_id)}
                    className="px-2 py-1 text-xs bg-primary text-primary-foreground rounded disabled:opacity-50"
                  >
                    {tR('review.save')}
                  </button>
                  <button
                    type="button"
                    data-testid={`btn-cancelar-${block.block_id}`}
                    onClick={() => setEditando(null)}
                    className="px-2 py-1 text-xs border rounded"
                  >
                    {t('cancel', 'Cancelar')}
                  </button>
                </div>
              </div>
            ) : (
              <>
                <p className="text-sm whitespace-pre-wrap">{texto}</p>

                {editadoPor && (
                  <p
                    data-testid={`editado-por-${block.block_id}`}
                    className="text-xs text-muted-foreground italic"
                  >
                    {tR('review.edited_by', { who: editadoPor })}
                  </p>
                )}

                {/* El original de la IA sigue a la vista: si no, la edición es irreversible en
                    la práctica, y la evidencia de qué propuso el modelo vive sólo en el
                    registro de auditoría, que ninguna pantalla expone. */}
                {originalIA && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-muted-foreground">
                      {tR('review.show_original')}
                    </summary>
                    <p
                      data-testid={`original-ia-${block.block_id}`}
                      className="mt-1 p-2 bg-muted rounded whitespace-pre-wrap"
                    >
                      {originalIA}
                    </p>
                  </details>
                )}

                <div className="flex gap-2 flex-wrap">
                  <button
                    type="button"
                    data-testid={`btn-approve-${block.block_id}`}
                    disabled={isPending}
                    onClick={() => actuar(block.block_id, 'approve')}
                    className="px-2 py-1 text-xs bg-green-600 text-white rounded disabled:opacity-50"
                  >
                    {tR('review.approve')}
                  </button>
                  <button
                    type="button"
                    data-testid={`btn-editar-${block.block_id}`}
                    onClick={() => empezarAEditar(block.block_id, texto)}
                    className="px-2 py-1 text-xs border rounded hover:bg-accent"
                  >
                    {tR('review.edit')}
                  </button>
                  <button
                    type="button"
                    data-testid={`btn-reject-${block.block_id}`}
                    disabled={isPending}
                    onClick={() => actuar(block.block_id, 'reject')}
                    className="px-2 py-1 text-xs bg-destructive text-destructive-foreground rounded disabled:opacity-50"
                  >
                    {tR('review.reject')}
                  </button>
                  <button
                    type="button"
                    data-testid={`btn-regenerate-${block.block_id}`}
                    disabled={isPending}
                    onClick={() => actuar(block.block_id, 'regenerate')}
                    className="px-2 py-1 text-xs border rounded disabled:opacity-50"
                  >
                    {tR('review.regenerate')}
                  </button>
                </div>
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}
