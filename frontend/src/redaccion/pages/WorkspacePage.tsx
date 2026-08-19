import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'

import {
  useGetWorkspaceById,
  useGetTemplateUiContractApiV1HubRedaccionTemplateVersionsVersionIdUiContractGet as useGetTemplateUiContract,
  getGetWorkspaceByIdQueryKey,
} from '@/shared/api/generated/hub-redaccion/hub-redaccion'
import {
  useRunWorkspace,
  useUploadWorkspaceInput,
} from '@/shared/api/generated/redaccion-workspaces/redaccion-workspaces'
import type { ReportUIContract, WorkspaceOut } from '@/shared/api/generated/model'

import { descargarConAutorizacion } from '@/shared/api/download'
import { FocusLayout } from '@/shared/layout/FocusLayout'
import { useFocusStore } from '@/shared/layout/useFocusStore'
import { AIBlockReviewPanel } from '../components/AIBlockReviewPanel'
import { DataQualityPanel } from '../components/DataQualityPanel'
import { ReportUIContractRenderer } from '../components/ReportUIContractRenderer'
import { WorkspaceEditor } from '../components/WorkspaceEditor'
import { WorkspaceStatusBar } from '../components/WorkspaceStatusBar'

/** Estados en los que ya hay algo que previsualizar. */
const CON_CONTENIDO = new Set(['in_review', 'assembled', 'exported'])

/**
 * La pantalla donde se trabaja un informe (VER.4).
 *
 * El módulo sabía crear workspaces y **no tenía dónde abrirlos**: `WorkspaceEditor`,
 * `DynamicUploadSlots`, `AIBlockReviewPanel` y `DataQualityPanel` existían desde 9R sin que
 * ninguna ruta los montara, y `App.tsx` solo enrutaba la vista de impresión. Esta página no
 * inventa interfaz: compone lo que ya estaba escrito y le da una dirección.
 *
 * El formulario de entrada sale del `ui_contract` de la versión de plantilla y no de campos
 * fijos —regla maestra nº1—, así que una plantilla nueva cambia el formulario sin tocar
 * React.
 */
