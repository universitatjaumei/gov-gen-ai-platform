/**
 * Panel de auditoría NER y configuración del modo de anonimización por workspace.
 * Deploy: edge — Fase 13.2
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useGetAnonymizationSummary,
  usePatchAnonymizationMode,
  useReAnalyzeAnonymization,
} from '../hooks/useAnonymizationApi'

interface WorkspaceAnonymizationPanelProps {
  workspaceId: string
  workspaceStatus: string
}

const MODES = [
  'off',
  'detect_only',
  'replace',
  'replace_with_disposition_7',
] as const

const LOCKED_STATUSES = new Set(['drafting', 'in_review', 'assembled', 'exported'])

export function WorkspaceAnonymizationPanel({
  workspaceId,
  workspaceStatus,
}: WorkspaceAnonymizationPanelProps) {
  const { t } = useTranslation('redaccion')
  const isLocked = LOCKED_STATUSES.has(workspaceStatus)

  const { data: summary, isLoading } = useGetAnonymizationSummary(workspaceId)
  const patchMode = usePatchAnonymizationMode(workspaceId)
  const reAnalyze = useReAnalyzeAnonymization(workspaceId)

  const currentMode = summary?.current_workspace_mode ?? 'replace'
  const [selectedMode, setSelectedMode] = useState<string>(currentMode)

  const handleModeChange = (mode: string) => {
    if (isLocked) return
    setSelectedMode(mode)
  }

  const handleApplyMode = () => {
    patchMode.mutate({ mode: selectedMode })
  }

  const handleReAnalyze = () => {
    reAnalyze.mutate()
  }

  if (isLoading) {
    return <div className="p-4 text-sm text-muted-foreground">{t('anonymization.loading', 'Cargando…')}</div>
  }

  return (
    <div data-testid="workspace-anonymization-panel" className="space-y-4 p-4">
      {/* Sección 1 — Modo */}
      <section aria-labelledby="anon-mode-heading">
        <h3 id="anon-mode-heading" className="text-sm font-semibold mb-2">
          {t('anonymization.mode_label')}
        </h3>

        {isLocked && (
          <p
            data-testid="anon-mode-locked-msg"
            className="text-xs text-amber-600 mb-2"
          >
            {t('anonymization.mode_locked')}
          </p>
        )}

        <div className="space-y-2">
          {MODES.map(mode => (
            <label key={mode} className="flex items-start gap-2 cursor-pointer">
              <input
                type="radio"
                name="anon-mode"
                value={mode}
                checked={(summary?.current_workspace_mode ?? selectedMode) === mode}
                disabled={isLocked}
                onChange={() => handleModeChange(mode)}
                className="mt-0.5"
              />
              <span className="text-sm">
                <span className="font-medium">{t(`anonymization.modes.${mode}`)}</span>
                <br />
                <span className="text-xs text-muted-foreground">
                  {t(`anonymization.mode_descriptions.${mode}`)}
                </span>
              </span>
            </label>
          ))}
        </div>

        {(summary?.current_workspace_mode === 'replace_with_disposition_7') && (
          <span
            data-testid="anon-badge-lopdgdd"
            className="inline-block mt-2 px-2 py-0.5 text-xs font-bold bg-blue-100 text-blue-800 rounded"
          >
            {t('anonymization.badge_lopdgdd')}
          </span>
        )}

        {!isLocked && (
          <button
            type="button"
            data-testid="btn-change-mode"
            onClick={handleApplyMode}
            disabled={patchMode.isPending}
            className="mt-3 text-sm px-3 py-1 bg-primary text-primary-foreground rounded"
          >
            {t('anonymization.btn_change_mode')}
          </button>
        )}
      </section>

      {/* Sección 2 — Tabla de conteos */}
      <section aria-labelledby="anon-counts-heading">
        <h3 id="anon-counts-heading" className="text-sm font-semibold mb-2">
          {t('anonymization.table_title')}
        </h3>

        {!summary || summary.total_spans === 0 ? (
          <p className="text-xs text-muted-foreground">{t('anonymization.no_run')}</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="py-1 pr-4">{t('anonymization.col_type')}</th>
                <th className="py-1">{t('anonymization.col_count')}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(summary.counts_by_type).map(([type, count]) => (
                <tr key={type} className="border-b last:border-0">
                  <td className="py-1 pr-4 font-mono text-xs">{type}</td>
                  <td
                    data-testid={`anon-type-${type}`}
                    className="py-1"
                  >
                    {count}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td className="py-1 text-xs font-semibold">{t('anonymization.total')}</td>
                <td
                  data-testid="anon-total-spans"
                  className="py-1 font-semibold"
                >
                  {summary.total_spans}
                </td>
              </tr>
            </tfoot>
          </table>
        )}
      </section>

      {/* Sección 3 — Acciones */}
      <section>
        <button
          type="button"
          data-testid="btn-reanalyze"
          onClick={handleReAnalyze}
          disabled={reAnalyze.isPending}
          className="text-sm px-3 py-1 border rounded"
        >
          {reAnalyze.isPending
            ? t('anonymization.reanalyzing')
            : t('anonymization.btn_reanalyze')}
        </button>
      </section>
    </div>
  )
}
