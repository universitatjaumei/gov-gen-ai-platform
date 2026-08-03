import { useTranslation } from 'react-i18next'
import { Loader2 } from 'lucide-react'

import type { HubDocumentDetailOut } from '@/shared/api/generated/model'

/** Vista del markdown ingestado, que es lo que acaba viendo el modelo. */
export function DocumentPreviewModal({
  detail,
  isLoading,
  onClose,
}: {
  detail: HubDocumentDetailOut | undefined
  isLoading: boolean
  onClose: () => void
}) {
  const { t: tc } = useTranslation('common')

  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 flex items-center justify-center bg-black/40 z-50 p-4">
      <div className="bg-card rounded-lg w-full max-w-3xl max-h-[80vh] flex flex-col shadow-xl">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-base font-semibold truncate">
            {isLoading ? tc('loading') : detail?.title}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-muted-foreground hover:text-foreground"
          >✕</button>
        </div>
        <div className="overflow-y-auto p-4 flex-1">
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 text-muted-foreground py-8">
              <Loader2 className="w-5 h-5 animate-spin" />{tc('loading')}
            </div>
          ) : (
            <pre className="text-xs whitespace-pre-wrap font-mono text-foreground/80">
              {detail?.markdown_content}
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}
