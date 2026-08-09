import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Eye, FileUp, Link, Loader2, Trash2 } from 'lucide-react'

import type { HubDocumentOut } from '@/shared/api/generated/model'
import { LanguageBadge, SourceKindBadge, SourceKindIcon } from './DocumentBadges'
import { formatTokens } from './format'

/**
 * Tabla de las unidades citables del corpus.
 *
 * Recibe los documentos **ya filtrados**: quién decide el filtro y de dónde salen los idiomas
 * disponibles es cosa de la página, que es la que tiene el corpus entero. Esta tabla sólo
 * pinta lo que le den y avisa de las tres acciones por fila.
 *
 * `headerActions` es el hueco donde la página cuelga las acciones sobre todo el corpus
 * (recalcular, limpiar), que viven en la cabecera pero no son responsabilidad de la tabla.
 */
export function DocumentsTable({
  documents,
  isLoading,
  langFilter,
  onLangFilterChange,
  presentLanguages,
  onPreview,
  onSubstitute,
  onDelete,
  headerActions,
}: {
  documents: HubDocumentOut[]
  isLoading: boolean
  langFilter: string
  onLangFilterChange: (value: string) => void
  presentLanguages: string[]
  onPreview: (documentId: string) => void
  onSubstitute: (doc: HubDocumentOut) => void
  onDelete: (doc: HubDocumentOut) => void
  headerActions?: ReactNode
}) {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')

  return (
    <div className="bg-card rounded-lg border overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b bg-muted/20 gap-3 flex-wrap">
        <h2 className="text-base font-medium">{t('hub.documents_table_title')}</h2>
        <div className="flex items-center gap-2 ml-auto">
          {presentLanguages.length > 1 && (
            <select
              value={langFilter}
              onChange={e => onLangFilterChange(e.target.value)}
              className="px-2 py-1 text-xs border rounded-md bg-background"
              aria-label={t('hub.filter_by_language')}
            >
              <option value="">{t('hub.all_languages')}</option>
              {presentLanguages.map(l => (
                <option key={l} value={l}>{l.toUpperCase()}</option>
              ))}
            </select>
          )}
          {headerActions}
        </div>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />{tc('loading')}
        </div>
      ) : documents.length === 0 ? (
        <div className="p-8 text-center text-muted-foreground text-sm">
          {t('hub.no_documents')}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/10 text-left text-muted-foreground">
                <th className="px-4 py-3 font-medium">{t('hub.doc_title')}</th>
                <th className="px-4 py-3 font-medium">{t('hub.doc_source')}</th>
                <th className="px-4 py-3 font-medium">{t('hub.doc_language')}</th>
                <th className="px-4 py-3 font-medium">{t('hub.doc_tokens')}</th>
                <th className="px-4 py-3 font-medium">{t('hub.doc_date')}</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {documents.map(doc => (
                <tr key={doc.id} className="border-b last:border-0 hover:bg-accent/20">
                  <td className="px-4 py-3 max-w-[220px]">
                    <div className="flex items-center gap-2">
                      <SourceKindIcon kind={doc.source_kind} />
                      <span className="truncate font-medium" title={doc.title}>{doc.title}</span>
                    </div>
                    {doc.canonical_url?.startsWith('http') && (
                      <a
                        href={doc.canonical_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-primary hover:underline mt-0.5 ml-6 truncate"
                        title={doc.canonical_url}
                      >
                        <Link className="w-3 h-3 shrink-0" />
                        {new URL(doc.canonical_url).hostname}
                      </a>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <SourceKindBadge kind={doc.source_kind} />
                  </td>
                  <td className="px-4 py-3">
                    <LanguageBadge language={doc.language} />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground tabular-nums">
                    {formatTokens(doc.token_count)}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs whitespace-nowrap">
                    {doc.created_at ? new Date(doc.created_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => onPreview(doc.id)}
                        title={t('hub.preview_doc')}
                        className="p-1 text-muted-foreground hover:text-primary transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => onSubstitute(doc)}
                        title={t('hub.substitute_doc')}
                        className="p-1 text-muted-foreground hover:text-primary transition-colors"
                      >
                        <FileUp className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => onDelete(doc)}
                        title={t('hub.delete_doc')}
                        className="p-1 text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
