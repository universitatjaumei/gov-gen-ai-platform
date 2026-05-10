import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  fetchLLMConfigs,
  createLLMConfig,
  updateLLMConfig,
  deleteLLMConfig,
  testLLMConfig,
  fetchAvailableModels,
  fetchProviders,
  createProvider,
  updateProvider,
  deleteProvider,
} from '@/shared/api/llmConfigs'
import type { LLMConfigRead, HubProviderOut } from '@/shared/api/generated/model'

const TIERS = [1, 2, 3] as const
const DEFAULT_MAX_TOKENS = 12000
const DEFAULT_TEMPERATURE_BY_TIER: Record<number, number> = {
  1: 0.1,
  2: 0.0,
  3: 0.0,
}

const DEFAULT_API_KEY_BY_PROVIDER: Record<string, string> = {
  google: 'GOOGLE_API_KEY',
  openrouter: 'OPENROUTER_API_KEY',
  openai: 'OPENAI_API_KEY',
}

const TIER_STYLES: Record<number, string> = {
  1: 'bg-green-100 text-green-700',
  2: 'bg-yellow-100 text-yellow-700',
  3: 'bg-red-100 text-red-700',
}

const schema = z.object({
  provider: z.string().min(1),
  model_name: z.string().min(1),
  tier: z.number().int().min(1).max(3),
  label: z.string().min(1),
  api_key_secret_name: z.string().optional(),
  is_default: z.boolean(),
  temperature: z.number().min(0).max(2),
  top_p: z.number().min(0).max(1),
  max_tokens: z.number().int().min(1),
})
type FormValues = z.infer<typeof schema>

function getDefaultApiKeySecret(
  providerId: string,
  providers: HubProviderOut[] = [],
): string {
  const byId = DEFAULT_API_KEY_BY_PROVIDER[providerId]
  if (byId) return byId

  const provider = providers.find((p) => p.id === providerId)
  if (!provider) return ''

  const pid = (provider.id || '').toLowerCase()
  const pname = (provider.name || '').toLowerCase()
  const pbase = (provider.base_url || '').toLowerCase()

  if (pid.includes('openrouter') || pname.includes('openrouter') || pbase.includes('openrouter.ai')) {
    return 'OPENROUTER_API_KEY'
  }
  if (pid.includes('openai') || pname.includes('openai')) {
    return 'OPENAI_API_KEY'
  }
  if (pid.includes('google') || pname.includes('google')) {
    return 'GOOGLE_API_KEY'
  }
  return ''
}

function getDefaultTemperatureForTier(tier: number): number {
  return DEFAULT_TEMPERATURE_BY_TIER[tier] ?? 0.1
}

