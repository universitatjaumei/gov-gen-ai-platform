import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  useListOrganizacionesApiV1HubOrganizacionesGet,
  useCreateOrganizacionApiV1HubOrganizacionesPost,
  useUpdateOrganizacionApiV1HubOrganizacionesOrganizacionIdPatch,
  useDeleteOrganizacionApiV1HubOrganizacionesOrganizacionIdDelete,
  getListOrganizacionesApiV1HubOrganizacionesGetQueryKey,
} from '@/shared/api/generated/hub-organizaciones/hub-organizaciones'
import type { OrganizacionRead } from '@/shared/api/generated/model'

const schema = z.object({
  name: z.string().min(1),
  partner_id: z.string().min(1),
  theme_config: z.string(),
  is_active: z.boolean(),
  default_public_graph_profile: z.string(),
  default_retrieval_mode: z.enum(['RAG', 'MD_LONG_CONTEXT', 'MD_AGENT_SELECTOR']),
  default_language_mode: z.string(),
  default_quality_threshold: z.number().min(0).max(1),
  default_min_retrieval_results: z.number().int().min(1).max(20),
  default_min_retrieval_score: z.number().min(0).max(1),
  default_reranker_enabled: z.boolean(),
  default_answer_template: z.string(),
})
type FormValues = z.infer<typeof schema>

