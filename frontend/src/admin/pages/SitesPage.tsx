import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  useListSites,
  useCreateSite,
  useDeleteSite,
  useTriggerSiteCrawl,
  getListSitesQueryKey,
} from '@/shared/api/generated/hub-sites/hub-sites'
import type { SiteView } from '@/shared/api/generated/model'
import { SiteMappingPanel } from './SiteMappingPanel'

const siteSchema = z.object({
  name: z.string().min(1),
  root_url: z.string().url(),
  sitemap_url: z.string().url().optional().or(z.literal('')),
  crawl_interval_hours: z.coerce.number().int().min(1).default(24),
  audit_semantic_scope: z.enum(['ingested', 'full']).default('ingested'),
})

type SiteFormInput = z.input<typeof siteSchema>
type SiteFormValues = z.output<typeof siteSchema>

export function SitesPage() {
  const { t } = useTranslation('contentQuality')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedSite, setSelectedSite] = useState<SiteView | null>(null)

  const { data: sites = [], isLoading } = useListSites()
  const createMutation = useCreateSite({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: getListSitesQueryKey() })
        setDialogOpen(false)
        reset()
      },
    },
  })
  const deleteMutation = useDeleteSite()
  const crawlMutation = useTriggerSiteCrawl()

  const { register, handleSubmit, reset, formState: { errors } } = useForm<SiteFormInput, unknown, SiteFormValues>({
    resolver: zodResolver(siteSchema),
    defaultValues: { crawl_interval_hours: 24, audit_semantic_scope: 'ingested' },
  })

  const onSubmit = (data: SiteFormValues) => {
    createMutation.mutate({
      data: {
        name: data.name,
        root_url: data.root_url,
        sitemap_url: data.sitemap_url || undefined,
        crawl_interval_hours: data.crawl_interval_hours,
        audit_semantic_scope: data.audit_semantic_scope,
      },
    })
  }

  const handleCrawl = (siteId: string) => {
    crawlMutation.mutate({ siteId })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t('sites_title')}</h1>
        <button
          className="px-3 py-1.5 rounded bg-primary text-primary-foreground text-sm"
          onClick={() => setDialogOpen(true)}
        >
          {t('new_site')}
        </button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">{tc('loading')}</p>
      ) : sites.length === 0 ? (
        <p className="text-muted-foreground">{t('no_sites')}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse" aria-label={t('sites_title')}>
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4">{t('site_name')}</th>
                <th className="py-2 pr-4">{t('site_root_url')}</th>
                <th className="py-2 pr-4">{t('site_last_crawled')}</th>
                <th className="py-2 pr-4">{t('site_status')}</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {(sites as SiteView[]).map((site) => (
                <tr
                  key={site.id}
                  className={`border-b cursor-pointer hover:bg-accent/30 ${selectedSite?.id === site.id ? 'bg-accent/50' : ''}`}
                  onClick={() => setSelectedSite(selectedSite?.id === site.id ? null : site)}
                >
                  <td className="py-2 pr-4 font-medium">{site.name}</td>
                  <td className="py-2 pr-4 text-xs text-muted-foreground truncate max-w-xs">{site.root_url}</td>
                  <td className="py-2 pr-4 text-xs">
                    {site.last_crawled_at
                      ? new Date(site.last_crawled_at).toLocaleString()
                      : t('site_never_crawled')}
                  </td>
                  <td className="py-2 pr-4">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${site.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {site.status}
                    </span>
                  </td>
                  <td className="py-2 space-x-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      className="text-xs px-2 py-1 rounded border hover:bg-accent"
                      onClick={() => handleCrawl(site.id)}
                      aria-label={t('crawl_now')}
                    >
                      {t('crawl_now')}
                    </button>
                    <button
                      className="text-xs px-2 py-1 rounded border text-destructive hover:bg-destructive/10"
                      onClick={() => deleteMutation.mutate({ siteId: site.id })}
                      aria-label={tc('delete')}
                    >
                      {tc('delete')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedSite && (
        <SiteMappingPanel siteId={selectedSite.id} siteName={selectedSite.name} />
      )}

      {dialogOpen && (
        <div role="dialog" aria-modal="true" aria-label={t('new_site')} className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-background rounded-lg shadow-lg p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold">{t('new_site')}</h2>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate>
              <div>
                <label className="text-sm font-medium">{t('site_name')}</label>
                <input {...register('name')} className="w-full border rounded px-2 py-1.5 text-sm mt-1" />
                {errors.name && <p className="text-xs text-destructive mt-0.5">{tc('required')}</p>}
              </div>
              <div>
                <label className="text-sm font-medium">{t('site_root_url')}</label>
                <input {...register('root_url')} className="w-full border rounded px-2 py-1.5 text-sm mt-1" type="url" />
                {errors.root_url && <p className="text-xs text-destructive mt-0.5">{tc('invalid_url')}</p>}
              </div>
              <div>
                <label className="text-sm font-medium">{t('site_sitemap_url')}</label>
                <input {...register('sitemap_url')} className="w-full border rounded px-2 py-1.5 text-sm mt-1" type="url" />
              </div>
              <div>
                <label className="text-sm font-medium">{t('site_interval')}</label>
                <input {...register('crawl_interval_hours')} type="number" min={1} className="w-full border rounded px-2 py-1.5 text-sm mt-1" />
              </div>
              <div>
                <label className="text-sm font-medium">{t('site_audit_scope')}</label>
                <select {...register('audit_semantic_scope')} className="w-full border rounded px-2 py-1.5 text-sm mt-1">
                  <option value="ingested">{t('scope_ingested')}</option>
                  <option value="full">{t('scope_full')}</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => { setDialogOpen(false); reset() }} className="px-3 py-1.5 rounded border text-sm">{tc('cancel')}</button>
                <button type="submit" disabled={createMutation.isPending} className="px-3 py-1.5 rounded bg-primary text-primary-foreground text-sm">{tc('save')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
