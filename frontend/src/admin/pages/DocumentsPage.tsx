import { useState, useCallback, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useDropzone } from 'react-dropzone'
import {
  UploadCloud, Trash2, FileText, AlertCircle, CheckCircle2,
  Clock, Loader2, Link, Globe, Play, Pause, RefreshCw,
} from 'lucide-react'

import { fetchChatbots } from '@/shared/api/chatbots'
import {
  fetchIngestionJobs, uploadDocument, deleteJob, clearCollection,
  fetchSources, createSource, updateSource, deleteSource, triggerSourceCheck,
  type IngestionJob, type IngestionSource,
} from '@/shared/api/ingestion'
import { Progress } from '@/components/ui/progress'

const INTERVAL_OPTIONS = [
  { value: 6,   label: 'Cada 6 h' },
  { value: 12,  label: 'Cada 12 h' },
  { value: 24,  label: 'Cada 24 h' },
  { value: 48,  label: 'Cada 48 h' },
  { value: 168, label: 'Semanal' },
]

export function DocumentsPage() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()

  const [selectedChatbotId, setSelectedChatbotId] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'documents' | 'sources'>('documents')

  // Documents tab state
  const [clearTarget, setClearTarget] = useState<string | null>(null)
  const [deleteJobTarget, setDeleteJobTarget] = useState<IngestionJob | null>(null)
  const [uploadError, setUploadError] = useState<string>('')
  const [canonicalUrl, setCanonicalUrl] = useState<string>('')
  const canonicalUrlRef = useRef<string>('')

  // Sources tab state
  const [newUrl, setNewUrl] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [newInterval, setNewInterval] = useState(24)
  const [sourceError, setSourceError] = useState('')
  const [deleteSourceTarget, setDeleteSourceTarget] = useState<IngestionSource | null>(null)

  // ── Chatbots ────────────────────────────────────────────────────────────────
  const { data: chatbots = [], isLoading: isLoadingChatbots } = useQuery({
    queryKey: ['chatbots'],
    queryFn: fetchChatbots,
  })

  if (!selectedChatbotId && chatbots.length > 0) {
    setSelectedChatbotId(chatbots[0].id)
  }

  // ── Jobs ────────────────────────────────────────────────────────────────────
  const { data: jobs = [], isLoading: isLoadingJobs } = useQuery({
    queryKey: ['ingestion-jobs', selectedChatbotId],
    queryFn: () => fetchIngestionJobs(selectedChatbotId),
    enabled: !!selectedChatbotId,
    refetchInterval: (query) => {
      const hasActive = query.state.data?.some(j => j.status === 'pending' || j.status === 'running')
      return hasActive ? 3000 : false
    },
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(selectedChatbotId, file, canonicalUrlRef.current || undefined),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['ingestion-jobs', selectedChatbotId] }); setUploadError('') },
    onError: (err: Error) => setUploadError(err.message),
  })

  const deleteJobMutation = useMutation({
    mutationFn: (jobId: string) => deleteJob(selectedChatbotId, jobId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['ingestion-jobs', selectedChatbotId] }); setDeleteJobTarget(null) },
  })

  const clearMutation = useMutation({
    mutationFn: () => clearCollection(selectedChatbotId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['ingestion-jobs', selectedChatbotId] }); setClearTarget(null) },
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setUploadError('')
    canonicalUrlRef.current = canonicalUrl
    for (const file of acceptedFiles) {
      if (file.size > 10 * 1024 * 1024) { setUploadError('El archivo supera el límite de 10 MB.'); continue }
      uploadMutation.mutate(file)
    }
  }, [uploadMutation, canonicalUrl])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
  })

  // ── Sources ─────────────────────────────────────────────────────────────────
  const { data: sources = [], isLoading: isLoadingSources } = useQuery({
    queryKey: ['ingestion-sources', selectedChatbotId],
    queryFn: () => fetchSources(selectedChatbotId),
    enabled: !!selectedChatbotId && activeTab === 'sources',
  })

  const createSourceMutation = useMutation({
    mutationFn: () => createSource(selectedChatbotId, {
      url: newUrl,
      label: newLabel || undefined,
      check_interval_hours: newInterval,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ingestion-sources', selectedChatbotId] })
      setNewUrl(''); setNewLabel(''); setNewInterval(24); setSourceError('')
    },
    onError: (err: Error) => setSourceError(err.message),
  })

  const toggleSourceMutation = useMutation({
    mutationFn: (source: IngestionSource) =>
      updateSource(selectedChatbotId, source.id, {
        status: source.status === 'active' ? 'paused' : 'active',
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ingestion-sources', selectedChatbotId] }),
  })

  const checkNowMutation = useMutation({
    mutationFn: (sourceId: string) => triggerSourceCheck(selectedChatbotId, sourceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ingestion-sources', selectedChatbotId] }),
  })

  const deleteSourceMutation = useMutation({
    mutationFn: (sourceId: string) => deleteSource(selectedChatbotId, sourceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ingestion-sources', selectedChatbotId] })
      setDeleteSourceTarget(null)
    },
  })

  const handleCreateSource = (e: React.FormEvent) => {
    e.preventDefault()
    setSourceError('')
    if (!newUrl.startsWith('http://') && !newUrl.startsWith('https://')) {
      setSourceError('La URL debe empezar por http:// o https://')
      return
    }
    createSourceMutation.mutate()
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header & Chatbot selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">{t('hub.documents_title', 'Documentos e Ingestión')}</h1>
          <p className="text-sm text-muted-foreground">{t('hub.documents_desc', 'Gestiona la base de conocimiento del chatbot.')}</p>
        </div>
        {chatbots.length > 0 && (
          <select
            value={selectedChatbotId}
            onChange={e => setSelectedChatbotId(e.target.value)}
            className="px-3 py-2 border rounded-md text-sm bg-background w-full sm:w-64"
          >
            {chatbots.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        )}
      </div>

      {!selectedChatbotId ? (
        <div className="p-8 text-center border border-dashed rounded-lg text-muted-foreground">
          {isLoadingChatbots ? tc('loading') : t('hub.select_chatbot_first', 'Crea o selecciona un chatbot primero')}
        </div>
      ) : (
        <>
          {/* Tabs */}
          <div className="flex border-b">
            {(['documents', 'sources'] as const).map(tab => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                {tab === 'documents'
                  ? t('hub.tab_documents', 'Documentos subidos')
                  : t('hub.tab_sources', 'Fuentes web')}
              </button>
            ))}
          </div>

          {/* ── Tab: Documentos ── */}
          {activeTab === 'documents' && (
            <div className="space-y-4">
              {/* URL canónica opcional */}
              <div className="flex items-center gap-2">
                <Link className="w-4 h-4 text-muted-foreground shrink-0" />
                <input
                  type="url"
                  value={canonicalUrl}
                  onChange={e => setCanonicalUrl(e.target.value)}
                  placeholder={t('hub.canonical_url_placeholder', 'URL pública del documento (opcional, para citar la fuente en el chat)')}
                  className="flex-1 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>

              {/* Dropzone */}
              <div
                {...getRootProps()}
                className={`p-10 border-2 border-dashed rounded-xl flex flex-col items-center justify-center text-center cursor-pointer transition-colors ${
                  isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/30'
                }`}
              >
                <input {...getInputProps()} />
                <UploadCloud className="w-10 h-10 text-muted-foreground mb-4" />
                <p className="text-sm font-medium mb-1">{t('hub.drag_drop', 'Arrastra y suelta tus archivos PDF aquí')}</p>
                <p className="text-xs text-muted-foreground">{t('hub.max_size_10mb', 'Tamaño máximo: 10 MB por archivo. Solo formato PDF.')}</p>
              </div>

              {uploadError && (
                <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                  <AlertCircle className="w-4 h-4" />{uploadError}
                </div>
              )}

              {/* Jobs table */}
              <div className="bg-card rounded-lg border overflow-hidden">
                <div className="flex items-center justify-between p-4 border-b bg-muted/20">
                  <h2 className="text-base font-medium">{t('hub.ingestion_history', 'Historial de Ingestión')}</h2>
                  {jobs.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setClearTarget(selectedChatbotId)}
                      className="flex items-center gap-2 text-xs px-3 py-1.5 text-destructive border border-destructive/30 rounded hover:bg-destructive/10 transition-colors"
                    >
                      <Trash2 className="w-3 h-3" />{t('hub.clear_collection', 'Limpiar colección')}
                    </button>
                  )}
                </div>
                {isLoadingJobs ? (
                  <div className="p-8 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />{tc('loading')}
                  </div>
                ) : jobs.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground text-sm">
                    {t('hub.no_jobs', 'No hay documentos ingeridos para este chatbot.')}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-muted/10 text-left text-muted-foreground">
                          <th className="px-4 py-3 font-medium">{t('hub.job_file', 'Archivo')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.job_source', 'Fuente')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.job_status', 'Estado')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.job_chunks', 'Chunks')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.job_date', 'Fecha')}</th>
                          <th className="px-4 py-3" />
                        </tr>
                      </thead>
                      <tbody>
                        {jobs.map(job => (
                          <tr key={job.id} className="border-b last:border-0 hover:bg-accent/20">
                            <td className="px-4 py-3 max-w-[180px] truncate" title={job.original_filename ?? job.source_url}>
                              <div className="flex items-center gap-2">
                                <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                                <span className="truncate">{job.original_filename ?? job.source_url.split('/').pop()?.split('\\').pop() ?? 'Documento'}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 max-w-[160px]">
                              {job.canonical_url ? (
                                <a href={job.canonical_url} target="_blank" rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-xs text-primary hover:underline truncate" title={job.canonical_url}>
                                  <Link className="w-3 h-3 shrink-0" />
                                  <span className="truncate">{new URL(job.canonical_url).hostname}</span>
                                </a>
                              ) : <span className="text-xs text-muted-foreground">—</span>}
                            </td>
                            <td className="px-4 py-3"><JobStatusBadge status={job.status} error={job.error_message} /></td>
                            <td className="px-4 py-3">
                              {job.status === 'running'
                                ? <div className="w-24"><Progress value={undefined} className="h-2" /></div>
                                : job.chunks_processed}
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">{new Date(job.created_at).toLocaleString()}</td>
                            <td className="px-4 py-3">
                              <button
                                type="button"
                                onClick={() => setDeleteJobTarget(job)}
                                disabled={job.status === 'pending' || job.status === 'running'}
                                className="p-1 text-muted-foreground hover:text-destructive disabled:opacity-30 transition-colors"
                                title={t('hub.delete_job', 'Eliminar documento')}
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Tab: Fuentes web ── */}
          {activeTab === 'sources' && (
            <div className="space-y-4">
              {/* Formulario nueva fuente */}
              <form onSubmit={handleCreateSource} className="bg-card border rounded-lg p-4 space-y-3">
                <h2 className="text-sm font-medium">{t('hub.add_source', 'Añadir fuente web')}</h2>
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    type="url"
                    value={newUrl}
                    onChange={e => setNewUrl(e.target.value)}
                    placeholder="https://ejemplo.com/documento.pdf"
                    required
                    className="flex-1 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                  <input
                    type="text"
                    value={newLabel}
                    onChange={e => setNewLabel(e.target.value)}
                    placeholder={t('hub.source_label_placeholder', 'Etiqueta (opcional)')}
                    className="w-full sm:w-48 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                  <select
                    value={newInterval}
                    onChange={e => setNewInterval(Number(e.target.value))}
                    className="w-full sm:w-36 px-3 py-2 text-sm border rounded-md bg-background"
                  >
                    {INTERVAL_OPTIONS.map(o => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  <button
                    type="submit"
                    disabled={createSourceMutation.isPending}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium disabled:opacity-50 flex items-center gap-2 whitespace-nowrap"
                  >
                    {createSourceMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                    {t('hub.add_source_btn', 'Añadir')}
                  </button>
                </div>
                {sourceError && (
                  <div className="flex items-center gap-2 text-sm text-destructive">
                    <AlertCircle className="w-4 h-4" />{sourceError}
                  </div>
                )}
              </form>

              {/* Tabla de fuentes */}
              <div className="bg-card rounded-lg border overflow-hidden">
                <div className="p-4 border-b bg-muted/20">
                  <h2 className="text-base font-medium">{t('hub.sources_title', 'Fuentes monitorizadas')}</h2>
                </div>
                {isLoadingSources ? (
                  <div className="p-8 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />{tc('loading')}
                  </div>
                ) : sources.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground text-sm">
                    {t('hub.no_sources', 'No hay fuentes configuradas para este chatbot.')}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-muted/10 text-left text-muted-foreground">
                          <th className="px-4 py-3 font-medium">{t('hub.source_url', 'URL')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.source_interval', 'Frecuencia')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.source_last_check', 'Última comprobación')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.source_status', 'Estado')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.source_actions', 'Acciones')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sources.map(source => (
                          <tr key={source.id} className="border-b last:border-0 hover:bg-accent/20">
                            <td className="px-4 py-3 max-w-[220px]">
                              <div className="flex items-center gap-2">
                                <Globe className="w-4 h-4 text-muted-foreground shrink-0" />
                                <div className="min-w-0">
                                  <a href={source.url} target="_blank" rel="noopener noreferrer"
                                    className="text-primary hover:underline truncate block text-xs" title={source.url}>
                                    {source.url}
                                  </a>
                                  {source.label && <span className="text-xs text-muted-foreground">{source.label}</span>}
                                </div>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">
                              {INTERVAL_OPTIONS.find(o => o.value === source.check_interval_hours)?.label
                                ?? `${source.check_interval_hours} h`}
                            </td>
                            <td className="px-4 py-3 text-muted-foreground text-xs">
                              {source.last_checked_at
                                ? new Date(source.last_checked_at).toLocaleString()
                                : t('hub.never_checked', 'Nunca')}
                            </td>
                            <td className="px-4 py-3">
                              <SourceStatusBadge source={source} />
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-1">
                                <button
                                  type="button"
                                  onClick={() => checkNowMutation.mutate(source.id)}
                                  disabled={checkNowMutation.isPending || source.status === 'paused'}
                                  title={t('hub.check_now', 'Comprobar ahora')}
                                  className="p-1 text-muted-foreground hover:text-primary disabled:opacity-30 transition-colors"
                                >
                                  <RefreshCw className="w-4 h-4" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => toggleSourceMutation.mutate(source)}
                                  title={source.status === 'active'
                                    ? t('hub.pause_source', 'Pausar')
                                    : t('hub.resume_source', 'Reanudar')}
                                  className="p-1 text-muted-foreground hover:text-primary transition-colors"
                                >
                                  {source.status === 'active'
                                    ? <Pause className="w-4 h-4" />
                                    : <Play className="w-4 h-4" />}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setDeleteSourceTarget(source)}
                                  title={t('hub.delete_source', 'Eliminar fuente')}
                                  className="p-1 text-muted-foreground hover:text-destructive transition-colors"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Diálogos de confirmación ── */}

      {deleteJobTarget && (
        <ConfirmDialog
          title={t('hub.delete_job_title', '¿Eliminar documento?')}
          description={<>{t('hub.delete_job_text', 'Se eliminarán el documento y todos sus fragmentos indexados.')}{' '}<strong>{deleteJobTarget.original_filename ?? 'Documento'}</strong></>}
          confirmLabel={t('hub.delete_confirm', 'Sí, eliminar')}
          isPending={deleteJobMutation.isPending}
          onConfirm={() => deleteJobMutation.mutate(deleteJobTarget.id)}
          onCancel={() => setDeleteJobTarget(null)}
          tc={tc}
        />
      )}

      {clearTarget && (
        <ConfirmDialog
          title={t('hub.clear_warning_title', '¿Vaciar base de conocimiento?')}
          description={t('hub.clear_warning_text', 'Esta acción eliminará todos los documentos procesados y chunks de este chatbot. No se puede deshacer.')}
          confirmLabel={t('hub.clear_confirm', 'Sí, vaciar')}
          isPending={clearMutation.isPending}
          onConfirm={() => clearMutation.mutate()}
          onCancel={() => setClearTarget(null)}
          tc={tc}
          destructive
        />
      )}

      {deleteSourceTarget && (
        <ConfirmDialog
          title={t('hub.delete_source_title', '¿Eliminar fuente?')}
          description={<>{t('hub.delete_source_text', 'Se dejará de monitorizar esta URL. Los chunks ya ingestados se mantienen.')}{' '}<strong>{deleteSourceTarget.url}</strong></>}
          confirmLabel={t('hub.delete_confirm', 'Sí, eliminar')}
          isPending={deleteSourceMutation.isPending}
          onConfirm={() => deleteSourceMutation.mutate(deleteSourceTarget.id)}
          onCancel={() => setDeleteSourceTarget(null)}
          tc={tc}
        />
      )}
    </div>
  )
}

function JobStatusBadge({ status, error }: { status: string; error: string | null }) {
  switch (status) {
    case 'completed': return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-green-100 text-green-700 border border-green-200"><CheckCircle2 className="w-3 h-3" /> Completado</span>
    case 'running':   return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-blue-100 text-blue-700 border border-blue-200"><Loader2 className="w-3 h-3 animate-spin" /> Procesando</span>
    case 'failed':    return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-red-100 text-red-700 border border-red-200" title={error || ''}><AlertCircle className="w-3 h-3" /> Error</span>
    default:          return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 border border-gray-200"><Clock className="w-3 h-3" /> En cola</span>
  }
}

function SourceStatusBadge({ source }: { source: IngestionSource }) {
  if (source.status === 'active')
    return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-green-100 text-green-700 border border-green-200"><CheckCircle2 className="w-3 h-3" /> Activa</span>
  if (source.status === 'paused')
    return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 border border-gray-200"><Pause className="w-3 h-3" /> Pausada</span>
  return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-red-100 text-red-700 border border-red-200" title={source.error_message || ''}><AlertCircle className="w-3 h-3" /> Error</span>
}

function ConfirmDialog({
  title, description, confirmLabel, isPending, onConfirm, onCancel, tc, destructive = false,
}: {
  title: string
  description: React.ReactNode
  confirmLabel: string
  isPending: boolean
  onConfirm: () => void
  onCancel: () => void
  tc: (k: string) => string
  destructive?: boolean
}) {
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 flex items-center justify-center bg-black/40 z-50 p-4">
      <div className="bg-card rounded-lg p-6 w-full max-w-md shadow-lg space-y-4">
        <h3 className={`text-lg font-semibold ${destructive ? 'text-destructive' : ''}`}>{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
        <div className="flex gap-2 justify-end pt-4">
          <button type="button" onClick={onCancel} className="px-4 py-2 border rounded-md text-sm font-medium">{tc('cancel')}</button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className="px-4 py-2 bg-destructive text-destructive-foreground rounded-md text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            {isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
