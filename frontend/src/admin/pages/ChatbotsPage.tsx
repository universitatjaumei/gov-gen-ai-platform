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

const schema = z.object({
  name: z.string().min(1),
  system_prompt: z.string().min(1),
  is_active: z.boolean(),
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

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', system_prompt: '', is_active: true },
  })

  function openCreate() {
    setEditing(null)
    reset({ name: '', system_prompt: '', is_active: true })
    setDialogOpen(true)
  }

  function openEdit(c: Chatbot) {
    setEditing(c)
    reset({ name: c.name, system_prompt: c.system_prompt, is_active: c.is_active })
    setDialogOpen(true)
  }

  function closeDialog() {
    setDialogOpen(false)
    setEditing(null)
    reset()
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
              {editing ? tc('edit') + ' — ' + editing.name : t('hub.new_chatbot')}
            </h2>
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
                  rows={4}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background resize-none"
                />
                {errors.system_prompt && <p className="text-destructive text-xs mt-1">{errors.system_prompt.message}</p>}
              </div>
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
      )}

      {/* Dialog confirmación borrado */}
      {deleteTarget && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 flex items-center justify-center bg-black/40 z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-sm shadow-lg space-y-4">
            <p className="text-sm">{t('hub.delete_confirm')}</p>
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
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
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
