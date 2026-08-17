import { useTranslation } from 'react-i18next'
import type { AuditResult } from '@/shared/api/generated/model'

interface ScriptCodePreviewProps {
  code: string
  auditResult: AuditResult
}

/** PRO.1 — la auditoría ya no es un sí o un no, así que la pantalla tampoco.
 *
 * `SAFE` es verde, `CRITICAL` es rojo y `WARNING` es ámbar: hay hallazgos, ninguno
 * bloqueante, y a eso se le puede dar salida por la cola de revisión. Cada hallazgo trae
 * su línea del servidor dentro del mensaje, que es lo que convierte «hay un problema» en
 * «está en la línea 14». */
const ESTILO_POR_NIVEL = {
  SAFE: 'bg-green-50 border-green-200 text-green-900',
  WARNING: 'bg-amber-50 border-amber-200 text-amber-900',
  CRITICAL: 'bg-red-50 border-red-200 text-red-900',
} as const

const ICONO_POR_NIVEL = { SAFE: '✓', WARNING: '!', CRITICAL: '✗' } as const

export function ScriptCodePreview({ code, auditResult }: ScriptCodePreviewProps) {
  const { t } = useTranslation('scripts')
  const nivel = auditResult.risk_level

  const veredicto = auditResult.approved
    ? t('audit.approved')
    : auditResult.puede_revisarse
      ? t('audit.revisable')
      : t('audit.rejected')

  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-sm font-medium mb-1">{t('code_preview.title')}</h3>
        <pre className="text-xs bg-muted rounded p-3 overflow-auto max-h-64 whitespace-pre-wrap">
          {code}
        </pre>
      </div>

      <div
        data-testid="audit-summary"
        data-risk-level={nivel}
        className={`rounded p-3 text-sm border ${ESTILO_POR_NIVEL[nivel]}`}
      >
        <div className="flex items-center gap-2 font-medium">
          <span aria-hidden="true">{ICONO_POR_NIVEL[nivel]}</span>
          <span>{veredicto}</span>
          <span className="text-xs ml-auto">
            {t('audit.risk_level')}: {t(`audit.level.${nivel}`)}
          </span>
        </div>

        {auditResult.findings.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium">{t('audit.findings')}:</p>
            <ul className="mt-1 space-y-0.5">
              {auditResult.findings.map((finding, i) => (
                <li
                  key={`${finding.rule}-${finding.line}-${i}`}
                  data-testid="audit-finding"
                  className={`text-xs ${
                    finding.severity === 'CRITICAL' ? 'text-red-700' : 'text-amber-700'
                  }`}
                >
                  • {finding.message}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
