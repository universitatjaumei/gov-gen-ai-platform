import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  fetchChatbots,
  createChatbot,
  deleteChatbot,
  type Chatbot,
  type ChatbotCreate,
} from '@/shared/api/chatbots'

const schema = z.object({
  name: z.string().min(1),
  client_id: z.string().uuid(),
  llm_config_id: z.string().uuid(),
  system_prompt: z.string().min(1),
})
type FormValues = z.infer<typeof schema>

const DEV_CLIENT_ID = '00000000-0000-0000-0000-000000000010'
const DEV_LLM_ID = '00000000-0000-0000-0000-000000000001'

export function ChatbotsPage() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)

  const { data: chatbots = [], isLoading } = useQuery({
    queryKey: ['chatbots'],
    queryFn: fetchChatbots,
  })

  const createMutation = useMutation({
    mutationFn: createChatbot,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['chatbots'] })
      setDialogOpen(false)
      reset()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteChatbot,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['chatbots'] }),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { client_id: DEV_CLIENT_ID, llm_config_id: DEV_LLM_ID },
  })

  function onSubmit(values: FormValues) {
    createMutation.mutate(values as ChatbotCreate)
  }

  function handleDelete(chatbot: Chatbot) {
    if (window.confirm(t('hub.delete_confirm'))) {
      deleteMutation.mutate(chatbot.id)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t('hub.chatbots')}</h1>
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
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
              <tr key={c.id} className="border-b last:border-0">
                <td className="py-3">{c.name}</td>
                <td className="py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${c.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {c.is_active ? '✓' : '✗'}
                  </span>
                </td>
                <td className="py-3 text-right">
                  <button
                    type="button"
                    onClick={() => handleDelete(c)}
                    className="text-destructive text-xs hover:underline"
                  >
                    {tc('delete')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {dialogOpen && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 flex items-center justify-center bg-black/40 z-50">
          <div className="bg-card rounded-lg p-6 w-full max-w-md shadow-lg space-y-4">
            <h2 className="text-lg font-semibold">{t('hub.new_chatbot')}</h2>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div>
                <label className="text-sm font-medium">{t('hub.chatbot_name')}</label>
                <input {...register('name')} className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background" />
                {errors.name && <p className="text-destructive text-xs mt-1">{errors.name.message}</p>}
              </div>
              <div>
                <label className="text-sm font-medium">{t('hub.chatbot_prompt')}</label>
                <textarea {...register('system_prompt')} rows={4}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background resize-none" />
                {errors.system_prompt && <p className="text-destructive text-xs mt-1">{errors.system_prompt.message}</p>}
              </div>
              <div className="flex gap-2 justify-end pt-2">
                <button type="button" onClick={() => { setDialogOpen(false); reset() }}
                  className="px-3 py-2 border rounded-md text-sm">{tc('cancel')}</button>
                <button type="submit" disabled={createMutation.isPending}
                  className="px-3 py-2 bg-primary text-primary-foreground rounded-md text-sm disabled:opacity-50">
                  {tc('save')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