export function OrganizacionesPage() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [editing, setEditing] = useState<OrganizacionRead | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<OrganizacionRead | null>(null)
  const [deleteError, setDeleteError] = useState('')
  const [filter, setFilter] = useState('')
  const [defaultsOpen, setDefaultsOpen] = useState(false)

  const listQueryKey = getListOrganizacionesApiV1HubOrganizacionesGetQueryKey()
  const invalidateList = () => qc.invalidateQueries({ queryKey: listQueryKey })

  const { data: organizaciones = [], isLoading } = useListOrganizacionesApiV1HubOrganizacionesGet()

  const toBody = (values: FormValues) => ({
    name: values.name,
    partner_id: values.partner_id,
    theme_config: parseJson(values.theme_config),
    is_active: values.is_active,
    default_public_graph_profile: values.default_public_graph_profile,
    default_retrieval_mode: values.default_retrieval_mode,
    default_language_mode: values.default_language_mode,
    default_quality_threshold: values.default_quality_threshold,
    default_min_retrieval_results: values.default_min_retrieval_results,
    default_min_retrieval_score: values.default_min_retrieval_score,
    default_reranker_enabled: values.default_reranker_enabled,
    default_answer_template: values.default_answer_template,
  })

  const createMutation = useCreateOrganizacionApiV1HubOrganizacionesPost({
    mutation: { onSuccess: () => { invalidateList(); closeDialog() } },
  })

  const updateMutation = useUpdateOrganizacionApiV1HubOrganizacionesOrganizacionIdPatch({
    mutation: { onSuccess: () => { invalidateList(); closeDialog() } },
  })

  const toggleMutation = useUpdateOrganizacionApiV1HubOrganizacionesOrganizacionIdPatch({
    mutation: { onSuccess: invalidateList },
  })

  const deleteMutation = useDeleteOrganizacionApiV1HubOrganizacionesOrganizacionIdDelete({
    mutation: {
      onSuccess: () => {
        invalidateList()
        setDeleteTarget(null)
        setDeleteError('')
      },
      onError: (err: Error) => setDeleteError(err.message),
    },
  })

  const DEFAULT_GRAPH_VALUES = {
    default_public_graph_profile: 'PUBLIC_KB_RICH',
    default_retrieval_mode: 'RAG' as const,
    default_language_mode: 'prefer',
    default_quality_threshold: 0.6,
    default_min_retrieval_results: 2,
    default_min_retrieval_score: 0.0,
    default_reranker_enabled: false,
    default_answer_template: 'generic',
  }

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', partner_id: '', theme_config: '{}', is_active: true, ...DEFAULT_GRAPH_VALUES },
  })

  function openCreate() {
    setEditing(null)
    setDefaultsOpen(false)
    reset({ name: '', partner_id: '', theme_config: '{}', is_active: true, ...DEFAULT_GRAPH_VALUES })
    setDialogOpen(true)
  }

  function openEdit(c: OrganizacionRead) {
    setEditing(c)
    setDefaultsOpen(false)
    reset({
      name: c.name,
      partner_id: c.partner_id,
      theme_config: JSON.stringify(c.theme_config, null, 2),
      is_active: c.is_active,
      default_public_graph_profile: c.default_public_graph_profile ?? 'PUBLIC_KB_RICH',
      default_retrieval_mode: (c.default_retrieval_mode as 'RAG' | 'MD_LONG_CONTEXT' | 'MD_AGENT_SELECTOR') ?? 'RAG',
      default_language_mode: c.default_language_mode ?? 'prefer',
      default_quality_threshold: c.default_quality_threshold ?? 0.6,
      default_min_retrieval_results: c.default_min_retrieval_results ?? 2,
      default_min_retrieval_score: c.default_min_retrieval_score ?? 0.0,
      default_reranker_enabled: c.default_reranker_enabled ?? false,
      default_answer_template: c.default_answer_template ?? 'generic',
    })
    setDialogOpen(true)
  }

  function closeDialog() {
    setDialogOpen(false)
    setEditing(null)
    reset()
  }

  function onSubmit(values: FormValues) {
    if (editing) {
      updateMutation.mutate({ organizacionId: editing.id, data: toBody(values) })
    } else {
      createMutation.mutate({ data: toBody(values) })
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  const filtered = filter
    ? organizaciones.filter((c) => c.name.toLowerCase().includes(filter.toLowerCase()))
    : organizaciones

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t('hub.organizaciones')}</h1>
        <button
          type="button"
          onClick={openCreate}
          className="px-3 py-2 bg-primary text-primary-foreground text-sm rounded-md"
        >
          {t('hub.new_organizacion')}
        </button>
      </div>

      <input
        type="text"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder={t('hub.filter_placeholder')}
        className="w-full px-3 py-2 border rounded-md text-sm bg-background"
        aria-label={t('hub.filter_placeholder')}
      />

      {isLoading && <p className="text-muted-foreground text-sm">{tc('loading')}</p>}

      {!isLoading && filtered.length === 0 && (
        <p className="text-muted-foreground text-sm py-8 text-center">{t('hub.no_organizaciones')}</p>
      )}

      {filtered.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="pb-2 font-medium">{t('hub.organizacion_name')}</th>
              <th className="pb-2 font-medium">{t('hub.organizacion_admin')}</th>
              <th className="pb-2 font-medium">{t('hub.organizacion_chatbots')}</th>
              <th className="pb-2 font-medium">{t('hub.organizacion_active')}</th>
              <th className="pb-2" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr
                key={c.id}
                className="border-b last:border-0 hover:bg-accent/30 cursor-pointer"
                onClick={() => openEdit(c)}
              >
                <td className="py-3 pr-4">{c.name}</td>
                <td className="py-3 pr-4 text-muted-foreground">{c.partner_id}</td>
                <td className="py-3 pr-4">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground border">
                    {c.chatbot_count}
                  </span>
                </td>
                <td className="py-3 pr-4">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleMutation.mutate({ organizacionId: c.id, data: { is_active: !c.is_active } })
                    }}
                    className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                      c.is_active
                        ? 'bg-green-100 text-green-700 border-green-200 hover:bg-green-200'
                        : 'bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-200'
                    }`}
                  >
                    {c.is_active ? t('hub.organizacion_active') : tc('edit')}
                  </button>
                </td>
                <td className="py-3 text-right">
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setDeleteTarget(c) }}
                    className="text-destructive text-xs hover:underline px-2"
                  >
                    {tc('delete')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Dialog crear / editar */}
      {dialogOpen && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 flex items-center justify-center bg-black/40 z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-md shadow-lg space-y-4">
            <h2 className="text-lg font-semibold">
              {editing ? tc('edit') + ' — ' + editing.name : t('hub.new_organizacion')}
            </h2>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div>
                <label htmlFor="organizacion_name" className="text-sm font-medium">{t('hub.organizacion_name')}</label>
                <input
                  id="organizacion_name"
                  {...register('name')}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                />
                {errors.name && <p className="text-destructive text-xs mt-1">{errors.name.message}</p>}
              </div>
              <div>
                <label htmlFor="organizacion_admin_id" className="text-sm font-medium">{t('hub.organizacion_admin')}</label>
                <input
                  id="organizacion_admin_id"
                  {...register('partner_id')}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                />
                {errors.partner_id && <p className="text-destructive text-xs mt-1">{errors.partner_id.message}</p>}
              </div>
              <div>
                <label htmlFor="organizacion_theme_config" className="text-sm font-medium">{t('hub.organizacion_theme')}</label>
                <textarea
                  id="organizacion_theme_config"
                  {...register('theme_config')}
                  rows={4}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background font-mono resize-y"
                />
              </div>
              <div className="border rounded-md overflow-hidden">
                <button
                  type="button"
                  onClick={() => setDefaultsOpen(v => !v)}
                  className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium bg-muted/30 hover:bg-muted/50 transition-colors"
                >
                  <span>{t('hub.organizacion_graph_defaults')}</span>
                  <span className="text-muted-foreground">{defaultsOpen ? '▾' : '▸'}</span>
                </button>
                {defaultsOpen && (
                  <div className="p-3 space-y-3 border-t">
                    <div>
                      <label htmlFor="org-default-graph-profile" className="text-xs font-medium text-muted-foreground">{t('hub.organizacion_default_graph_profile')}</label>
                      <select id="org-default-graph-profile" {...register('default_public_graph_profile')} className="w-full mt-1 px-2 py-1.5 border rounded-md text-sm bg-background">
                        <option value="PUBLIC_KB_RICH">{t('hub.chatbot_graph_profile_rich')}</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="org-default-retrieval-mode" className="text-xs font-medium text-muted-foreground">{t('hub.organizacion_default_retrieval_mode')}</label>
                      <select id="org-default-retrieval-mode" {...register('default_retrieval_mode')} className="w-full mt-1 px-2 py-1.5 border rounded-md text-sm bg-background">
                        <option value="RAG">Vectorial RAG</option>
                        <option value="MD_LONG_CONTEXT">Contexto largo</option>
                        <option value="MD_AGENT_SELECTOR">Exploración agéntica</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="org-default-language-mode" className="text-xs font-medium text-muted-foreground">{t('hub.organizacion_default_language_mode')}</label>
                      <select id="org-default-language-mode" {...register('default_language_mode')} className="w-full mt-1 px-2 py-1.5 border rounded-md text-sm bg-background">
                        <option value="prefer">{t('hub.chatbot_language_prefer')}</option>
                        <option value="strict">{t('hub.chatbot_language_strict')}</option>
                        <option value="none">{t('hub.chatbot_language_none')}</option>
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label htmlFor="org-default-quality-threshold" className="text-xs font-medium text-muted-foreground">{t('hub.organizacion_default_quality_threshold')}</label>
                        <input type="number" min={0} max={1} step={0.05} id="org-default-quality-threshold" {...register('default_quality_threshold', { valueAsNumber: true })} className="w-full mt-1 px-2 py-1.5 border rounded-md text-sm bg-background" />
                      </div>
                      <div>
                        <label htmlFor="org-default-min-results" className="text-xs font-medium text-muted-foreground">{t('hub.organizacion_default_min_results')}</label>
                        <input type="number" min={1} max={20} id="org-default-min-results" {...register('default_min_retrieval_results', { valueAsNumber: true })} className="w-full mt-1 px-2 py-1.5 border rounded-md text-sm bg-background" />
                      </div>
                      <div>
                        <label htmlFor="org-default-min-score" className="text-xs font-medium text-muted-foreground">{t('hub.organizacion_default_min_score')}</label>
                        <input type="number" min={0} max={1} step={0.05} id="org-default-min-score" {...register('default_min_retrieval_score', { valueAsNumber: true })} className="w-full mt-1 px-2 py-1.5 border rounded-md text-sm bg-background" />
                      </div>
                      <div>
                        <label htmlFor="org-default-answer-template" className="text-xs font-medium text-muted-foreground">{t('hub.organizacion_default_answer_template')}</label>
                        <select id="org-default-answer-template" {...register('default_answer_template')} className="w-full mt-1 px-2 py-1.5 border rounded-md text-sm bg-background">
                          <option value="generic">{t('hub.chatbot_answer_template_generic')}</option>
                          <option value="institutional">{t('hub.chatbot_answer_template_institutional')}</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <input type="checkbox" id="default_reranker_enabled" {...register('default_reranker_enabled')} className="rounded" />
                      <label htmlFor="default_reranker_enabled" className="text-xs">{t('hub.organizacion_default_reranker_enabled')}</label>
                    </div>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="is_active" {...register('is_active')} className="rounded" />
                <label htmlFor="is_active" className="text-sm">{t('hub.organizacion_active')}</label>
              </div>
              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={closeDialog}
                  className="px-3 py-2 border rounded-md text-sm"
                >
                  {tc('cancel')}
                </button>
                <button
                  type="submit"
                  disabled={isPending}
                  className="px-3 py-2 bg-primary text-primary-foreground rounded-md text-sm disabled:opacity-50"
                >
                  {tc('save')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Dialog confirmación borrado */}
      {deleteTarget && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 flex items-center justify-center bg-black/40 z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-sm shadow-lg space-y-4">
            <p className="text-sm">{t('hub.delete_organizacion_confirm')}</p>
            <p className="font-medium">{deleteTarget.name}</p>
            {deleteError && <p className="text-destructive text-xs">{deleteError}</p>}
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => { setDeleteTarget(null); setDeleteError('') }}
                className="px-3 py-2 border rounded-md text-sm"
              >
                {tc('cancel')}
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate({ organizacionId: deleteTarget.id })}
                disabled={deleteMutation.isPending}
                className="px-3 py-2 bg-destructive text-destructive-foreground rounded-md text-sm disabled:opacity-50"
              >
                {tc('delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function parseJson(raw: string): Record<string, unknown> {
  try {
    return JSON.parse(raw)
  } catch {
    return {}
  }
}
