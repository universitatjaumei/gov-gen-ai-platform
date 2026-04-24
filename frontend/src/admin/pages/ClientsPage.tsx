import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  fetchClients,
  createClient,
  updateClient,
  deleteClient,
  type Client,
} from '@/shared/api/clients'

const schema = z.object({
  name: z.string().min(1),
  partner_id: z.string().min(1),
  theme_config: z.string().default('{}'),
  is_active: z.boolean(),
})
type FormValues = z.infer<typeof schema>

export function ClientsPage() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [editing, setEditing] = useState<Client | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Client | null>(null)
  const [deleteError, setDeleteError] = useState('')
  const [filter, setFilter] = useState('')

  const { data: clients = [], isLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: fetchClients,
  })

  const createMutation = useMutation({
    mutationFn: (values: FormValues) =>
      createClient({
        name: values.name,
        partner_id: values.partner_id,
        theme_config: parseJson(values.theme_config),
        is_active: values.is_active,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clients'] })
      closeDialog()
    },
  })

  const updateMutation = useMutation({
    mutationFn: (values: FormValues) =>
      updateClient(editing!.id, {
        name: values.name,
        partner_id: values.partner_id,
        theme_config: parseJson(values.theme_config),
        is_active: values.is_active,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clients'] })
      closeDialog()
    },
  })

  const toggleMutation = useMutation({
    mutationFn: (c: Client) => updateClient(c.id, { is_active: !c.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['clients'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteClient(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clients'] })
      setDeleteTarget(null)
      setDeleteError('')
    },
    onError: (err: Error) => setDeleteError(err.message),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', partner_id: '', theme_config: '{}', is_active: true },
  })

  function openCreate() {
    setEditing(null)
    reset({ name: '', partner_id: '', theme_config: '{}', is_active: true })
    setDialogOpen(true)
  }

  function openEdit(c: Client) {
    setEditing(c)
    reset({
      name: c.name,
      partner_id: c.partner_id,
      theme_config: JSON.stringify(c.theme_config, null, 2),
      is_active: c.is_active,
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
      updateMutation.mutate(values)
    } else {
      createMutation.mutate(values)
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  const filtered = filter
    ? clients.filter((c) => c.name.toLowerCase().includes(filter.toLowerCase()))
    : clients

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t('hub.clients')}</h1>
        <button
          type="button"
          onClick={openCreate}
          className="px-3 py-2 bg-primary text-primary-foreground text-sm rounded-md"
        >
          {t('hub.new_client')}
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
        <p className="text-muted-foreground text-sm py-8 text-center">{t('hub.no_clients')}</p>
      )}

      {filtered.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="pb-2 font-medium">{t('hub.client_name')}</th>
              <th className="pb-2 font-medium">{t('hub.client_partner')}</th>
              <th className="pb-2 font-medium">{t('hub.client_chatbots')}</th>
              <th className="pb-2 font-medium">{t('hub.client_active')}</th>
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
                    onClick={(e) => { e.stopPropagation(); toggleMutation.mutate(c) }}
                    className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                      c.is_active
                        ? 'bg-green-100 text-green-700 border-green-200 hover:bg-green-200'
                        : 'bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-200'
                    }`}
                  >
                    {c.is_active ? t('hub.client_active') : tc('edit')}
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
              {editing ? tc('edit') + ' — ' + editing.name : t('hub.new_client')}
            </h2>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
              <div>
                <label htmlFor="client_name" className="text-sm font-medium">{t('hub.client_name')}</label>
                <input
                  id="client_name"
                  {...register('name')}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                />
                {errors.name && <p className="text-destructive text-xs mt-1">{errors.name.message}</p>}
              </div>
              <div>
                <label htmlFor="client_partner_id" className="text-sm font-medium">{t('hub.client_partner')}</label>
                <input
                  id="client_partner_id"
                  {...register('partner_id')}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                />
                {errors.partner_id && <p className="text-destructive text-xs mt-1">{errors.partner_id.message}</p>}
              </div>
              <div>
                <label htmlFor="client_theme_config" className="text-sm font-medium">{t('hub.client_theme')}</label>
                <textarea
                  id="client_theme_config"
                  {...register('theme_config')}
                  rows={4}
                  className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background font-mono resize-y"
                />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="is_active" {...register('is_active')} className="rounded" />
                <label htmlFor="is_active" className="text-sm">{t('hub.client_active')}</label>
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
            <p className="text-sm">{t('hub.delete_client_confirm')}</p>
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

function parseJson(raw: string): Record<string, unknown> {
  try {
    return JSON.parse(raw)
  } catch {
    return {}
  }
}
