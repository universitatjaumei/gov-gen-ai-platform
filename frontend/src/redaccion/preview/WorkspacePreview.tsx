import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useGetWorkspacePreview } from '@/shared/api/generated/redaccion-workspaces/redaccion-workspaces'
import { PreviewRenderer } from './PreviewRenderer'
import type { PreviewPayload } from './PreviewRenderer'
import './WorkspacePreview.css'

export function WorkspacePreview() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation('common')

  const { data, isLoading, isError } = useGetWorkspacePreview(id ?? '')

  if (isLoading) return <div className="preview-loading">{t('loading')}</div>
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
