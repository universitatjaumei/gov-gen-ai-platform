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

const siteSchema = z.object({
  name: z.string().min(1),
  root_url: z.string().url(),
  sitemap_url: z.string().url().optional().or(z.literal('')),
  crawl_interval_hours: z.coerce.number().int().min(1).default(24),
  audit_semantic_scope: z.enum(['ingested', 'full']).default('ingested'),
  // RAS.5 — el rastreo se acota por apartado, que es como tiene sentido usarlo: cada apartado
  // del portal tiene un responsable distinto y un informe del portal completo no lo lee nadie.
  // El spider ya leía esto; lo que no había era forma de fijarlo desde ninguna pantalla.
  url_regex_filter: z
    .string()
    .optional()
    .refine(
      (valor) => {
        if (!valor) return true
        try {
          new RegExp(valor)
          return true
        } catch {
          return false
        }
      },
      { message: 'regex' },
    ),
  crawl_depth: z.coerce.number().int().min(0).max(10).default(1),
  max_pages: z.coerce.number().int().min(1).max(100000).default(50),
  // La cortesía viene puesta: rastrear despacio y respetar robots.txt es el defecto, y quitarlo
  // exige decirlo aquí, donde queda a la vista de quien da de alta el apartado.
  delay_seconds: z.coerce.number().min(0).max(60).default(1),
  respect_robots: z.boolean().default(true),
  // CUR.1 — de dónde saca este portal la fecha que publica cada página. En `www.uji.es` está en
  // `.clockBarDate`, con la unidad responsable al lado. Sin esto, «desactualizada» se adivina.
  content_date_selector: z.string().optional(),
  content_date_format: z.string().default('%d/%m/%Y'),
  // CUR.2.1 — los criterios de juicio son de cada sitio, y por tanto de cada organización: un
  // portal de normativa y uno de noticias no envejecen igual, y donde uno publica series vigentes
  // otro versiona convocatorias. Estaban en el código.
  stale_days: z.coerce.number().int().min(1).max(36500).default(365),
  thin_min_tokens: z.coerce.number().int().min(0).max(100000).default(120),
  version_series_policy: z.enum(['series', 'superseded', 'off']).default('series'),
})

type SiteFormInput = z.input<typeof siteSchema>
type SiteFormValues = z.output<typeof siteSchema>

