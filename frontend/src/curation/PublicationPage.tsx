import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  useListSites,
  useListSelections,
  useCreateSelection,
  useDeleteSelection,
  useListCandidates,
  useIngestPage,
  getListSelectionsQueryKey,
} from '@/shared/api/generated/hub-sites/hub-sites'
import type { CandidatePageView, SiteView } from '@/shared/api/generated/model'
import { useListChatbotsApiV1HubChatbotsGet } from '@/shared/api/generated/hub-chatbots/hub-chatbots'

const selSchema = z.object({
  rule_type: z.enum(['path_prefix', 'sitemap_section', 'manual']).default('path_prefix'),
  rule_value: z.string().optional(),
  auto_ingest_new: z.boolean().default(true),
})

type SelFormInput = z.input<typeof selSchema>
type SelFormValues = z.output<typeof selSchema>

/**
 * El paso de publicación (CUR.2): decidir qué página entra al corpus de qué chatbot.
 *
 * `docs/DECISION_CURACION_SEPARADA.md`: `CorpusSelectionService` es el punto exacto donde la
 * materia prima se convierte en corpus, y antes de CUR.2 estaba enterrado como un panel que
 * sólo aparecía al pulsar una fila de `SitesPage`. Aquí es una página propia con su propio
 * selector de sitio: la publicación no es un detalle de gestionar sitios, es la decisión que
 * importa.
 *
 * Cada página candidata se ingiere con su propio botón — no hay «ingerir todo el sitio». Eso
 * es a propósito: automatizarlo sería devolver la promesa de ingesta automática que
 * `docs/DECISION_CURACION_SEPARADA.md` retira explícitamente.
 */
