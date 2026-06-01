import { useTranslation } from 'react-i18next'

interface Props {
  open: boolean
  onReload: () => void
}

/**
 * Modal de conflicto de concurrencia optimista (1C.1).
 *
 * Se abre cuando el backend responde 409: otra sesión modificó el workspace.
 * Sólo ofrece "Recargar workspace" — los cambios no guardados se pierden
 * porque no podemos resolver el conflicto sin contexto humano.
 */
export function ConflictModal({ open, onReload }: Props) {
  const { t } = useTranslation('redaccion')

  if (!open) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="conflict-modal-title"
      data-testid="conflict-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
    >
      <div className="bg-background rounded-lg shadow-lg p-6 max-w-md w-full mx-4 space-y-4">
        <h2 id="conflict-modal-title" className="text-lg font-semibold">
          {t('autosave.conflict_title', 'Conflicto al guardar')}
        </h2>
        <p className="text-sm text-muted-foreground">
          {t(
            'autosave.conflict_body',
            'Otra sesión ha modificado este workspace. Recarga para ver los cambios; los tuyos no guardados se perderán.',
          )}
        </p>
        <div className="flex justify-end">
          <button
            data-testid="conflict-reload-btn"
            className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm"
            onClick={onReload}
          >
            {t('autosave.reload_workspace', 'Recargar workspace')}
          </button>
        </div>
      </div>
    </div>
  )
}
