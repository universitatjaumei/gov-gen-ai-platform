import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { ChatbotRead, CorpusStatsOut } from '@/shared/api/generated/model'
import {
  useCreateChatbotApiV1HubChatbotsPost,
  useUpdateChatbotApiV1HubChatbotsChatbotIdPatch,
  useDeleteChatbotApiV1HubChatbotsChatbotIdDelete,
  useListChatbotsApiV1HubChatbotsGet,
  useGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGet,
  useListChildrenApiV1HubChatbotsChatbotIdChildrenGet,
  useRegenerateChunksApiV1HubChatbotsChatbotIdRegenerateChunksPost,
  useAssignChildApiV1HubChatbotsChatbotIdChildrenPost,
  getListChatbotsApiV1HubChatbotsGetQueryKey,
  getListChildrenApiV1HubChatbotsChatbotIdChildrenGetQueryKey,
  getGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGetQueryKey,
} from '@/shared/api/generated/hub-chatbots/hub-chatbots'
import { useListLlmConfigsApiV1HubLlmConfigsGet } from '@/shared/api/generated/hub-llm-configs/hub-llm-configs'
import { useListOrganizacionesApiV1HubOrganizacionesGet } from '@/shared/api/generated/hub-organizaciones/hub-organizaciones'
import { chatbotCreateSchema, type FormValues } from '../chatbots/schemas/chatbotSchemas'
import { mapApiErrorsToFormErrors } from '@/shared/utils/formErrors'

const RETRIEVAL_MODES = [
  { value: 'RAG',               label: 'Vectorial RAG',         hint: 'Recupera los fragmentos más relevantes por búsqueda semántica. Recomendado para bases de conocimiento grandes.' },
  { value: 'MD_LONG_CONTEXT',   label: 'Contexto largo',        hint: 'Mete todos los documentos enteros en el prompt (máx. 128k tokens de contexto). Útil para colecciones pequeñas donde importa la visión global.' },
  { value: 'MD_AGENT_SELECTOR', label: 'Exploración agéntica',  hint: 'El LLM decide qué documentos leer durante la conversación usando herramientas. Sin límite de corpus, pero más lento.' },
] as const

// SEC.4.1: solo el color. El estado y su motivo vienen del contrato —los calcula el
// servidor—, y el texto sale de i18n; aquí no se decide nada sobre disponibilidad.
const AVAILABILITY_STYLES: Record<string, string> = {
  available: 'bg-green-100 text-green-700 border-green-200',
  expired: 'bg-red-100 text-red-700 border-red-200',
  not_yet_open: 'bg-amber-100 text-amber-700 border-amber-200',
  budget_exhausted: 'bg-orange-100 text-orange-700 border-orange-200',
}

// FIX.1: aquí vivían `DEV_ORG_ID` y `DEV_LLM_ID`. Eran dos identificadores de la BD de
// desarrollo escritos a mano en React —lo que CLAUDE.md prohíbe—, y el del modelo tenía
// consecuencia funcional: no había forma de cambiar de modelo, y guardar cualquier edición
// reasignaba el chatbot a esa configuración sin decirlo. Ahora salen del contrato.

type LlmConfigOption = {
  id: string
  provider: string
  model_name: string
  label?: string | null
  is_default?: boolean
}

type OrganizacionOption = { id: string; name: string }

function etiquetaModelo(config: LlmConfigOption): string {
  // El `model_name` exacto va SIEMPRE, aunque haya etiqueta. Es lo que distingue
  // `gemini-2.0-flash` de `gemini-2.5-flash`, y lo que deja ver de un vistazo que
  // `gemini-2.5-flash-preview-tts` es de texto a voz y no sirve para chatear.
  const etiqueta = config.label?.trim()
  const base = `${config.provider} · ${config.model_name}`
  const conEtiqueta = etiqueta ? `${etiqueta} — ${base}` : base
  return config.is_default ? `${conEtiqueta} (por defecto)` : conEtiqueta
}