export function LLMConfigsPage() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [editing, setEditing] = useState<LLMConfigRead | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<LLMConfigRead | null>(null)
  const [deleteError, setDeleteError] = useState('')
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; latency_ms: number } | { error: string }>>({})
  const [testingId, setTestingId] = useState<string | null>(null)
  const [isCustomModel, setIsCustomModel] = useState(false)

  const { data: configs = [], isLoading: isLoadingConfigs } = useQuery({
    queryKey: ['llm-configs'],
    queryFn: fetchLLMConfigs,
  })

  const { data: providers = [], isLoading: isLoadingProviders } = useQuery({
    queryKey: ['hub-providers'],
    queryFn: fetchProviders,
  })

  const createMutation = useMutation({
    mutationFn: (values: FormValues) => createLLMConfig(values),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['llm-configs'] }); closeDialog() },
  })

  const updateMutation = useMutation({
    mutationFn: (values: FormValues) => updateLLMConfig(editing!.id, values),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['llm-configs'] }); closeDialog() },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteLLMConfig(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['llm-configs'] }); setDeleteTarget(null); setDeleteError('') },
    onError: (err: Error) => setDeleteError(err.message),
  })

  const isPending = createMutation.isPending || updateMutation.isPending

  const { register, handleSubmit, reset, control, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      provider: '',
      model_name: '',
      tier: 1,
      label: '',
      api_key_secret_name: '',
      is_default: false,
      temperature: getDefaultTemperatureForTier(1),
      top_p: 1,
      max_tokens: DEFAULT_MAX_TOKENS,
    },
  })

  const currentProvider = useWatch({ control, name: 'provider' })
  const { data: availableModels = [] } = useQuery({
    queryKey: ['available-models', currentProvider],
    queryFn: () => fetchAvailableModels(currentProvider),
    enabled: dialogOpen && !!currentProvider,
  })

  function openCreate() {
    setEditing(null)
    setIsCustomModel(false)
    const defaultProvider = providers[0]?.id ?? ''
    reset({
      provider: defaultProvider,
      model_name: '',
      tier: 1,
      label: '',
      api_key_secret_name: getDefaultApiKeySecret(defaultProvider, providers),
      is_default: false,
      temperature: getDefaultTemperatureForTier(1),
      top_p: 1,
      max_tokens: DEFAULT_MAX_TOKENS,
    })
    setDialogOpen(true)
  }

  function openEdit(c: LLMConfigRead) {
    setEditing(c)
    setIsCustomModel(false)
    reset({
      provider: c.provider,
      model_name: c.model_name,
      tier: c.tier,
      label: c.label,
      api_key_secret_name: c.api_key_secret_name ?? getDefaultApiKeySecret(c.provider, providers),
      is_default: c.is_default,
      temperature: c.temperature,
      top_p: c.top_p ?? 1,
      max_tokens: c.max_tokens,
    })
    setDialogOpen(true)
  }

  function closeDialog() { setDialogOpen(false); setEditing(null) }

  function onSubmit(values: FormValues) {
    if (editing) updateMutation.mutate(values)
    else createMutation.mutate(values)
  }

  async function handleTest(id: string) {
    setTestingId(id)
    try {
      const result = await testLLMConfig(id)
      setTestResults(prev => ({ ...prev, [id]: result }))
    } catch (e) {
      setTestResults(prev => ({ ...prev, [id]: { error: (e as Error).message } }))
    } finally {
      setTestingId(null)
    }
  }

  const tierField = register('tier', { valueAsNumber: true })

  return (
    <div className="space-y-8">
      {/* SECCIÓN DE PROVEEDORES */}
      <ProvidersSection providers={providers} isLoading={isLoadingProviders} />

      {/* SECCIÓN DE CONFIGURACIONES LLM */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{t('hub.llm_configs')}</h2>
          <button onClick={openCreate} className="px-3 py-2 bg-primary text-primary-foreground rounded-md text-sm">
            {t('hub.new_llm_config')}
          </button>
        </div>

        {isLoadingConfigs ? (
          <p className="text-sm text-muted-foreground">…</p>
        ) : configs.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('hub.no_llm_configs')}</p>
        ) : (
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">{t('hub.llm_config_label')}</th>
                  <th className="text-left px-4 py-3 font-medium">{t('hub.llm_config_provider')}</th>
                  <th className="text-left px-4 py-3 font-medium">{t('hub.llm_config_model')}</th>
                  <th className="text-left px-4 py-3 font-medium">{t('hub.llm_config_tier')}</th>
                  <th className="text-left px-4 py-3 font-medium">{t('hub.llm_config_is_default')}</th>
                  <th className="text-left px-4 py-3 font-medium">{t('hub.llm_config_api_key')}</th>
                  <th className="text-right px-4 py-3 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {configs.map(c => {
                  const pName = providers.find(p => p.id === c.provider)?.name || c.provider;
                  return (
                    <tr key={c.id} className="border-t hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-medium cursor-pointer" onClick={() => openEdit(c)}>{c.label || '—'}</td>
                      <td className="px-4 py-3 text-muted-foreground">{pName}</td>
                      <td className="px-4 py-3 font-mono text-xs">{c.model_name}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TIER_STYLES[c.tier] ?? 'bg-muted text-muted-foreground'}`}>
                          Tier {c.tier}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {c.is_default && <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">default</span>}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{c.api_key_secret_name ?? '—'}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 justify-end">
                          <button
                            onClick={() => handleTest(c.id)}
                            disabled={testingId === c.id}
                            className="px-2 py-1 border rounded text-xs hover:bg-accent disabled:opacity-50"
                          >
                            {testingId === c.id ? '…' : t('hub.llm_config_test')}
                          </button>
                          {testResults[c.id] && (
                            'error' in testResults[c.id] ? (
                              <span className="text-xs text-destructive" data-testid={`test-error-${c.id}`}>
                                {(testResults[c.id] as { error: string }).error}
                              </span>
                            ) : (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700" data-testid={`test-ok-${c.id}`}>
                                OK · {(testResults[c.id] as { ok: boolean; latency_ms: number }).latency_ms} ms
                              </span>
                            )
                          )}
                          <button
                            onClick={() => openEdit(c)}
                            className="px-2 py-1 border rounded text-xs hover:bg-accent"
                          >
                            {tc('edit')}
                          </button>
                          <button
                            onClick={() => { setDeleteTarget(c); setDeleteError('') }}
                            className="px-2 py-1 border rounded text-xs text-destructive hover:bg-destructive/10"
                          >
                            {tc('delete')}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Delete confirmation */}
        {deleteTarget && (
          <div role="dialog" aria-modal="true" className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-background border rounded-lg p-6 w-96 space-y-4 shadow-xl">
              <h2 className="font-semibold">{t('hub.llm_config_delete_confirm')}</h2>
              <p className="text-sm text-muted-foreground">{deleteTarget.label} ({deleteTarget.model_name})</p>
              {deleteError && (
                <p className="text-sm text-destructive" data-testid="delete-error">{deleteError}</p>
              )}
              <div className="flex gap-2 justify-end">
                <button onClick={() => { setDeleteTarget(null); setDeleteError('') }} className="px-3 py-2 border rounded-md text-sm">{tc('cancel')}</button>
                <button
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

        {/* Create / edit dialog */}
        {dialogOpen && (
          <div role="dialog" aria-modal="true" className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-background border rounded-lg w-full max-w-lg shadow-xl flex flex-col max-h-[90vh]">
              <div className="px-6 py-4 border-b shrink-0">
                <h2 className="font-semibold">{editing ? t('hub.llm_config_edit') : t('hub.new_llm_config')}</h2>
              </div>
              <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col flex-1 overflow-hidden">
                <div className="px-6 py-4 space-y-4 overflow-y-auto flex-1">
                  <div>
                    <label className="text-sm font-medium">{t('hub.llm_config_label')}</label>
                    <input {...register('label')} className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background" />
                    {errors.label && <p className="text-destructive text-xs mt-1">{errors.label.message}</p>}
                  </div>
                  <div>
                    <label className="text-sm font-medium">{t('hub.llm_config_provider')}</label>
                    <select
                      {...register('provider')}
                      className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                      onChange={(e) => {
                        register('provider').onChange(e)
                        if (!editing) {
                          setValue('api_key_secret_name', getDefaultApiKeySecret(e.target.value, providers))
                        }
                      }}
                    >
                      <option value="" disabled>-- {t('hub.llm_config_provider')} --</option>
                      {providers.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">{t('hub.llm_config_model')}</label>
                    <div className="flex gap-2 mt-1">
                      {!isCustomModel ? (
                        <select 
                          {...register('model_name')} 
                          className="flex-1 px-3 py-2 border rounded-md text-sm bg-background"
                          onChange={(e) => {
                            if (e.target.value === '__custom__') {
                              setIsCustomModel(true)
                            } else {
                              register('model_name').onChange(e)
                            }
                          }}
                        >
                          <option value="">-- Seleccionar de la lista --</option>
                          {availableModels.map(m => <option key={m} value={m}>{m}</option>)}
                          <option value="__custom__">Escribir manualmente...</option>
                        </select>
                      ) : (
                        <div className="flex flex-1 gap-2">
                          <input 
                            {...register('model_name')} 
                            className="flex-1 px-3 py-2 border rounded-md text-sm bg-background" 
                            placeholder="Ej: gpt-4o-custom" 
                            autoFocus
                          />
                          <button 
                            type="button" 
                            onClick={() => setIsCustomModel(false)} 
                            className="px-3 py-2 border rounded bg-muted text-xs"
                          >
                            Lista
                          </button>
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Lista de modelos obtenida dinámicamente para el proveedor seleccionado.
                    </p>
                    {errors.model_name && <p className="text-destructive text-xs mt-1">{errors.model_name.message}</p>}
                  </div>
                  <div>
                    <label className="text-sm font-medium">{t('hub.llm_config_tier')}</label>
                    <select
                      {...tierField}
                      className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
                      onChange={(e) => {
                        tierField.onChange(e)
                        if (!editing) {
                          setValue('temperature', getDefaultTemperatureForTier(Number(e.target.value)))
                        }
                      }}
                    >
                      {TIERS.map(n => <option key={n} value={n}>Tier {n}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">{t('hub.llm_config_api_key')}</label>
                    <input {...register('api_key_secret_name')} placeholder="GOOGLE_API_KEY / OPENROUTER_API_KEY" className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background font-mono" />
                    <p className="text-xs text-muted-foreground mt-1">Nombre de la variable de entorno que contiene la clave (opcional si el proveedor ya la tiene).</p>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="text-sm font-medium">Temperature</label>
                      <input type="number" step="0.1" {...register('temperature', { valueAsNumber: true })} className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background" />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Top P</label>
                      <input type="number" step="0.1" min="0" max="1" {...register('top_p', { valueAsNumber: true })} className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background" />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Max tokens (salida)</label>
                      <input type="number" {...register('max_tokens', { valueAsNumber: true })} className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background" />
                      <p className="text-xs text-muted-foreground mt-1">Por defecto: 12000 (salida). La ventana de contexto para long context se controla aparte (128K).</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <input type="checkbox" id="is_default" {...register('is_default')} className="rounded" />
                    <label htmlFor="is_default" className="text-sm">{t('hub.llm_config_is_default')}</label>
                  </div>
                </div>
                <div className="px-6 py-4 border-t flex gap-2 justify-end shrink-0">
                  <button type="button" onClick={closeDialog} className="px-3 py-2 border rounded-md text-sm">{tc('cancel')}</button>
                  <button type="submit" disabled={isPending} className="px-3 py-2 bg-primary text-primary-foreground rounded-md text-sm disabled:opacity-50">
                    {tc('save')}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const providerSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  provider_type: z.string().min(1),
  base_url: z.string().optional().nullable(),
  api_key: z.string().optional().nullable(),
})
type ProviderFormValues = z.infer<typeof providerSchema>

function ProvidersSection({ providers, isLoading }: { providers: HubProviderOut[], isLoading: boolean }) {
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()
  const [editing, setEditing] = useState<HubProviderOut | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<HubProviderOut | null>(null)
  const [deleteError, setDeleteError] = useState('')

  const createMutation = useMutation({
    mutationFn: (values: ProviderFormValues) => createProvider(values),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hub-providers'] }); closeDialog() },
  })

  const updateMutation = useMutation({
    mutationFn: (values: ProviderFormValues) => updateProvider(editing!.id, values),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hub-providers'] }); closeDialog() },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProvider(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['hub-providers'] }); setDeleteTarget(null); setDeleteError('') },
    onError: (err: Error) => setDeleteError(err.message),
  })

  const isPending = createMutation.isPending || updateMutation.isPending

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ProviderFormValues>({
    resolver: zodResolver(providerSchema),
    defaultValues: { id: '', name: '', provider_type: 'openai_compatible', base_url: '', api_key: '' },
  })

  function openCreate() {
    setEditing(null)
    reset({ id: '', name: '', provider_type: 'openai_compatible', base_url: '', api_key: '' })
    setDialogOpen(true)
  }

  function openEdit(p: HubProviderOut) {
    setEditing(p)
    reset({ id: p.id, name: p.name, provider_type: p.provider_type, base_url: p.base_url || '', api_key: p.api_key || '' })
    setDialogOpen(true)
  }

  function closeDialog() { setDialogOpen(false); setEditing(null) }

  function onSubmit(values: ProviderFormValues) {
    if (editing) updateMutation.mutate(values)
    else createMutation.mutate(values)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Proveedores de Modelos (Dinámicos)</h2>
        <button onClick={openCreate} className="px-3 py-2 border border-primary text-primary rounded-md text-sm hover:bg-primary/5 transition-colors">
          Nuevo Proveedor
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">…</p>
      ) : providers.length === 0 ? (
        <p className="text-sm text-muted-foreground">No hay proveedores definidos.</p>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-4 py-3 font-medium">ID</th>
                <th className="text-left px-4 py-3 font-medium">Nombre</th>
                <th className="text-left px-4 py-3 font-medium">Tipo</th>
                <th className="text-left px-4 py-3 font-medium">Base URL</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {providers.map(p => (
                <tr key={p.id} className="border-t hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs">{p.id}</td>
                  <td className="px-4 py-3 font-medium cursor-pointer" onClick={() => openEdit(p)}>{p.name}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-secondary/20 text-secondary-foreground font-medium">
                      {p.provider_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{p.base_url || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 justify-end">
                      <button
                        onClick={() => { setDeleteTarget(p); setDeleteError('') }}
                        className="px-2 py-1 border rounded text-xs text-destructive hover:bg-destructive/10"
                      >
                        {tc('delete')}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete confirmation for Provider */}
      {deleteTarget && (
        <div role="dialog" className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background border rounded-lg p-6 w-96 space-y-4 shadow-xl">
            <h2 className="font-semibold">Eliminar Proveedor</h2>
            <p className="text-sm text-muted-foreground">{deleteTarget.name} ({deleteTarget.id})</p>
            {deleteError && (
              <p className="text-sm text-destructive">{deleteError}</p>
            )}
            <div className="flex gap-2 justify-end">
              <button onClick={() => { setDeleteTarget(null); setDeleteError('') }} className="px-3 py-2 border rounded-md text-sm">{tc('cancel')}</button>
              <button
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

      {/* Create / edit dialog for Provider */}
      {dialogOpen && (
        <div role="dialog" className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background border rounded-lg w-full max-w-md shadow-xl flex flex-col">
            <div className="px-6 py-4 border-b shrink-0">
              <h2 className="font-semibold">{editing ? 'Editar Proveedor' : 'Nuevo Proveedor'}</h2>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col flex-1">
              <div className="px-6 py-4 space-y-4">
                <div>
                  <label className="text-sm font-medium">ID del Proveedor</label>
                  <input {...register('id')} disabled={!!editing} className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background font-mono disabled:opacity-50" placeholder="ej: mi-lmstudio" />
                  {errors.id && <p className="text-destructive text-xs mt-1">{errors.id.message}</p>}
                </div>
                <div>
                  <label className="text-sm font-medium">Nombre a mostrar</label>
                  <input {...register('name')} className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background" placeholder="ej: LM Studio Local" />
                  {errors.name && <p className="text-destructive text-xs mt-1">{errors.name.message}</p>}
                </div>
                <div>
                  <label className="text-sm font-medium">Tipo de API</label>
                  <select {...register('provider_type')} className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background">
                    <option value="openai_compatible">OpenAI Compatible (OpenRouter, LMStudio, vLLM, OpenAI)</option>
                    <option value="google_genai">Google GenAI (Gemini)</option>
                    <option value="ollama">Ollama</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Base URL (Opcional)</label>
                  <input {...register('base_url')} className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background" placeholder="http://localhost:1234/v1" />
                </div>
                <div>
                  <label className="text-sm font-medium">API Key (Opcional)</label>
                  <input type="password" {...register('api_key')} className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background" placeholder="••••••••••••" />
                  <p className="text-xs text-muted-foreground mt-1">Si se especifica, se usará en lugar de la variable de entorno.</p>
                </div>
              </div>
              <div className="px-6 py-4 border-t flex gap-2 justify-end shrink-0 bg-muted/10">
                <button type="button" onClick={closeDialog} className="px-3 py-2 border rounded-md text-sm">{tc('cancel')}</button>
                <button type="submit" disabled={isPending} className="px-3 py-2 bg-primary text-primary-foreground rounded-md text-sm disabled:opacity-50">
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
