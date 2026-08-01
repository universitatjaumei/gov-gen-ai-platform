import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import {
  useListSites,
} from '@/shared/api/generated/hub-sites/hub-sites'
import {
  useListSiteFindings,
  useTransitionFinding,
  useAnalyzeSite,
  getListSiteFindingsQueryKey,
} from '@/shared/api/generated/hub-content-quality/hub-content-quality'
import type { SiteView } from '@/shared/api/generated/model'
import { WebQualityReportViewer } from './WebQualityReportViewer'
import { ContentGapsPanel } from './ContentGapsPanel'

type Severity = 'critical' | 'warning' | 'info'

const SEVERITY_BADGE: Record<Severity, string> = {
  critical: 'bg-red-100 text-red-800',
  warning: 'bg-yellow-100 text-yellow-800',
  info: 'bg-blue-100 text-blue-800',
}

export function ContentQualityPage() {
  const { t } = useTranslation('contentQuality')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()

  const [selectedSiteId, setSelectedSiteId] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [showReport, setShowReport] = useState(false)

  const { data: sites = [] } = useListSites()
  const { data: findings = [], isLoading: findingsLoading } = useListSiteFindings(
    selectedSiteId,
    { status: statusFilter || undefined, type: typeFilter || undefined },
    { query: { enabled: !!selectedSiteId } }
  )

  const analyzeMutation = useAnalyzeSite({
    mutation: {
      onSuccess: () => {
        if (selectedSiteId) {
          qc.invalidateQueries({ queryKey: getListSiteFindingsQueryKey(selectedSiteId) })
        }
      },
    },
  })

  const transitionMutation = useTransitionFinding({
    mutation: {
      onSuccess: () => {
        if (selectedSiteId) {
          qc.invalidateQueries({ queryKey: getListSiteFindingsQueryKey(selectedSiteId) })
        }
      },
    },
  })

  const handleTransition = (findingId: string, newStatus: string) => {
    if (!selectedSiteId) return
    transitionMutation.mutate({
      siteId: selectedSiteId,
      findingId,
      data: { new_status: newStatus },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t('quality_title')}</h1>
      </div>

      {/* Site selector + actions */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={selectedSiteId}
          onChange={(e) => { setSelectedSiteId(e.target.value); setShowReport(false) }}
          className="border rounded px-2 py-1.5 text-sm"
          aria-label={t('select_site')}
        >
          <option value="">{t('select_site')}</option>
          {(sites as SiteView[]).map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <button
          className="px-3 py-1.5 rounded border text-sm"
          disabled={!selectedSiteId || analyzeMutation.isPending}
          onClick={() => selectedSiteId && analyzeMutation.mutate({ siteId: selectedSiteId })}
        >
          {t('analyze_now')}
        </button>
        {selectedSiteId && (
          <button
            className="px-3 py-1.5 rounded border text-sm"
            onClick={() => setShowReport(!showReport)}
          >
            {t('report_title')}
          </button>
        )}
      </div>

      {showReport && selectedSiteId && (
        <WebQualityReportViewer siteId={selectedSiteId} />
      )}

      {/* Filters */}
      {selectedSiteId && (
        <div className="flex gap-3 flex-wrap">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border rounded px-2 py-1.5 text-sm"
            aria-label={t('filter_status')}
          >
            <option value="">{t('filter_status')}</option>
            <option value="new">{t('status_new')}</option>
            <option value="confirmed">{t('status_confirmed')}</option>
            <option value="dismissed">{t('status_dismissed')}</option>
            <option value="resolved">{t('status_resolved')}</option>
          </select>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border rounded px-2 py-1.5 text-sm"
            aria-label={t('filter_type')}
          >
            <option value="">{t('filter_type')}</option>
            {['superseded','duplicate','contradiction','empty','thin','stale','crawl_error','orphan_page'].map((ft) => (
              <option key={ft} value={ft}>{t(`type_${ft}` as Parameters<typeof t>[0])}</option>
            ))}
          </select>
        </div>
      )}

      {/* Findings table */}
      {selectedSiteId && (
        findingsLoading ? (
          <p className="text-muted-foreground">{tc('loading')}</p>
        ) : (findings as { id: string; finding_type: string; severity: string; status: string; source_url?: string; detected_at: string }[]).length === 0 ? (
          <p className="text-muted-foreground">{t('no_findings')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse" aria-label={t('findings_title')}>
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-3">{t('finding_type')}</th>
                  <th className="py-2 pr-3">{t('finding_severity')}</th>
                  <th className="py-2 pr-3">{t('finding_status')}</th>
                  <th className="py-2 pr-3">{t('finding_url')}</th>
                  <th className="py-2 pr-3">{t('finding_detected')}</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {(findings as { id: string; finding_type: string; severity: Severity; status: string; source_url?: string | null; detected_at: string }[]).map((f) => (
                  <tr key={f.id} className="border-b">
                    <td className="py-2 pr-3">
                      <span className="text-xs">{t(`type_${f.finding_type}` as Parameters<typeof t>[0])}</span>
                    </td>
                    <td className="py-2 pr-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${SEVERITY_BADGE[f.severity] ?? ''}`}>
                        {t(`severity_${f.severity}` as Parameters<typeof t>[0])}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-xs">{t(`status_${f.status}` as Parameters<typeof t>[0])}</td>
                    <td className="py-2 pr-3 text-xs truncate max-w-xs">{f.source_url ?? '—'}</td>
                    <td className="py-2 pr-3 text-xs">{new Date(f.detected_at).toLocaleDateString()}</td>
                    <td className="py-2 space-x-1">
                      {f.status === 'new' && (
                        <>
                          <button className="text-xs px-1.5 py-0.5 rounded border" onClick={() => handleTransition(f.id, 'confirmed')}>{t('confirm')}</button>
                          <button className="text-xs px-1.5 py-0.5 rounded border" onClick={() => handleTransition(f.id, 'dismissed')}>{t('dismiss')}</button>
                        </>
                      )}
                      {f.status === 'confirmed' && (
                        <button className="text-xs px-1.5 py-0.5 rounded border" onClick={() => handleTransition(f.id, 'resolved')}>{t('resolve')}</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
      {/* RAG.14: los huecos de corpus son la misma tarea de revisión, pero su sujeto es un
          chatbot y no un sitio, así que van en su propio panel con su propio selector. */}
      <ContentGapsPanel />
    </div>
  )
}
