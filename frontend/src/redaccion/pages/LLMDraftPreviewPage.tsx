import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useProposeLlmDraft,
  useValidateLlmDraft,
  useApproveAsTemplate,
  useApproveAsWorkspace,
} from '@/shared/api/generated/redaccion-llm-drafts/redaccion-llm-drafts'
import type {
  ReportTemplateDraftOutput,
  ReportTemplateDraftInput,
  ReportTemplateDraftValidationResult,
} from '@/shared/api/generated/model'
import { useAuth } from '@/shared/auth'

export function LLMDraftPreviewPage() {
  const { t } = useTranslation('common')
  const { user } = useAuth()
  const isAdmin = user?.role === 'superadmin' || user?.role === 'admin'

  const [promptText, setPromptText] = useState('')
  const [draftName, setDraftName] = useState('')
  const [mode, setMode] = useState<'template' | 'workspace'>('workspace')

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
