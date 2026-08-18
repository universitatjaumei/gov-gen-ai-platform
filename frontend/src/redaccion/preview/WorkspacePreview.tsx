import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useGetWorkspacePreview } from '@/shared/api/generated/redaccion-workspaces/redaccion-workspaces'
import { PreviewRenderer } from './PreviewRenderer'
import type { PreviewPayload } from './PreviewRenderer'
import './WorkspacePreview.css'

/** Los bloques que el servidor devuelve como pendientes en el 409, si es lo que ha pasado. */
function bloquesPendientes(error: unknown): string[] {
  const detalle = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  const pendientes = (detalle as { pending_block_ids?: unknown })?.pending_block_ids
  return Array.isArray(pendientes) ? pendientes.map(String) : []
}

export function WorkspacePreview() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation('common')
  const { t: tr } = useTranslation('redaccion')

  const { data, isLoading, isError, error } = useGetWorkspacePreview(id ?? '')

  if (isLoading) return <div className="preview-loading">{t('loading')}</div>

  // GUI.5 — cualquier fallo salía como la palabra «Error», a secas. El caso normal no es un
  // fallo: es que falta aprobar un bloque de IA, y el servidor lo dice con nombres y apellidos
  // en un 409. Dejarlo en «Error» convierte un paso pendiente en un misterio.
  const pendientes = isError ? bloquesPendientes(error) : []
  if (pendientes.length > 0) {
    return (
      <div className="preview-error" data-testid="preview-pendiente">
        <p>{tr('preview_pending', { count: pendientes.length })}</p>
        <ul>
          {pendientes.map((bloque) => (
            <li key={bloque}>{bloque}</li>
          ))}
        </ul>
      </div>
    )
  }
  if (isError || !data) return <div className="preview-error">{t('error')}</div>

  return (
    <div className="workspace-preview-page">
      <div className="preview-toolbar no-print">
        <button
          className="btn-print"
          onClick={() => window.print()}
        >
          Imprimir / Exportar PDF
        </button>
      </div>
      <div className="preview-a4-container">
        <PreviewRenderer payload={data as unknown as PreviewPayload} />
      </div>
    </div>
  )
}
