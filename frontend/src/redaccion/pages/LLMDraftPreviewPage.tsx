import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useProposeLlmDraft,
  useValidateLlmDraft,
  useApproveAsTemplate,
  useApproveAsWorkspace,
  useDescribeSampleFile,
} from '@/shared/api/generated/redaccion-llm-drafts/redaccion-llm-drafts'
import type {
  ReportTemplateDraftOutput,
  ReportTemplateDraftInput,
  ReportTemplateDraftValidationResult,
  MuestraDeDatos,
} from '@/shared/api/generated/model'
import { useAuth } from '@/shared/auth'

export function LLMDraftPreviewPage() {
  const { t } = useTranslation('common')
  const { user } = useAuth()
  const isAdmin = user?.role === 'superadmin' || user?.role === 'admin'

  const [promptText, setPromptText] = useState('')
  const [draftName, setDraftName] = useState('')
  const [mode, setMode] = useState<'template' | 'workspace'>('workspace')

  /**
   * INF.4 — la estructura del fichero sobre el que va el informe.
   *
   * Se ofrece **antes** del prompt a propósito: sin ella el modelo no conoce las columnas y
   * tiene que adivinarlas, que es lo que hizo fracasar la propuesta en las pruebas del
   * 2026-08-20. El servidor la resume y **anonimiza los valores**, y aquí se enseña lo que se
   * va a enviar: quien pide el informe puede ver qué sale de su organización antes de que
   * salga.
   */
  const [muestra, setMuestra] = useState<MuestraDeDatos | null>(null)
  const [errorDeMuestra, setErrorDeMuestra] = useState('')
  const { mutate: describirFichero, isPending: leyendoFichero } = useDescribeSampleFile()

  function elegirFichero(fichero: File | undefined) {
    setErrorDeMuestra('')
    setMuestra(null)
    if (!fichero) return
    describirFichero(
      { data: { file: fichero } },
      {
        onSuccess: (resumen) => setMuestra(resumen as unknown as MuestraDeDatos),
        onError: (fallo: unknown) =>
          setErrorDeMuestra((fallo as Error)?.message || t('error')),
      },
    )
  }

  const { mutate: propose, data: proposedRaw, isPending: isProposing } = useProposeLlmDraft()
  const { mutate: validateMutate, data: validationRaw, isPending: isValidating } = useValidateLlmDraft()
  const { mutate: approveTemplate, isPending: isApprovingTemplate } = useApproveAsTemplate()
  const { mutate: approveWorkspace, isPending: isApprovingWorkspace } = useApproveAsWorkspace()

  const draft = proposedRaw as unknown as ReportTemplateDraftOutput | undefined
  const validation = validationRaw as unknown as ReportTemplateDraftValidationResult | undefined
  const isApproving = isApprovingTemplate || isApprovingWorkspace
  const canApprove = !!draft && !isValidating && (!validation || validation.ok === true)

  useEffect(() => {
    if (draft) {
      validateMutate({ data: draft as unknown as ReportTemplateDraftInput })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft])

  function handlePropose() {
    if (!promptText) return
    propose({
      data: {
        prompt_nl: promptText,
        mode: mode === 'template' ? 'admin_template' : 'user_workspace',
        // Si no hay fichero va `null` y el servidor se comporta como antes.
        muestra,
      },
    })
  }

  function handleApprove() {
    if (!draft || !canApprove) return
    const name = draftName || 'Nuevo informe'
    if (mode === 'template') {
      approveTemplate({ data: { draft: draft as unknown as ReportTemplateDraftInput, name } })
    } else {
      approveWorkspace({ data: { draft: draft as unknown as ReportTemplateDraftInput, name } })
    }
  }

  return (
    <div className="space-y-4 p-4 max-w-2xl">
      {/* INF.4 — el fichero va antes del prompt: describir un informe sobre datos que el modelo
          no ha visto es pedirle que adivine los nombres de las columnas. Es opcional. */}
      <div className="space-y-2 border rounded p-3 bg-card">
        <label htmlFor="fichero-de-muestra" className="text-sm font-medium block">
          {t('sample_label', 'Fichero de datos (opcional)')}
        </label>
        <p className="text-xs text-muted-foreground">
          {t(
            'sample_help',
            'Si lo aportas, la IA verá los nombres de las columnas y su tipo. Los valores se anonimizan antes de enviarse.',
          )}
        </p>
        <input
          id="fichero-de-muestra"
          data-testid="input-muestra"
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(e) => elegirFichero(e.target.files?.[0])}
        />
        {leyendoFichero && <p className="text-xs text-muted-foreground">{t('loading')}</p>}
        {errorDeMuestra && (
          <p role="alert" className="text-xs text-destructive">{errorDeMuestra}</p>
        )}
        {muestra && (
          <div data-testid="resumen-de-muestra" className="text-xs space-y-1">
            <p>
              <strong>{muestra.nombre_del_fichero}</strong> — {muestra.filas_totales}{' '}
              {t('sample_rows', 'filas')}
            </p>
            {/* Lo que se va a enviar, a la vista. */}
            <p className="text-muted-foreground">{muestra.columnas.join(' · ')}</p>
          </div>
        )}
      </div>

      {/* Prompt input */}
      <div className="space-y-2">
        <textarea
          data-testid="input-prompt"
          value={promptText}
          onChange={e => setPromptText(e.target.value)}
          rows={3}
          placeholder="Describe el informe en lenguaje natural..."
          className="w-full border rounded p-2 text-sm resize-none"
        />
        <button
          type="button"
          data-testid="btn-propose"
          disabled={isProposing || !promptText}
          onClick={handlePropose}
          className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded disabled:opacity-50"
        >
          {isProposing ? t('loading') : 'Generar propuesta'}
        </button>
      </div>

      {/* Draft preview */}
      {draft && (
        <div data-testid="draft-preview" className="border rounded p-4 space-y-3 bg-card">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Perfil: <strong>{draft.proposed_profile}</strong></span>
            <span>·</span>
            <span>Secciones: {draft.proposed_sections?.length ?? 0}</span>
            <span>·</span>
            <span>Modelo: {draft.model_used}</span>
          </div>

          {draft.rationale && (
            <p className="text-xs text-muted-foreground italic">{draft.rationale}</p>
          )}

          {/* Validation errors */}
          {validation && !validation.ok && (
            <ul data-testid="validation-errors" className="space-y-1">
              {(validation.errors ?? []).map((e, i) => (
                <li
                  key={i}
                  data-testid={`error-${e.field}`}
                  className="text-xs text-destructive"
                >
                  <span className="font-medium">{e.field}</span>: {e.message}
                </li>
              ))}
            </ul>
          )}

          {/* Mode toggle — superadmin/admin only */}
          {isAdmin && (
            <div className="flex gap-2">
              <button
                type="button"
                data-testid="mode-workspace"
                onClick={() => setMode('workspace')}
                className={`px-3 py-1 text-xs rounded border transition-colors ${
                  mode === 'workspace' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent/30'
                }`}
              >
                Crear workspace
              </button>
              <button
                type="button"
                data-testid="mode-template"
                onClick={() => setMode('template')}
                className={`px-3 py-1 text-xs rounded border transition-colors ${
                  mode === 'template' ? 'bg-primary text-primary-foreground' : 'hover:bg-accent/30'
                }`}
              >
                Crear plantilla
              </button>
            </div>
          )}

          {/* Name input */}
          <input
            data-testid="input-draft-name"
            value={draftName}
            onChange={e => setDraftName(e.target.value)}
            placeholder={mode === 'template' ? 'Nombre de plantilla' : 'Nombre del informe'}
            className="w-full border rounded px-3 py-1.5 text-sm"
          />

          {/* Approve button */}
          <button
            type="button"
            data-testid="btn-approve"
            disabled={!canApprove || isApproving}
            onClick={handleApprove}
            className="px-4 py-2 text-sm bg-green-600 text-white rounded disabled:opacity-50"
          >
            {isApproving ? t('loading') : 'Aprobar y crear'}
          </button>
        </div>
      )}
    </div>
  )
}