export function SitesPage() {
  const { t } = useTranslation('curation')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)

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
  const deleteMutation = useDeleteSite({
    mutation: {
      onSuccess: () => qc.invalidateQueries({ queryKey: getListSitesQueryKey() }),
    },
  })
  const crawlMutation = useTriggerSiteCrawl()

  const { register, handleSubmit, reset, formState: { errors } } = useForm<SiteFormInput, unknown, SiteFormValues>({
    resolver: zodResolver(siteSchema),
    defaultValues: {
      crawl_interval_hours: 24,
      audit_semantic_scope: 'ingested',
      crawl_depth: 1,
      max_pages: 50,
      delay_seconds: 1,
      respect_robots: true,
      content_date_format: '%d/%m/%Y',
      stale_days: 365,
      thin_min_tokens: 120,
      version_series_policy: 'series',
    },
  })

  const onSubmit = (data: SiteFormValues) => {
    createMutation.mutate({
      data: {
        name: data.name,
        root_url: data.root_url,
        sitemap_url: data.sitemap_url || undefined,
        crawl_interval_hours: data.crawl_interval_hours,
        audit_semantic_scope: data.audit_semantic_scope,
        crawl_config: {
          url_regex_filter: data.url_regex_filter || undefined,
          crawl_depth: data.crawl_depth,
          max_pages: data.max_pages,
          delay_seconds: data.delay_seconds,
          respect_robots: data.respect_robots,
          content_date_selector: data.content_date_selector || undefined,
          content_date_format: data.content_date_format,
          stale_days: data.stale_days,
          thin_min_tokens: data.thin_min_tokens,
          version_series_policy: data.version_series_policy,
        },
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
          data-testid="btn-nuevo-sitio"
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
                <tr key={site.id} className="border-b hover:bg-accent/30">
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
                  <td className="py-2 space-x-2">
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

      {dialogOpen && (
        <div role="dialog" aria-modal="true" aria-label={t('new_site')} className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-background rounded-lg shadow-lg p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold">{t('new_site')}</h2>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate data-testid="form-sitio">
              <div>
                <label className="text-sm font-medium">{t('site_name')}</label>
                <input {...register('name')} data-testid="campo-nombre" className="w-full border rounded px-2 py-1.5 text-sm mt-1" />
                {errors.name && <p className="text-xs text-destructive mt-0.5">{tc('required')}</p>}
              </div>
              <div>
                <label className="text-sm font-medium">{t('site_root_url')}</label>
                <input {...register('root_url')} data-testid="campo-url" className="w-full border rounded px-2 py-1.5 text-sm mt-1" type="url" />
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
              {/* El apartado y la cortesía: lo que convierte «rastrear un portal» en «rastrear
                  este apartado, despacio y por donde el servidor deja». */}
              <fieldset className="border-t pt-3 space-y-3">
                <legend className="text-sm font-medium">{t('site_crawl_section')}</legend>
                <div>
                  <label className="text-sm font-medium" htmlFor="url_regex_filter">
                    {t('site_url_filter')}
                  </label>
                  <input
                    {...register('url_regex_filter')}
                    id="url_regex_filter"
                    data-testid="campo-url-regex"
                    placeholder="/centres/escola-doctorat/"
                    className="w-full border rounded px-2 py-1.5 text-sm mt-1 font-mono"
                  />
                  <p className="text-xs text-muted-foreground mt-0.5">{t('site_url_filter_help')}</p>
                  {errors.url_regex_filter && (
                    <p data-testid="error-url-regex" className="text-xs text-destructive mt-0.5">
                      {t('site_url_filter_invalid')}
                    </p>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-sm font-medium" htmlFor="crawl_depth">
                      {t('site_depth')}
                    </label>
                    <input {...register('crawl_depth')} id="crawl_depth" data-testid="campo-profundidad" type="number" min={0} max={10} className="w-full border rounded px-2 py-1.5 text-sm mt-1" />
                  </div>
                  <div>
                    <label className="text-sm font-medium" htmlFor="max_pages">
                      {t('site_max_pages')}
                    </label>
                    <input {...register('max_pages')} id="max_pages" data-testid="campo-max-paginas" type="number" min={1} className="w-full border rounded px-2 py-1.5 text-sm mt-1" />
                  </div>
                  <div>
                    <label className="text-sm font-medium" htmlFor="delay_seconds">
                      {t('site_delay')}
                    </label>
                    <input {...register('delay_seconds')} id="delay_seconds" data-testid="campo-pausa" type="number" min={0} step={0.5} className="w-full border rounded px-2 py-1.5 text-sm mt-1" />
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <input {...register('respect_robots')} data-testid="campo-robots" type="checkbox" />
                  {t('site_respect_robots')}
                </label>
                {/* CUR.1 — la fecha que el propio portal publica en cada página. Con ella,
                    «desactualizada» es un dato; sin ella se adivina por el año de la URL. */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-sm font-medium" htmlFor="content_date_selector">
                      {t('site_date_selector')}
                    </label>
                    <input
                      {...register('content_date_selector')}
                      id="content_date_selector"
                      data-testid="campo-selector-fecha"
                      placeholder=".clockBarDate"
                      className="w-full border rounded px-2 py-1.5 text-sm mt-1 font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium" htmlFor="content_date_format">
                      {t('site_date_format')}
                    </label>
                    <input
                      {...register('content_date_format')}
                      id="content_date_format"
                      data-testid="campo-formato-fecha"
                      className="w-full border rounded px-2 py-1.5 text-sm mt-1 font-mono"
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">{t('site_date_help')}</p>
              </fieldset>

              {/* CUR.2.1 — los criterios con los que se juzga el contenido de ESTE sitio. Vivían en
                  el código, así que todas las organizaciones compartían el mismo. */}
              <fieldset className="border-t pt-3 space-y-3">
                <legend className="text-sm font-medium">{t('site_criteria_section')}</legend>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-sm font-medium" htmlFor="stale_days">
                      {t('site_stale_days')}
                    </label>
                    <input {...register('stale_days')} id="stale_days" data-testid="campo-antiguedad" type="number" min={1} className="w-full border rounded px-2 py-1.5 text-sm mt-1" />
                  </div>
                  <div>
                    <label className="text-sm font-medium" htmlFor="thin_min_tokens">
                      {t('site_thin_tokens')}
                    </label>
                    <input {...register('thin_min_tokens')} id="thin_min_tokens" data-testid="campo-pobreza" type="number" min={0} className="w-full border rounded px-2 py-1.5 text-sm mt-1" />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium" htmlFor="version_series_policy">
                    {t('site_series_policy')}
                  </label>
                  <select {...register('version_series_policy')} id="version_series_policy" data-testid="campo-politica-series" className="w-full border rounded px-2 py-1.5 text-sm mt-1">
                    <option value="series">{t('series_policy_series')}</option>
                    <option value="superseded">{t('series_policy_superseded')}</option>
                    <option value="off">{t('series_policy_off')}</option>
                  </select>
                  <p className="text-xs text-muted-foreground mt-0.5">{t('site_series_help')}</p>
                </div>
                <p className="text-xs text-muted-foreground">{t('site_courtesy_help')}</p>
              </fieldset>

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