export function ChatbotsPage() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [editing, setEditing] = useState<ChatbotRead | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<ChatbotRead | null>(null)
  const [deleteError, setDeleteError] = useState('')
  const [copied, setCopied] = useState(false)
  const [assignOpen, setAssignOpen] = useState(false)
  const [selectedChildId, setSelectedChildId] = useState('')

  const { data: chatbotsRaw, isLoading } = useListChatbotsApiV1HubChatbotsGet()
  const chatbots: ChatbotRead[] = (chatbotsRaw as unknown as ChatbotRead[] | undefined) ?? []

  // FIX.1: los dos catálogos que antes eran constantes escritas a mano.
  const { data: configsRaw } = useListLlmConfigsApiV1HubLlmConfigsGet()
  const llmConfigs = (configsRaw as unknown as LlmConfigOption[] | undefined) ?? []
  const { data: orgsRaw } = useListOrganizacionesApiV1HubOrganizacionesGet()
  const organizaciones = (orgsRaw as unknown as OrganizacionOption[] | undefined) ?? []

  const createMutation = useCreateChatbotApiV1HubChatbotsPost({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: getListChatbotsApiV1HubChatbotsGetQueryKey() })
        closeDialog()
      },
      onError: (error) => {
        mapApiErrorsToFormErrors(error, setError)
      },
    },
  })

  const updateMutation = useUpdateChatbotApiV1HubChatbotsChatbotIdPatch({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: getListChatbotsApiV1HubChatbotsGetQueryKey() })
        closeDialog()
      },
      onError: (error) => {
        mapApiErrorsToFormErrors(error, setError)
      },
    },
  })

  const toggleMutation = useUpdateChatbotApiV1HubChatbotsChatbotIdPatch({
    mutation: {
      onSuccess: () => qc.invalidateQueries({ queryKey: getListChatbotsApiV1HubChatbotsGetQueryKey() }),
    },
  })

  const deleteMutation = useDeleteChatbotApiV1HubChatbotsChatbotIdDelete({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: getListChatbotsApiV1HubChatbotsGetQueryKey() })
        setDeleteTarget(null)
        setDeleteError('')
      },
      onError: (err: unknown) => setDeleteError(err instanceof Error ? err.message : 'Error al eliminar'),
    },
  })

  const { register, handleSubmit, reset, watch, setError, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(chatbotCreateSchema),
    defaultValues: {
      name: '',
      kind: 'atomic',
      system_prompt: '',
      is_active: true,
      retrieval_mode: 'RAG',
      retrieval_top_k: 8,
      use_prompt_caching: false,
      cache_ttl: 3600,
      public_graph_profile: 'PUBLIC_KB_RICH',
      language_mode: 'prefer',
      quality_threshold: 0.6,
      min_retrieval_results: 2,
      min_retrieval_score: 0.0,
      reranker_enabled: false,
      answer_template: 'generic',
      llm_config_id: '',
      organizacion_id: '',
    },
  })
  const selectedKind = watch('kind')
  const retrievalHint = RETRIEVAL_MODES.find(m => m.value === watch('retrieval_mode'))?.hint

  const { data: childrenRaw, isLoading: isLoadingChildren } = useListChildrenApiV1HubChatbotsChatbotIdChildrenGet(
    editing?.id ?? '',
    { query: { enabled: dialogOpen && !!editing && selectedKind === 'router' } },
  )
  const children: ChatbotRead[] = (childrenRaw as unknown as ChatbotRead[] | undefined) ?? []

  const { data: corpusStatsRaw } = useGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGet(
    editing?.id ?? '',
    { query: { enabled: dialogOpen && !!editing } },
  )
  const corpusStats = corpusStatsRaw as unknown as CorpusStatsOut | undefined

  const assignChildMutation = useAssignChildApiV1HubChatbotsChatbotIdChildrenPost({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: getListChatbotsApiV1HubChatbotsGetQueryKey() })
        qc.invalidateQueries({ queryKey: getListChildrenApiV1HubChatbotsChatbotIdChildrenGetQueryKey(editing?.id ?? '') })
        setAssignOpen(false)
        setSelectedChildId('')
      },
    },
  })

  const regenerateChunksMutation = useRegenerateChunksApiV1HubChatbotsChatbotIdRegenerateChunksPost({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: getGetCorpusStatsApiV1HubChatbotsChatbotIdCorpusStatsGetQueryKey(editing?.id ?? '') })
      },
    },
  })

  function openCreate() {
    setEditing(null)
    setAssignOpen(false)
    setSelectedChildId('')
    reset({
      name: '',
      kind: 'atomic',
      system_prompt: '',
      is_active: true,
      retrieval_mode: 'RAG',
      retrieval_top_k: 8,
      use_prompt_caching: false,
      cache_ttl: 3600,
      public_graph_profile: 'PUBLIC_KB_RICH',
      language_mode: 'prefer',
      quality_threshold: 0.6,
      min_retrieval_results: 2,
      min_retrieval_score: 0.0,
      reranker_enabled: false,
      answer_template: 'generic',
      // Al crear se propone la configuración marcada por defecto, que es una sugerencia
      // visible en el desplegable y no un identificador oculto en el código.
      llm_config_id: (llmConfigs.find((c) => c.is_default) ?? llmConfigs[0])?.id ?? '',
      organizacion_id: organizaciones[0]?.id ?? '',
    })
    setDialogOpen(true)
  }

  function openEdit(c: ChatbotRead) {
    setEditing(c)
    setCopied(false)
    setAssignOpen(false)
    setSelectedChildId('')
    reset({
      name: c.name,
      kind: (c.kind as 'atomic' | 'router') ?? 'atomic',
      system_prompt: c.system_prompt,
      is_active: c.is_active,
      retrieval_mode: c.retrieval_mode ?? 'RAG',
      retrieval_top_k: c.retrieval_top_k ?? 8,
      use_prompt_caching: c.use_prompt_caching ?? false,
      cache_ttl: c.cache_ttl ?? 3600,
      public_graph_profile: c.public_graph_profile ?? 'PUBLIC_KB_RICH',
      language_mode: c.language_mode ?? 'prefer',
      quality_threshold: c.quality_threshold ?? 0.6,
      min_retrieval_results: c.min_retrieval_results ?? 2,
      min_retrieval_score: c.min_retrieval_score ?? 0.0,
      reranker_enabled: c.reranker_enabled ?? false,
      answer_template: c.answer_template ?? 'generic',
      // La del chatbot, no la de por defecto: es lo que impide que guardar una edición
      // cualquiera lo mueva de modelo sin que nadie lo haya pedido.
      llm_config_id: c.llm_config_id,
      organizacion_id: c.organizacion_id,
    })
    setDialogOpen(true)
  }

  function copyId() {
    void navigator.clipboard.writeText(editing!.id)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function installSnippet(id: string): string {
    const base = import.meta.env.VITE_API_URL ?? 'https://tu-api.ejemplo.com'
    return [
      `<div id="govgenai-widget"`,
      `     data-chatbot-id="${id}"`,
      `     data-lang="es"`,
      `     data-api-url="${base}/api/v1">`,
      `</div>`,
      `<script src="${base}/widget.iife.js"></script>`,
    ].join('\n')
  }

  function closeDialog() {
    setDialogOpen(false)
    setEditing(null)
    setAssignOpen(false)
    setSelectedChildId('')
    reset()
  }

  function openDelete(c: ChatbotRead) {
    closeDialog()
    deleteMutation.reset()
    setDeleteError('')
    setDeleteTarget(c)
  }

  function onSubmit(values: FormValues) {
    if (
      values.kind === 'atomic' &&
      values.retrieval_mode === 'MD_LONG_CONTEXT' &&
      (corpusStats?.total_tokens ?? 0) > 128_000
    ) {
      return
    }

    if (editing) {
      updateMutation.mutate({
        chatbotId: editing.id,
        data: {
          name: values.name,
          kind: values.kind,
          system_prompt: values.system_prompt,
          is_active: values.is_active,
          retrieval_mode: values.retrieval_mode,
          retrieval_top_k: values.retrieval_top_k,
          use_prompt_caching: values.use_prompt_caching,
          cache_ttl: values.cache_ttl,
          public_graph_profile: values.public_graph_profile,
          language_mode: values.language_mode,
          quality_threshold: values.quality_threshold,
          min_retrieval_results: values.min_retrieval_results,
          min_retrieval_score: values.min_retrieval_score,
          reranker_enabled: values.reranker_enabled,
          answer_template: values.answer_template,
          llm_config_id: values.llm_config_id,
        },
      })
    } else {
      createMutation.mutate({
        data: {
          name: values.name,
          kind: values.kind,
          system_prompt: values.system_prompt,
          is_active: values.is_active,
          retrieval_mode: values.retrieval_mode,
          retrieval_top_k: values.retrieval_top_k,
          use_prompt_caching: values.use_prompt_caching,
          cache_ttl: values.cache_ttl,
          organizacion_id: values.organizacion_id,
          llm_config_id: values.llm_config_id,
          public_graph_profile: values.public_graph_profile,
          language_mode: values.language_mode,
          quality_threshold: values.quality_threshold,
          min_retrieval_results: values.min_retrieval_results,
          min_retrieval_score: values.min_retrieval_score,
          reranker_enabled: values.reranker_enabled,
          answer_template: values.answer_template,
        },
      })
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending
  const showLongContextHardError =
    selectedKind === 'atomic' &&
    watch('retrieval_mode') === 'MD_LONG_CONTEXT' &&
    (corpusStats?.total_tokens ?? 0) > 128_000

  const assignableChildren = chatbots.filter(
    (cb) =>
      cb.id !== editing?.id &&
      cb.kind === 'atomic' &&
      cb.organizacion_id === (editing?.organizacion_id ?? organizaciones[0]?.id) &&
      cb.parent_chatbot_id === null,
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t('hub.chatbots')}</h1>
        <button
          type="button"
          onClick={openCreate}
          className="px-3 py-2 bg-primary text-primary-foreground text-sm rounded-md"
        >
          {t('hub.new_chatbot')}
        </button>
      </div>

      {isLoading && <p className="text-muted-foreground text-sm">{tc('loading')}</p>}

      {!isLoading && chatbots.length === 0 && (
        <p className="text-muted-foreground text-sm py-8 text-center">{t('hub.no_chatbots')}</p>
      )}

      {chatbots.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="pb-2 font-medium">{t('hub.chatbot_name')}</th>
              <th className="pb-2 font-medium">Retrieval</th>
              <th className="pb-2 font-medium">{t('hub.chatbot_active')}</th>
              <th className="pb-2 font-medium">{t('hub.availability')}</th>
              <th className="pb-2" />
            </tr>
          </thead>
          <tbody>
            {chatbots.map((c) => (
              <tr
                key={c.id}
                className="border-b last:border-0 hover:bg-accent/30 cursor-pointer"
                onClick={() => openEdit(c)}
              >
                <td className="py-3 pr-4">{c.name}</td>
                <td className="py-3 pr-4">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground border">
                    {RETRIEVAL_MODES.find(m => m.value === c.retrieval_mode)?.label ?? c.retrieval_mode}
                  </span>
                </td>
                <td className="py-3 pr-4">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleMutation.mutate({ chatbotId: c.id, data: { is_active: !c.is_active } })
                    }}
                    className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                      c.is_active
                        ? 'bg-green-100 text-green-700 border-green-200 hover:bg-green-200'
                        : 'bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-200'
                    }`}
                  >
                    {c.is_active ? t('hub.chatbot_active') : tc('edit')}
                  </button>
                </td>
                <td className="py-3 pr-4">
                  {/* SEC.4.1: el estado lo calcula el servidor y aquí solo se pinta. Nada
                      de comparar fechas en el cliente: serían dos máquinas de estado, la
                      del panel y la del chat, y se contradirían. */}
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border ${
                      AVAILABILITY_STYLES[c.availability?.state ?? 'available'] ??
                      AVAILABILITY_STYLES.available
                    }`}
                  >
                    {t(`hub.availability_${c.availability?.state ?? 'available'}`)}
                  </span>
                </td>
                <td className="py-3 text-right">
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); openDelete(c) }}
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
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 flex items-center justify-center bg-black/40 z-50 p-4"
          onClick={(e) => { if (e.target === e.currentTarget) closeDialog() }}
        >
          <div className="bg-card rounded-lg w-full max-w-md shadow-lg flex flex-col max-h-[90vh]">
            {/* Cabecera fija — siempre visible */}
            <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
              <h2 className="text-lg font-semibold truncate">
                {editing ? tc('edit') + ' — ' + editing.name : t('hub.new_chatbot')}
              </h2>
              <button
                type="button"
                onClick={closeDialog}
                className="ml-3 p-1 text-muted-foreground hover:text-foreground transition-colors"
                aria-label={tc('cancel')}
              >
                ✕
              </button>
            </div>

            {/* Cuerpo scrollable */}
            <div className="overflow-y-auto flex-1 px-6 py-4 space-y-4">
              {editing && (
                <div className="space-y-3 rounded-md border bg-muted/40 p-3 text-sm">
                  <div>
                    <p className="font-medium text-muted-foreground mb-1">{t('hub.chatbot_id_label')}</p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 truncate rounded bg-background px-2 py-1 font-mono text-xs border">
                        {editing.id}
                      </code>
                      <button
                        type="button"
                        onClick={copyId}
                        className="shrink-0 px-2 py-1 text-xs border rounded-md hover:bg-accent transition-colors"
                      >
                        {copied ? t('hub.chatbot_id_copied') : t('hub.chatbot_id_copy')}
                      </button>
                    </div>
                  </div>

                  <div>
                    <p className="font-medium text-muted-foreground mb-1">{t('hub.chatbot_install_title')}</p>
                    <p className="text-muted-foreground text-xs mb-1">{t('hub.chatbot_install_desc')}</p>
                    <pre
                      data-testid="install-snippet"
                      className="overflow-x-auto rounded bg-background border px-3 py-2 text-xs font-mono leading-relaxed"
                    >
                      {installSnippet(editing.id)}
                    </pre>
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
                <div>
                  <label htmlFor="chatbot-name" className="text-sm font-medium">{t('hub.chatbot_name')}</label>
                  <input
                    id="chatbot-name"
                    {...register('name')}
                    className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                  />
                  {errors.name && <p className="text-destructive text-xs mt-1">{errors.name.message}</p>}
                </div>
                <div>
                  <label htmlFor="chatbot-llm-config" className="text-sm font-medium">
                    {t('hub.chatbot_model')}
                  </label>
                  <select
                    id="chatbot-llm-config"
                    {...register('llm_config_id')}
                    className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                  >
                    {llmConfigs.length === 0 && <option value="">{t('hub.no_llm_configs')}</option>}
                    {llmConfigs.map((config) => (
                      <option key={config.id} value={config.id}>{etiquetaModelo(config)}</option>
                    ))}
                  </select>
                  <p className="text-xs text-muted-foreground mt-1">{t('hub.chatbot_model_hint')}</p>
                  {errors.llm_config_id && (
                    <p className="text-destructive text-xs mt-1">{errors.llm_config_id.message}</p>
                  )}
                </div>
                {!editing && (
                  <div>
                    <label htmlFor="chatbot-organizacion" className="text-sm font-medium">
                      {t('hub.chatbot_organizacion')}
                    </label>
                    <select
                      id="chatbot-organizacion"
                      {...register('organizacion_id')}
                      className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                    >
                      {organizaciones.map((org) => (
                        <option key={org.id} value={org.id}>{org.name}</option>
                      ))}
                    </select>
                    {errors.organizacion_id && (
                      <p className="text-destructive text-xs mt-1">{errors.organizacion_id.message}</p>
                    )}
                  </div>
                )}
                <div>
                  <label htmlFor="chatbot-kind" className="text-sm font-medium">Tipo de chatbot</label>
                  <select
                    id="chatbot-kind"
                    {...register('kind')}
                    className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                  >
                    <option value="atomic">Atómico</option>
                    <option value="router">Router</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="chatbot-system-prompt" className="text-sm font-medium">{selectedKind === 'router' ? 'Descripción del router' : t('hub.chatbot_prompt')}</label>
                  <textarea
                    id="chatbot-system-prompt"
                    {...register('system_prompt')}
                    rows={8}
                    className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background resize-y"
                  />
                  {errors.system_prompt && <p className="text-destructive text-xs mt-1">{errors.system_prompt.message}</p>}
                </div>
                {editing && corpusStats && (
                  <div className="rounded-md border bg-blue-50 border-blue-200 p-3 space-y-1">
                    <p className="text-sm">
                      <span className="font-medium">Sugerido:</span>{' '}
                      <strong>{corpusStats.recommended_mode}</strong>
                      <span className="text-muted-foreground"> — {corpusStats.total_tokens.toLocaleString()} tokens</span>
                    </p>
                    <p className="text-xs text-muted-foreground">{corpusStats.recommendation_reason}</p>
                    {selectedKind === 'atomic' && watch('retrieval_mode') !== corpusStats.recommended_mode && (
                      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                        Has elegido un modo distinto del recomendado para este corpus.
                      </p>
                    )}
                    {selectedKind === 'atomic' && watch('retrieval_mode') === 'RAG' && (
                      <div className="pt-1">
                        <button
                          type="button"
                          onClick={() => regenerateChunksMutation.mutate({ chatbotId: editing!.id })}
                          disabled={regenerateChunksMutation.isPending}
                          className="px-2 py-1 text-xs border rounded-md hover:bg-accent disabled:opacity-50"
                        >
                          {regenerateChunksMutation.isPending ? 'Regenerando...' : 'Recalcular chunks'}
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {selectedKind === 'atomic' && (
                  <>
                    <div>
                      <label htmlFor="chatbot-retrieval-mode" className="text-sm font-medium">Modo de retrieval</label>
                      <select
                        id="chatbot-retrieval-mode"
                        {...register('retrieval_mode')}
                        className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                      >
                        {RETRIEVAL_MODES.map(m => (
                          <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                      </select>
                      {retrievalHint && <p className="text-xs text-muted-foreground mt-1">{retrievalHint}</p>}
                    </div>
                    {watch('retrieval_mode') === 'RAG' && (
                      <div>
                        <label className="text-sm font-medium">Resultados recuperados (top-k)</label>
                        <input
                          type="number"
                          min={1}
                          max={50}
                          {...register('retrieval_top_k', { valueAsNumber: true })}
                          className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                        />
                        {errors.retrieval_top_k && <p className="text-destructive text-xs mt-1">{errors.retrieval_top_k.message}</p>}
                        <p className="text-xs text-muted-foreground mt-1">Número de fragmentos que se recuperan por consulta (1–50). Valor recomendado: 8.</p>
                      </div>
                    )}
                    {watch('retrieval_mode') === 'MD_LONG_CONTEXT' && (
                      <div className="rounded-md border bg-muted/40 p-3 space-y-2">
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            id="use_prompt_caching"
                            {...register('use_prompt_caching')}
                            className="rounded"
                          />
                          <label htmlFor="use_prompt_caching" className="text-sm">
                            Activar Prompt Caching
                          </label>
                        </div>
                        {watch('use_prompt_caching') && (
                          <div>
                            <label className="text-sm font-medium">TTL de caché (segundos)</label>
                            <input
                              type="number"
                              min={60}
                              max={86400}
                              {...register('cache_ttl', { valueAsNumber: true })}
                              className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                            />
                            {errors.cache_ttl && <p className="text-destructive text-xs mt-1">{errors.cache_ttl.message}</p>}
                          </div>
                        )}
                      </div>
                    )}
                    {showLongContextHardError && (
                      <p className="text-destructive text-xs mt-1">
                        {t('hub.chatbot_long_context_error')}
                      </p>
                    )}
                    <div className="pt-2">
                      <p className="text-sm font-medium text-muted-foreground mb-2">{t('hub.chatbot_graph_section')}</p>
                      <div className="space-y-3 rounded-md border bg-muted/40 p-3">
                        <div>
                          <label className="text-sm font-medium">{t('hub.chatbot_graph_profile')}</label>
                          <select
                            {...register('public_graph_profile')}
                            className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                          >
                            <option value="PUBLIC_KB_RICH">{t('hub.chatbot_graph_profile_rich')}</option>
                            <option value="PUBLIC_PORTAL_AGGREGATOR">{t('hub.chatbot_graph_profile_aggregator')}</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-sm font-medium">{t('hub.chatbot_language_mode')}</label>
                          <select
                            {...register('language_mode')}
                            className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                          >
                            <option value="prefer">{t('hub.chatbot_language_prefer')}</option>
                            <option value="strict">{t('hub.chatbot_language_strict')}</option>
                            <option value="none">{t('hub.chatbot_language_none')}</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-sm font-medium">{t('hub.chatbot_quality_threshold')}</label>
                          <input
                            type="number"
                            min={0}
                            max={1}
                            step={0.05}
                            {...register('quality_threshold', { valueAsNumber: true })}
                            className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                          />
                        </div>
                        <div>
                          <label className="text-sm font-medium">{t('hub.chatbot_min_results')}</label>
                          <input
                            type="number"
                            min={1}
                            max={20}
                            {...register('min_retrieval_results', { valueAsNumber: true })}
                            className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                          />
                        </div>
                        <div>
                          <label className="text-sm font-medium">{t('hub.chatbot_min_score')}</label>
                          <input
                            type="number"
                            min={0}
                            max={1}
                            step={0.05}
                            {...register('min_retrieval_score', { valueAsNumber: true })}
                            className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            id="reranker_enabled"
                            {...register('reranker_enabled')}
                            className="rounded"
                          />
                          <label htmlFor="reranker_enabled" className="text-sm">{t('hub.chatbot_reranker_enabled')}</label>
                        </div>
                        <div>
                          <label className="text-sm font-medium">{t('hub.chatbot_answer_template')}</label>
                          <select
                            {...register('answer_template')}
                            className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                          >
                            <option value="generic">{t('hub.chatbot_answer_template_generic')}</option>
                            <option value="institutional">{t('hub.chatbot_answer_template_institutional')}</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </>
                )}
                {editing && selectedKind === 'router' && (
                  <div className="rounded-md border bg-muted/40 p-3 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">Sub-chatbots</p>
                      <button
                        type="button"
                        onClick={() => setAssignOpen(true)}
                        className="px-2 py-1 text-xs border rounded-md hover:bg-accent"
                      >
                        Asignar hijo
                      </button>
                    </div>
                    {isLoadingChildren && <p className="text-xs text-muted-foreground">Cargando sub-chatbots...</p>}
                    {!isLoadingChildren && children.length === 0 && (
                      <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
                        Este router no tiene sub-chatbots asignados
                      </p>
                    )}
                    {!isLoadingChildren && children.length > 0 && (
                      <ul className="space-y-1">
                        {children.map((child) => (
                          <li key={child.id} className="text-xs rounded border px-2 py-1 bg-background">
                            {child.name}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                {assignOpen && editing && selectedKind === 'router' && (
                  <div className="rounded-md border p-3 space-y-2 bg-background">
                    <label className="text-xs font-medium">Selecciona chatbot atómico</label>
                    <select
                      value={selectedChildId}
                      onChange={(e) => setSelectedChildId(e.target.value)}
                      className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                    >
                      <option value="">-- Seleccionar --</option>
                      {assignableChildren.map((cb) => (
                        <option key={cb.id} value={cb.id}>{cb.name}</option>
                      ))}
                    </select>
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => { setAssignOpen(false); setSelectedChildId('') }}
                        className="px-2 py-1 text-xs border rounded-md"
                      >
                        Cancelar
                      </button>
                      <button
                        type="button"
                        disabled={!selectedChildId || assignChildMutation.isPending}
                        onClick={() =>
                          assignChildMutation.mutate({
                            chatbotId: editing.id,
                            data: { child_chatbot_id: selectedChildId },
                          })
                        }
                        className="px-2 py-1 text-xs bg-primary text-primary-foreground rounded-md disabled:opacity-50"
                      >
                        Asignar
                      </button>
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <input type="checkbox" id="is_active" {...register('is_active')} className="rounded" />
                  <label htmlFor="is_active" className="text-sm">{t('hub.chatbot_active')}</label>
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
                    disabled={isPending || showLongContextHardError}
                    className="px-3 py-2 bg-primary text-primary-foreground rounded-md text-sm disabled:opacity-50"
                  >
                    {tc('save')}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Dialog confirmación borrado */}
      {deleteTarget && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 flex items-center justify-center bg-black/40 z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-sm shadow-lg space-y-4">
            <p className="text-sm">{t('hub.delete_confirm')}</p>
            <p className="font-medium">{deleteTarget.name}</p>
            {deleteError && (
              <div className="rounded-md bg-destructive/10 border border-destructive/30 px-3 py-2">
                <p className="text-destructive text-sm font-medium">{deleteError}</p>
              </div>
            )}
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
                onClick={() => deleteMutation.mutate({ chatbotId: deleteTarget.id })}
                disabled={deleteMutation.isPending}
                className="px-3 py-2 bg-destructive text-destructive-foreground rounded-md text-sm disabled:opacity-50 min-w-[80px]"
              >
                {deleteMutation.isPending ? '...' : tc('delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