export function PublicationPage() {
  const { t } = useTranslation('curation')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [selDialogOpen, setSelDialogOpen] = useState(false)
  const [selectedSiteId, setSelectedSiteId] = useState<string>('')
  const [selectedChatbotId, setSelectedChatbotId] = useState<string>('')

  const { data: sites = [] } = useListSites()
  const { data: chatbots = [] } = useListChatbotsApiV1HubChatbotsGet()
  const { data: selections = [] } = useListSelections(selectedChatbotId, {
    query: { enabled: !!selectedChatbotId },
  })
  const { data: candidates = [] } = useListCandidates(
    selectedSiteId,
    { chatbot_id: selectedChatbotId },
    { query: { enabled: !!selectedSiteId && !!selectedChatbotId } },
  )

  const createSelMutation = useCreateSelection({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: getListSelectionsQueryKey(selectedChatbotId) })
        setSelDialogOpen(false)
        reset()
      },
    },
  })
  const deleteSelMutation = useDeleteSelection()
  const ingestMutation = useIngestPage()

  const { register, handleSubmit, reset } = useForm<SelFormInput, unknown, SelFormValues>({
    resolver: zodResolver(selSchema),
    defaultValues: { rule_type: 'path_prefix', auto_ingest_new: true },
  })

  const onSubmit = (data: SelFormValues) => {
    if (!selectedChatbotId || !selectedSiteId) return
    createSelMutation.mutate({
      chatbotId: selectedChatbotId,
      data: {
        site_id: selectedSiteId,
        rule_type: data.rule_type,
        rule_value: data.rule_value,
        auto_ingest_new: data.auto_ingest_new,
      },
    })
  }

  const handleIngest = (pageId: string) => {
    if (!selectedChatbotId) return
    ingestMutation.mutate({ chatbotId: selectedChatbotId, pageId })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{t('publish_title')}</h1>
        <p className="text-sm text-muted-foreground">{t('publish_desc')}</p>
      </div>

      {/* Selectores de sitio y chatbot destino */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={selectedSiteId}
          onChange={(e) => setSelectedSiteId(e.target.value)}
          className="border rounded px-2 py-1.5 text-sm"
          aria-label={t('select_site')}
        >
          <option value="">{t('select_site')}</option>
          {(sites as SiteView[]).map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <select
          value={selectedChatbotId}
          onChange={(e) => setSelectedChatbotId(e.target.value)}
          className="border rounded px-2 py-1.5 text-sm"
          aria-label={t('candidates_chatbot')}
        >
          <option value="">{t('candidates_chatbot')}</option>
          {(chatbots as { id: string; name: string }[]).map((cb) => (
            <option key={cb.id} value={cb.id}>{cb.name}</option>
          ))}
        </select>
      </div>

      {selectedSiteId && selectedChatbotId && (
        <>
          {/* Selections */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold">{t('selections_title')}</h3>
              <button
                className="text-xs px-2 py-1 rounded border"
                onClick={() => setSelDialogOpen(true)}
              >
                {t('new_selection')}
              </button>
            </div>
            {selections.length === 0 ? (
              <p className="text-xs text-muted-foreground">{t('no_selections')}</p>
            ) : (
              <ul className="text-sm space-y-1">
                {(selections as { id: string; rule_type: string; rule_value?: string | null; auto_ingest_new: boolean }[]).map((sel) => (
                  <li key={sel.id} className="flex items-center gap-2">
                    <span className="text-xs bg-accent px-1.5 py-0.5 rounded">{sel.rule_type}</span>
                    <span className="flex-1 truncate">{sel.rule_value ?? '—'}</span>
                    {sel.auto_ingest_new && <span className="text-xs text-green-600">{t('sel_auto_ingest')}</span>}
                    <button
                      className="text-xs text-destructive hover:underline"
                      onClick={() => deleteSelMutation.mutate({ chatbotId: selectedChatbotId, selectionId: sel.id })}
                    >
                      {tc('delete')}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Candidates: cada fila publica por su cuenta, sin acción masiva */}
          <section>
            <h3 className="text-sm font-semibold mb-2">{t('candidates_title')}</h3>
            {(candidates as CandidatePageView[]).length === 0 ? (
              <p className="text-xs text-muted-foreground">{t('no_candidates')}</p>
            ) : (
              <table className="w-full text-xs border-collapse" aria-label={t('candidates_title')}>
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-1 pr-2">{t('candidate_url')}</th>
                    <th className="py-1 pr-2">{t('candidate_matched_rule')}</th>
                    <th className="py-1 pr-2">{t('candidate_is_new')}</th>
                    <th className="py-1" />
                  </tr>
                </thead>
                <tbody>
                  {(candidates as CandidatePageView[]).map((c) => (
                    <tr key={String(c.page_id)} className="border-b">
                      <td className="py-1 pr-2 truncate max-w-xs">{c.url}</td>
                      <td className="py-1 pr-2">{c.matched_rule ?? '—'}</td>
                      <td className="py-1 pr-2">{c.is_new ? '✓' : '—'}</td>
                      <td className="py-1">
                        <button
                          className="px-2 py-0.5 rounded border text-xs"
                          onClick={() => handleIngest(String(c.page_id))}
                          disabled={ingestMutation.isPending}
                        >
                          {t('ingest')}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}

      {/* Selection dialog */}
      {selDialogOpen && (
        <div role="dialog" aria-modal="true" aria-label={t('new_selection')} className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-background rounded-lg shadow-lg p-6 w-full max-w-sm space-y-4">
            <h2 className="text-base font-semibold">{t('new_selection')}</h2>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate>
              <div>
                <label className="text-sm font-medium">{t('sel_rule_type')}</label>
                <select {...register('rule_type')} className="w-full border rounded px-2 py-1.5 text-sm mt-1">
                  <option value="path_prefix">{t('sel_rule_path_prefix')}</option>
                  <option value="sitemap_section">{t('sel_rule_sitemap_section')}</option>
                  <option value="manual">{t('sel_rule_manual')}</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">{t('sel_rule_value')}</label>
                <input {...register('rule_value')} className="w-full border rounded px-2 py-1.5 text-sm mt-1" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" {...register('auto_ingest_new')} id="auto_ingest" />
                <label htmlFor="auto_ingest" className="text-sm">{t('sel_auto_ingest')}</label>
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => { setSelDialogOpen(false); reset() }} className="px-3 py-1.5 rounded border text-sm">{tc('cancel')}</button>
                <button type="submit" disabled={createSelMutation.isPending} className="px-3 py-1.5 rounded bg-primary text-primary-foreground text-sm">{tc('save')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
