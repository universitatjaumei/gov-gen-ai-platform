import { useTranslation } from 'react-i18next'
import type { TestProposalResponse } from '@/shared/api/generated/model'

interface SandboxTestResultViewerProps {
  result: TestProposalResponse
}

export function SandboxTestResultViewer({ result }: SandboxTestResultViewerProps) {
  const { t } = useTranslation('scripts')

  return (
    <div className="space-y-2 rounded border p-3 bg-card text-sm">
      <h3 className="font-medium">{t('test_result.title')}</h3>
      <div className="text-xs text-muted-foreground font-mono">
        <span>{t('test_result.hash')}: </span>
        <span>{result.hash}</span>
      </div>
      <pre className="text-xs bg-muted rounded p-2 overflow-auto max-h-48">
        {JSON.stringify(result.result, null, 2)}
      </pre>
    </div>
  )
}
