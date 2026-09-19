import { Fragment, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useListSiteRuns } from '@/shared/api/generated/hub-sites/hub-sites'
import type { CrawlRunView } from '@/shared/api/generated/model'

/**
 * DIN.6 — el diario de la automatización, donde trabaja el curador.
 *
 * Con DIN.4 y DIN.5 detrás, esta tabla es el único sitio donde se ve que la salvaguarda paró una
 * retirada entera o que la puerta de calidad dejó cinco páginas fuera. La confianza en una
 * automatización se construye pudiendo auditarla barata: si quien cura no ve lo que hizo, la
 * apagará al primer susto — y tendrá razón.
 *
 * El ámbito de cada pasada va **bien visible** y en texto (`scope_label`, que el servidor
 * conserva aunque la sección se borre): una tabla de pasadas que no diga qué cubrió cada una no
 * se puede leer.
 */
const POR_PAGINA = 10

export function RunsPanel({
  siteId,
  sectionId,
}: {
  siteId: string
  sectionId?: string
}) {
  const { t } = useTranslation('curation')
  const { t: tc } = useTranslation('common')
  const [page, setPage] = useState(1)
  const [desplegada, setDesplegada] = useState<string | null>(null)

  const { data, isLoading } = useListSiteRuns(siteId, {
    section_id: sectionId,
    page,
    size: POR_PAGINA,
  })
  const pasadas = (data?.items ?? []) as CrawlRunView[]
  const total = data?.total ?? 0
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA))

  if (isLoading) return <p className="text-xs text-muted-foreground">{tc('loading')}</p>

  return (
    <div className="space-y-2" data-testid={`diario-${siteId}`}>
      <h3 className="text-sm font-semibold">{t('runs_title')}</h3>
      {pasadas.length === 0 ? (
        <p className="text-xs text-muted-foreground" data-testid="sin-pasadas">
          {t('no_runs')}
        </p>
      ) : (
        <>
          <table className="w-full text-xs border-collapse" aria-label={t('runs_title')}>
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-1 pr-3">{t('run_scope')}</th>
                <th className="py-1 pr-3">{t('run_when')}</th>
                <th className="py-1 pr-3">{t('run_new')}</th>
                <th className="py-1 pr-3">{t('run_reingested')}</th>
                <th className="py-1 pr-3">{t('run_retired')}</th>
                <th className="py-1 pr-3">{t('run_blocked')}</th>
                <th className="py-1 pr-3">{t('run_gone')}</th>
                <th className="py-1" />
              </tr>
            </thead>
            <tbody>
              {pasadas.map((pasada) => {
                // `pages_error` cuenta aquí: al verificar el diario, una pasada con una página
                // que no se pudo descargar no ofrecía detalle y no decía nada de ella — y «una
                // página falló» es la pregunta más común de quien mira el diario.
                const detalle =
                  (pasada.errors ?? []).length > 0 ||
                  pasada.pages_blocked_by_findings > 0 ||
                  pasada.pages_error > 0 ||
                  pasada.truncated
                return (
                  // La clave va en el fragmento y no en el `<tr>`: con dos filas por pasada
                  // —la fila y su detalle— React pide la clave en el elemento que envuelve a
                  // las dos, y ponerla dentro deja un error en consola en cada render.
                  <Fragment key={pasada.id}>
                    <tr
                      className="border-b"
                      data-testid={`pasada-${pasada.id}`}
                      data-ambito={pasada.scope_label}
                    >
                      <td className="py-1 pr-3 font-medium">{pasada.scope_label}</td>
                      <td className="py-1 pr-3">
                        {new Date(pasada.started_at).toLocaleString()}
                      </td>
                      <td className="py-1 pr-3">{pasada.documents_auto_ingested}</td>
                      <td className="py-1 pr-3">{pasada.documents_reingested}</td>
                      <td className="py-1 pr-3">{pasada.documents_auto_retired}</td>
                      <td className="py-1 pr-3">{pasada.pages_blocked_by_findings}</td>
                      <td className="py-1 pr-3">{pasada.pages_gone}</td>
                      <td className="py-1">
                        {detalle && (
                          <button
                            type="button"
                            className="px-2 py-0.5 rounded border"
                            data-testid={`detalle-${pasada.id}`}
                            aria-expanded={desplegada === pasada.id}
                            onClick={() =>
                              setDesplegada((abierta) =>
                                abierta === pasada.id ? null : pasada.id,
                              )
                            }
                          >
                            {t('run_detail')}
                          </button>
                        )}
                      </td>
                    </tr>
                    {desplegada === pasada.id && (
                      <tr className="border-b bg-accent/10">
                        <td colSpan={8} className="py-2 px-2 space-y-1">
                          {/* RAS.1 — «cero bajas» y «no se han comprobado las bajas» son dos
                              noticias distintas, y aquí es donde se distinguen. */}
                          {pasada.truncated && (
                            <p data-testid={`truncada-${pasada.id}`}>
                              {t('run_truncated', {
                                motivo: pasada.stop_reason ?? '—',
                              })}
                            </p>
                          )}
                          {pasada.pages_blocked_by_findings > 0 && (
                            <p>
                              {t('run_blocked_detail', {
                                cuantas: pasada.pages_blocked_by_findings,
                              })}
                            </p>
                          )}
                          {pasada.pages_error > 0 && (
                            <p data-testid={`errores-de-pagina-${pasada.id}`}>
                              {t('run_page_errors', { cuantas: pasada.pages_error })}
                            </p>
                          )}
                          {(pasada.errors ?? []).length > 0 && (
                            <ul className="font-mono text-destructive">
                              {(pasada.errors ?? []).map((error, i) => (
                                <li key={i}>{error}</li>
                              ))}
                            </ul>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>

          {paginas > 1 && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="px-2 py-0.5 rounded border disabled:opacity-50"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                {tc('back')}
              </button>
              <span data-testid="pagina-del-diario">
                {t('runs_page', { page, paginas })}
              </span>
              <button
                type="button"
                className="px-2 py-0.5 rounded border disabled:opacity-50"
                data-testid="siguiente-pagina"
                disabled={page >= paginas}
                onClick={() => setPage((p) => p + 1)}
              >
                {tc('continue')}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