export function WorkspacePage() {
  const { id = '' } = useParams()
  const { t } = useTranslation('redaccion')
  const cajonAbierto = useFocusStore((s) => s.drawerVisible)
  const alternarCajon = useFocusStore((s) => s.toggleDrawer)
  const irAlCopiloto = useFocusStore((s) => s.setActiveTab)

  /** Abre el cajón directamente en la pestaña del copiloto, que es lo que se ha pedido. */
  function abrirCopiloto() {
    if (!cajonAbierto) irAlCopiloto('copilot')
    alternarCajon()
  }
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [errorDeSubida, setErrorDeSubida] = useState('')

  const { data: workspaceRaw, isLoading } = useGetWorkspaceById(id, {
    query: {
      enabled: !!id,
      // Mientras genera, el estado lo cambia una tarea de fondo: sin refresco, la pantalla
      // se queda en «generando» hasta que alguien recarga a mano.
      refetchInterval: (query) => {
        const estado = (query.state.data as WorkspaceOut | undefined)?.status
        return estado === 'drafting' || estado === 'extracting' ? 3000 : false
      },
    },
  })
  const workspace = workspaceRaw as unknown as WorkspaceOut | undefined

  const { data: contratoRaw } = useGetTemplateUiContract(
    workspace?.template_version_id ?? '',
    { query: { enabled: !!workspace?.template_version_id } },
  )
  const contrato = contratoRaw as unknown as ReportUIContract | undefined

  const subir = useUploadWorkspaceInput()
  const { mutate: generar, isPending: generando } = useRunWorkspace()

  if (isLoading) return <div className="p-4">{tc('loading')}</div>
  if (!workspace) return <div className="p-4">{t('workspace_not_found')}</div>

  const enMarcha = workspace.status === 'drafting' || workspace.status === 'extracting'

  /** Sube lo que el contrato pidiera y lanza la generación. */
  async function enviar(datos: { fields: Record<string, string>; files: Record<string, File[]> }) {
    setErrorDeSubida('')
    try {
      for (const [slotId, ficheros] of Object.entries(datos.files)) {
        for (const fichero of ficheros) {
          await subir.mutateAsync({ workspaceId: id, slotId, data: { file: fichero } })
        }
      }
    } catch (fallo) {
      setErrorDeSubida((fallo as Error).message)
      return
    }
    generar({ workspaceId: id }, {
      onSuccess: () => qc.invalidateQueries({ queryKey: getGetWorkspaceByIdQueryKey(id) }),
    })
  }

  /** CUR.5 — el DOCX se pide con el token; un `<a href>` a la API se lleva un 401. */
  async function exportar() {
    setErrorDeSubida('')
    try {
      await descargarConAutorizacion(
        `/api/v1/redaccion/workspaces/${id}/export`,
        `informe_${id}.docx`,
      )
    } catch (fallo) {
      setErrorDeSubida((fallo as Error).message)
    }
  }

  return (
    <FocusLayout context={{ type: 'informe', entityId: id }}>
      <div className="space-y-4 p-4">
        <WorkspaceStatusBar workspaceId={id} />

      {workspace.status === 'error' && (
        <p data-testid="workspace-error" className="p-3 border rounded-md text-sm bg-destructive/10 text-destructive">
          {t('workspace_error')}
        </p>
      )}

      {contrato && (
        <section className="border rounded-lg p-4 bg-card">
          <h2 className="text-base font-medium mb-3">{t('workspace_inputs')}</h2>
          <ReportUIContractRenderer contract={contrato} onSubmit={enviar} />
          {errorDeSubida && (
            <p className="text-sm text-destructive mt-2">{errorDeSubida}</p>
          )}
        </section>
      )}

      <div className="flex items-center gap-3 flex-wrap">
        <button
          type="button"
          data-testid="btn-generar-informe"
          disabled={generando || enMarcha}
          onClick={() => generar({ workspaceId: id }, {
            onSuccess: () => qc.invalidateQueries({ queryKey: getGetWorkspaceByIdQueryKey(id) }),
          })}
          className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md disabled:opacity-50"
        >
          {enMarcha ? t('workspace_generating') : t('workspace_generate')}
        </button>

        {CON_CONTENIDO.has(workspace.status) && (
          <>
            <Link
              to={`/redaccion/workspaces/${id}/preview`}
              className="px-4 py-2 text-sm border rounded-md hover:bg-accent"
            >
              {t('workspace_preview')}
            </Link>
            {/* PRO.5 — el informe se puede descargar: el servicio existía y ninguna ruta lo
                servía, así que no había de dónde bajarlo. CUR.5 — y pedirlo con un `<a href>` es
                una navegación sin cabecera de autorización: el endpoint depende de
                `get_current_user`, así que devolvía 401 y el navegador enseñaba su propio error de
                descarga. */}
            <button
              type="button"
              data-testid="btn-exportar"
              onClick={() => exportar()}
              className="px-4 py-2 text-sm border rounded-md hover:bg-accent"
            >
              {t('workspace_export')}
            </button>
          </>
        )}

        {/* PRO.6 — el copiloto se abre desde aquí. Su panel existía y ninguna ruta montaba el
            layout que lo contiene, así que era inalcanzable. Va en un cajón lateral y arranca
            cerrado, como en la aplicación NiceGUI: un panel que nadie ha pedido tapa media
            pantalla. */}
        <button
          type="button"
          data-testid="btn-abrir-copiloto"
          aria-expanded={cajonAbierto}
          onClick={abrirCopiloto}
          className="px-4 py-2 text-sm border rounded-md hover:bg-accent ml-auto"
        >
          {t('workspace_copilot')}
        </button>
        </div>

        <DataQualityPanel workspaceId={id} />
        <WorkspaceEditor workspace={{ blocks: workspace.blocks, status: workspace.status }} />
        {contrato?.ai_review_panel_enabled && <AIBlockReviewPanel workspaceId={id} />}
      </div>
    </FocusLayout>
  )
}
