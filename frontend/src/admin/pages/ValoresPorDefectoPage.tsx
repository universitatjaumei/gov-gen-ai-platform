import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useListOrganizacionesApiV1HubOrganizacionesGet } from '@/shared/api/generated/hub-organizaciones/hub-organizaciones'
import {
  useGetValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoGet as useValores,
  useUpdateValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoPatch as useGuardarValores,
  getGetValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoGetQueryKey as claveDeValores,
} from '@/shared/api/generated/hub-organizaciones/hub-organizaciones'

/** Los campos que pueden volver a «heredar el defecto de plataforma» valiendo `null`. */
const HEREDABLES = [
  'default_context_token_budget',
  'default_chunk_size',
  'default_chunk_overlap',
  'default_chunking_strategy',
  'default_query_rewriting_enabled',
] as const

/**
 * Los valores por defecto de RAG de una organización (PLAT.3).
 *
 * Vivían dentro de la pantalla de Organizaciones, y por eso esa pantalla acabó bajo el módulo
 * Chatbots: la mayoría de sus campos eran de Chatbots. Aquí están donde pertenecen —el perfil de
 * grafo, el modo de recuperación, el troceado o el reranker no dicen nada de quién es el
 * inquilino— con selector de organización, porque son configuración **del módulo** aplicada a
 * una organización.
 *
 * **Y se puede volver a heredar.** Seis de estos campos usan `null` con el significado «usa el
 * defecto de la plataforma», y hasta PLAT.3 el `PATCH` descartaba el `null` explícito
 * (`exclude_none`), así que una vez fijado un valor propio no había vuelta atrás por API. El
 * botón de cada campo heredable manda ese `null`.
 */
export function ValoresPorDefectoPage() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()

  const { data: organizaciones = [] } = useListOrganizacionesApiV1HubOrganizacionesGet()
  const [organizacionId, setOrganizacionId] = useState('')

  useEffect(() => {
    if (!organizacionId && organizaciones.length > 0) {
      setOrganizacionId(String(organizaciones[0].id))
    }
  }, [organizaciones, organizacionId])

  const { data: valores, isLoading } = useValores(organizacionId, {
    query: { enabled: Boolean(organizacionId) },
  })
  const { mutate: guardar, isPending } = useGuardarValores()

  function cambiar(campo: string, valor: unknown) {
    guardar(
      { organizacionId, data: { [campo]: valor } },
      {
        onSuccess: () =>
          void qc.invalidateQueries({ queryKey: claveDeValores(organizacionId) }),
      }
    )
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold">{t('hub.valores_por_defecto.titulo')}</h2>
        <p className="text-sm text-muted-foreground">{t('hub.valores_por_defecto.alcance')}</p>
      </header>

      <div className="flex flex-col gap-1 max-w-sm">
        <label htmlFor="vpd_organizacion" className="text-sm font-medium">
          {t('hub.valores_por_defecto.organizacion')}
        </label>
        <select
          id="vpd_organizacion"
          value={organizacionId}
          onChange={(e) => setOrganizacionId(e.target.value)}
          className="rounded-md border px-2 py-1.5 text-sm bg-background"
        >
          {organizaciones.map((o) => (
            <option key={o.id} value={String(o.id)}>
              {o.name}
            </option>
          ))}
        </select>
      </div>

      {isLoading || !valores ? (
        <p>{tc('loading')}</p>
      ) : (
        <div className="space-y-3">
          {Object.entries(valores).map(([campo, valor]) => {
            const heredable = (HEREDABLES as readonly string[]).includes(campo)
            const heredado = valor === null
            return (
              <div
                key={campo}
                data-testid={campo}
                className="flex flex-wrap items-center gap-3 rounded-md border p-3 text-sm"
              >
                {/* La etiqueta traducida, con el nombre tecnico como reserva: si el
                    contrato crece con un campo nuevo, la fila aparece igual —con su nombre
                    crudo— en vez de quedarse vacia o reventar. */}
                <span className="w-72 shrink-0">
                  {t(`hub.valores_por_defecto.campos.${campo}` as Parameters<typeof t>[0], {
                    defaultValue: campo,
                  })}
                </span>
                <span className="flex-1">
                  {/* «Heredado» y no una celda vacía: `null` aquí es una decisión, no un dato
                      que falte, y confundirlas es lo que hace que nadie se atreva a tocarlo. */}
                  {heredado ? (
                    <em className="text-muted-foreground">
                      {t('hub.valores_por_defecto.heredado')}
                    </em>
                  ) : (
                    String(valor)
                  )}
                </span>
                {heredable && !heredado && (
                  <button
                    type="button"
                    disabled={isPending}
                    onClick={() => cambiar(campo, null)}
                    className="text-xs underline disabled:opacity-50"
                  >
                    {t('hub.valores_por_defecto.volver_a_heredar')}
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
