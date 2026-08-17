import { useTranslation } from 'react-i18next'
import type { RevisionDelModelo } from '@/shared/api/generated/model'

/**
 * El veredicto del modelo auditor (PRO.2) — la segunda opinión, no la puerta.
 *
 * Se pinta **aparte** del resultado de la auditoría determinista y con otra forma, porque
 * tienen autoridades distintas: la determinista bloquea y no se puede convencer; ésta explica
 * lo que un AST no puede ver —si el script hace lo que se pidió, si asume una columna que no
 * consta—. Mezclarlas en un mismo cuadro invitaría a leer un «acepta» del modelo como si
 * fuera una aprobación, y no lo es.
 */
const ESTILO_POR_VEREDICTO = {
  acepta: 'border-green-200 bg-green-50 text-green-900',
  duda: 'border-amber-200 bg-amber-50 text-amber-900',
  rechaza: 'border-red-200 bg-red-50 text-red-900',
} as const

interface Props {
  revision: RevisionDelModelo
}

export function ModelAuditVerdict({ revision }: Props) {
  const { t } = useTranslation('scripts')

  return (
    <div
      data-testid="model-audit-verdict"
      data-veredicto={revision.veredicto}
      className={`rounded border p-3 text-sm ${ESTILO_POR_VEREDICTO[revision.veredicto]}`}
    >
      <div className="flex items-center gap-2 font-medium">
        <span>{t('model_audit.title')}</span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-white/60">
          {t(`model_audit.verdict.${revision.veredicto}`)}
        </span>
        <span className="text-xs ml-auto opacity-70">{revision.model_used}</span>
      </div>

      {revision.motivos.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs">
          {revision.motivos.map((motivo, i) => (
            <li key={i} data-testid="model-audit-reason">• {motivo}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
