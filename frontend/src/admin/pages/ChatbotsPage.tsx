import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  fetchChatbots,
  createChatbot,
  updateChatbot,
  deleteChatbot,
  type Chatbot,
} from '@/shared/api/chatbots'

const RETRIEVAL_MODES = [
  { value: 'vector',       label: 'Vectorial RAG',         hint: 'Recupera los fragmentos más relevantes por búsqueda semántica. Recomendado para bases de conocimiento grandes.' },
  { value: 'long_context', label: 'Contexto largo',        hint: 'Mete todos los documentos enteros en el prompt (máx. 150k tokens). Útil para colecciones pequeñas donde importa la visión global.' },
  { value: 'agentic',      label: 'Exploración agéntica',  hint: 'El LLM decide qué documentos leer durante la conversación usando herramientas. Sin límite de corpus, pero más lento.' },
] as const

const schema = z.object({
  name: z.string().min(1),
  system_prompt: z.string().min(1),
  is_active: z.boolean(),
  retrieval_mode: z.enum(['vector', 'long_context', 'agentic']),
  retrieval_top_k: z.number().int().min(1).max(50),
})
type FormValues = z.infer<typeof schema>

const DEV_CLIENT_ID = '00000000-0000-0000-0000-000000000010'
const DEV_LLM_ID = '00000000-0000-0000-0000-000000000001'

export function ChatbotsPage() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [editing, setEditing] = useState<Chatbot | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Chatbot | null>(null)
  const [deleteError, setDeleteError] = useState('')
  const [copied, setCopied] = useState(false)

  const { data: chatbots = [], isLoading } = useQuery({
    queryKey: ['chatbots'],
    queryFn: fetchChatbots,
  })

  const createMutation = useMutation({
    mutationFn: (values: FormValues) =>
      createChatbot({
        name: values.name,
        system_prompt: values.system_prompt,
        is_active: values.is_active,
        retrieval_mode: values.retrieval_mode,
        retrieval_top_k: values.retrieval_top_k,
        client_id: DEV_CLIENT_ID,
        llm_config_id: DEV_LLM_ID,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['chatbots'] })
      closeDialog()
    },
  })

  const updateMutation = useMutation({
    mutationFn: (values: FormValues) =>
      updateChatbot(editing!.id, {
        name: values.name,
        system_prompt: values.system_prompt,
        is_active: values.is_active,
        retrieval_mode: values.retrieval_mode,
        retrieval_top_k: values.retrieval_top_k,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['chatbots'] })
      closeDialog()
    },
  })

  const toggleMutation = useMutation({
    mutationFn: (c: Chatbot) => updateChatbot(c.id, { is_active: !c.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['chatbots'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteChatbot(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['chatbots'] })
      setDeleteTarget(null)
      setDeleteError('')
    },
    onError: (err: Error) => setDeleteError(err.message),
  })

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', system_prompt: '', is_active: true, retrieval_mode: 'vector', retrieval_top_k: 8 },
  })
  const retrievalHint = RETRIEVAL_MODES.find(m => m.value === watch('retrieval_mode'))?.hint

  function openCreate() {
    setEditing(null)
    reset({ name: '', system_prompt: '', is_active: true, retrieval_mode: 'vector', retrieval_top_k: 8 })
    setDialogOpen(true)
  }

  function openEdit(c: Chatbot) {
    setEditing(c)
    setCopied(false)
    reset({ name: c.name, system_prompt: c.system_prompt, is_active: c.is_active, retrieval_mode: c.retrieval_mode ?? 'vector', retrieval_top_k: c.retrieval_top_k ?? 8 })
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
    reset()
  }

  function openDelete(c: Chatbot) {
    closeDialog()
    deleteMutation.reset()
    setDeleteError('')
    setDeleteTarget(c)
  }

  function onSubmit(values: FormValues) {
    if (editing) {
      updateMutation.mutate(values)
    } else {
      createMutation.mutate(values)
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

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
                    onClick={(e) => { e.stopPropagation(); toggleMutation.mutate(c) }}
                    className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                      c.is_active
                        ? 'bg-green-100 text-green-700 border-green-200 hover:bg-green-200'
                        : 'bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-200'
                    }`}
                  >
                    {c.is_active ? t('hub.chatbot_active') : tc('edit')}
                  </button>
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
                  <label className="text-sm font-medium">{t('hub.chatbot_name')}</label>
                  <input
                    {...register('name')}
                    className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                  />
                  {errors.name && <p className="text-destructive text-xs mt-1">{errors.name.message}</p>}
                </div>
                <div>
                  <label className="text-sm font-medium">{t('hub.chatbot_prompt')}</label>
                  <textarea
                    {...register('system_prompt')}
                    rows={8}
                    className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background resize-y"
                  />
                  {errors.system_prompt && <p className="text-destructive text-xs mt-1">{errors.system_prompt.message}</p>}
                </div>
                <div>
                  <label className="text-sm font-medium">Modo de retrieval</label>
                  <select
                    {...register('retrieval_mode')}
                    className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                  >
                    {RETRIEVAL_MODES.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                  {retrievalHint && <p className="text-xs text-muted-foreground mt-1">{retrievalHint}</p>}
                </div>
                {watch('retrieval_mode') === 'vector' && (
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
                    disabled={isPending}
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
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
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
