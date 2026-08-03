import { useTranslation } from 'react-i18next'

import { RETRIEVAL_LABELS } from './constants'
import { formatTokens } from './format'

/** Recuerda con qué estrategia se recupera el corpus y cuánto pesa en tokens. */
export function RetrievalBanner({ mode, totalTokens }: { mode: string; totalTokens: number }) {
  const { t } = useTranslation('admin')

  const modeLabel = RETRIEVAL_LABELS[mode] ?? mode
  const recommendation =
    mode === 'RAG'               ? t('hub.retrieval_rec_vector', 'Usa RAG para documentos extensos.')
    : mode === 'MD_LONG_CONTEXT' ? t('hub.retrieval_rec_lc', 'El documento completo se envía al LLM en cada consulta.')
    : t('hub.retrieval_rec_agentic', 'El agente decide qué fragmentos leer.')

  return (
    <div className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
      <div className="flex-1">
        <span className="font-medium">{t('hub.retrieval_mode_label', 'Modo de retrieval')}: </span>
        <strong>{modeLabel}</strong>
        {totalTokens > 0 && (
          <span className="text-muted-foreground"> — {formatTokens(totalTokens)} tokens totales</span>
        )}
        <p className="text-muted-foreground mt-0.5 text-xs">{recommendation}</p>
      </div>
    </div>
  )
}
