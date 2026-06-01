import { useTranslation } from 'react-i18next'
import type { AuditResult } from '@/shared/api/generated/model'

interface ScriptCodePreviewProps {
  code: string
  auditResult: AuditResult
}

export function ScriptCodePreview({ code, auditResult }: ScriptCodePreviewProps) {
  const { t } = useTranslation('scripts')

  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-sm font-medium mb-1">{t('code_preview.title')}</h3>
        <pre className="text-xs bg-muted rounded p-3 overflow-auto max-h-64 whitespace-pre-wrap">
          {code}
        </pre>
      </div>

      <div className={`rounded p-3 text-sm ${auditResult.approved ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
        <div className="flex items-center gap-2 font-medium">
          <span>{auditResult.approved ? '✓' : '✗'}</span>
          <span>{auditResult.approved ? t('audit.approved') : t('audit.rejected')}</span>
          <span className="text-xs text-muted-foreground ml-auto">
            {t('audit.risk_level')}: {auditResult.risk_level}
          </span>
        </div>

        {auditResult.findings.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium text-muted-foreground">{t('audit.findings')}:</p>
            <ul className="mt-1 space-y-0.5">
              {auditResult.findings.map((finding, i) => (
                <li key={i} className="text-xs text-red-700">• {finding}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
