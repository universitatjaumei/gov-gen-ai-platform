import { Fragment, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Download, Star, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useListChatbotsApiV1HubChatbotsGet } from '@/shared/api/generated/hub-chatbots/hub-chatbots'
import { useGetInteractionsForReviewApiV1HubFeedbackChatbotIdReviewGet } from '@/shared/api/generated/hub-feedback/hub-feedback'
import type { ChatbotRead, InteractionReviewOut } from '@/shared/api/generated/model'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

function StarRating({ score }: { score: number | null }) {
  if (score === null) return <span className="text-muted-foreground">—</span>
  return (
    <span className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={`h-3.5 w-3.5 ${n <= score ? 'text-yellow-400 fill-yellow-400' : 'text-muted-foreground'}`}
        />
      ))}
    </span>
  )
}

function exportToCsv(chatbotId: string, interactions: InteractionReviewOut[]) {
  const header = ['date', 'user_message', 'assistant_message', 'score', 'comment']
  const escape = (s: string) => `"${s.replace(/"/g, '""')}"`
  const rows = interactions.map((i) => [
    i.created_at,
    escape(i.user_message),
    escape(i.assistant_message),
    String(i.feedback_score ?? ''),
    escape(i.feedback_text ?? ''),
  ])
  const csv = [header, ...rows].map((r) => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `interactions-${chatbotId}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export function ReportsPage() {
  const { t } = useTranslation('admin')

  const [selectedChatbotId, setSelectedChatbotId] = useState('')
  const [onlyLowScores, setOnlyLowScores] = useState(false)
  const [expandedRow, setExpandedRow] = useState<string | null>(null)

  const { data: chatbotsRaw } = useListChatbotsApiV1HubChatbotsGet()
  const chatbots: ChatbotRead[] = (chatbotsRaw as unknown as ChatbotRead[] | undefined) ?? []

  if (!selectedChatbotId && chatbots.length > 0) {
    setSelectedChatbotId(chatbots[0].id)
  }

  const { data: interactions = [], isLoading } =
    useGetInteractionsForReviewApiV1HubFeedbackChatbotIdReviewGet(
      selectedChatbotId,
      { only_low_scores: onlyLowScores },
      { query: { enabled: !!selectedChatbotId } },
    )

  const scoredInteractions = interactions.filter((i) => i.feedback_score != null)
  const avgScore =
    scoredInteractions.length > 0
      ? scoredInteractions.reduce((s, i) => s + i.feedback_score!, 0) / scoredInteractions.length
      : null

  const scoreDistribution = [1, 2, 3, 4, 5].map((star) => ({
    star,
    count: scoredInteractions.filter((i) => i.feedback_score === star).length,
  }))

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={selectedChatbotId}
          onChange={(e) => setSelectedChatbotId(e.target.value)}
          className="rounded-md border bg-background px-3 py-1.5 text-sm"
        >
          {chatbots.map((cb) => (
            <option key={cb.id} value={cb.id}>
              {cb.name}
            </option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={onlyLowScores}
            onChange={(e) => setOnlyLowScores(e.target.checked)}
            className="rounded"
          />
          {t('hub.reports_only_low', 'Solo puntuaciones bajas')}
        </label>

        <button
          onClick={() => exportToCsv(selectedChatbotId, interactions)}
          disabled={interactions.length === 0}
          aria-label={t('hub.reports_export_csv', 'Exportar CSV')}
          className="ml-auto flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-accent disabled:opacity-50"
        >
          <Download className="h-3.5 w-3.5" />
          CSV
        </button>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t('hub.reports_total', 'Total interacciones')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{interactions.length}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('hub.reports_avg_score', 'Puntuación media')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold" data-testid="avg-score">
              {avgScore !== null ? avgScore.toFixed(1) : '—'}
            </p>
            {scoredInteractions.length > 0 && (
              <div className="mt-2 h-16">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={scoreDistribution} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                    <XAxis dataKey="star" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                      {scoreDistribution.map((entry) => (
                        <Cell
                          key={entry.star}
                          fill={entry.star <= 2 ? '#f87171' : entry.star === 3 ? '#facc15' : '#4ade80'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Interactions table */}
      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : interactions.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          {t('hub.reports_no_data', 'Sin interacciones para este chatbot')}
        </p>
      ) : (
        <div className="rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50 text-left text-xs text-muted-foreground">
                <th className="px-3 py-2">{t('hub.reports_date', 'Fecha')}</th>
                <th className="px-3 py-2">{t('hub.reports_user_msg', 'Mensaje usuario')}</th>
                <th className="px-3 py-2">{t('hub.reports_score', 'Puntuación')}</th>
                <th className="px-3 py-2">{t('hub.reports_comment', 'Comentario')}</th>
                <th className="px-3 py-2 w-10" />
              </tr>
            </thead>
            <tbody>
              {interactions.map((interaction) => (
                <Fragment key={interaction.id}>
                  <tr className="border-b hover:bg-muted/30">
                    <td className="px-3 py-2 text-muted-foreground whitespace-nowrap">
                      {new Date(interaction.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-2 max-w-xs truncate">
                      {interaction.user_message}
                    </td>
                    <td className="px-3 py-2">
                      <StarRating score={interaction.feedback_score ?? null} />
                    </td>
                    <td className="px-3 py-2 max-w-xs truncate text-muted-foreground">
                      {interaction.feedback_text ?? '—'}
                    </td>
                    <td className="px-3 py-2">
                      <button
                        aria-label={
                          expandedRow === interaction.id
                            ? t('hub.reports_collapse', 'Collapse')
                            : t('hub.reports_expand', 'Expand')
                        }
                        onClick={() =>
                          setExpandedRow(expandedRow === interaction.id ? null : interaction.id)
                        }
                        className="rounded p-0.5 hover:bg-accent"
                      >
                        {expandedRow === interaction.id ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </button>
                    </td>
                  </tr>
                  {expandedRow === interaction.id && (
                    <tr className="bg-muted/20">
                      <td colSpan={5} className="px-4 py-3 space-y-2">
                        <div>
                          <p className="text-xs font-medium text-muted-foreground mb-1">
                            {t('hub.reports_user_msg', 'Mensaje usuario')}
                          </p>
                          <p className="text-sm">{interaction.user_message}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-muted-foreground mb-1">
                            {t('hub.reports_assistant_msg', 'Respuesta asistente')}
                          </p>
                          <p className="text-sm">{interaction.assistant_message}</p>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
