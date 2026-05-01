import { useState, useCallback, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useDropzone } from 'react-dropzone'
import {
  UploadCloud, Trash2, FileText, AlertCircle, CheckCircle2,
  Clock, Loader2, Link, Globe, Play, Pause, RefreshCw,
  Eye, FileUp, ChevronDown, ChevronUp, Upload,
} from 'lucide-react'

import { fetchChatbots } from '@/shared/api/chatbots'
import {
  fetchIngestionJobs, uploadDocument, deleteJob, clearCollection,
  fetchSources, createSource, updateSource, deleteSource, triggerSourceCheck,
  fetchDocuments, fetchDocument, deleteDocument,
  type IngestionSource, type HubDocument,
} from '@/shared/api/ingestion'
import { Progress } from '@/components/ui/progress'

const INTERVAL_OPTIONS = [
  { value: 6,   label: 'Cada 6 h' },
  { value: 12,  label: 'Cada 12 h' },
  { value: 24,  label: 'Cada 24 h' },
  { value: 48,  label: 'Cada 48 h' },
  { value: 168, label: 'Semanal' },
]

const LANGUAGE_OPTIONS = [
  { value: '',   label: 'Auto-detectar' },
  { value: 'es', label: 'Español' },
  { value: 'ca', label: 'Català' },
  { value: 'en', label: 'English' },
]

const LANG_BADGE: Record<string, string> = {
  es: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  ca: 'bg-red-100 text-red-800 border-red-200',
  en: 'bg-blue-100 text-blue-800 border-blue-200',
}

const RETRIEVAL_LABELS: Record<string, string> = {
  vector:       'Vectorial (RAG)',
  long_context: 'Contexto largo',
  agentic:      'Agéntico',
}

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)} k`
  return String(n)
}

export function DocumentsPage() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()

  const [selectedChatbotId, setSelectedChatbotId] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'documents' | 'sources'>('documents')
  const [jobsOpen, setJobsOpen] = useState(false)

  // Documents tab state
  const [langFilter, setLangFilter] = useState<string>('')
  const [previewDoc, setPreviewDoc] = useState<string | null>(null)
  const [deleteDocTarget, setDeleteDocTarget] = useState<HubDocument | null>(null)
  const [substituteDoc, setSubstituteDoc] = useState<HubDocument | null>(null)
  const [uploadError, setUploadError] = useState<string>('')
  const [canonicalUrl, setCanonicalUrl] = useState<string>('')
  const canonicalUrlRef = useRef<string>('')
  const [uploadLanguage, setUploadLanguage] = useState<string>('')
  const uploadLanguageRef = useRef<string>('')

  // Sources tab state
  const [newUrl, setNewUrl] = useState('')
  const [newLabel, setNewLabel] = useState('')
  const [newInterval, setNewInterval] = useState(24)
  const [newSourceLanguage, setNewSourceLanguage] = useState('')
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

  const selectedChatbot = chatbots.find(c => c.id === selectedChatbotId)

  // ── Documents ───────────────────────────────────────────────────────────────
  const { data: documents = [], isLoading: isLoadingDocs } = useQuery({
    queryKey: ['hub-documents', selectedChatbotId],
    queryFn: () => fetchDocuments(selectedChatbotId),
    enabled: !!selectedChatbotId,
  })

  const { data: previewDetail, isLoading: isLoadingPreview } = useQuery({
    queryKey: ['hub-document-detail', selectedChatbotId, previewDoc],
    queryFn: () => fetchDocument(selectedChatbotId, previewDoc!),
    enabled: !!previewDoc,
  })

  const deleteDocMutation = useMutation({
    mutationFn: (docId: string) => deleteDocument(selectedChatbotId, docId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hub-documents', selectedChatbotId] })
      setDeleteDocTarget(null)
    },
  })

  // Languages present in document list (for filter dropdown)
  const presentLanguages = Array.from(new Set(documents.map(d => d.language))).sort()

  const filteredDocs = langFilter
    ? documents.filter(d => d.language === langFilter)
    : documents

  const totalTokens = documents.reduce((sum, d) => sum + d.token_count, 0)

  // ── Jobs (técnico) ──────────────────────────────────────────────────────────
  const { data: jobs = [], isLoading: isLoadingJobs } = useQuery({
    queryKey: ['ingestion-jobs', selectedChatbotId],
    queryFn: () => fetchIngestionJobs(selectedChatbotId),
    enabled: !!selectedChatbotId && jobsOpen,
    refetchInterval: (query) => {
      const hasActive = query.state.data?.some(j => j.status === 'pending' || j.status === 'running')
      return hasActive ? 3000 : false
    },
  })

  const deleteJobMutation = useMutation({
    mutationFn: (jobId: string) => deleteJob(selectedChatbotId, jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ingestion-jobs', selectedChatbotId] }),
  })

  // ── Upload ──────────────────────────────────────────────────────────────────
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(
      selectedChatbotId,
      file,
      canonicalUrlRef.current || undefined,
      uploadLanguageRef.current || undefined,
    ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hub-documents', selectedChatbotId] })
      qc.invalidateQueries({ queryKey: ['ingestion-jobs', selectedChatbotId] })
      setUploadError('')
      setSubstituteDoc(null)
    },
    onError: (err: Error) => setUploadError(err.message),
  })

  const clearMutation = useMutation({
    mutationFn: () => clearCollection(selectedChatbotId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hub-documents', selectedChatbotId] })
      qc.invalidateQueries({ queryKey: ['ingestion-jobs', selectedChatbotId] })
    },
  })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setUploadError('')
    canonicalUrlRef.current = canonicalUrl
    uploadLanguageRef.current = uploadLanguage
    for (const file of acceptedFiles) {
      if (file.size > 10 * 1024 * 1024) { setUploadError('El archivo supera el límite de 10 MB.'); continue }
      uploadMutation.mutate(file)
    }
  }, [uploadMutation, canonicalUrl, uploadLanguage])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
  })

  const handleSubstitute = (doc: HubDocument) => {
    setSubstituteDoc(doc)
    setCanonicalUrl(doc.canonical_url)
    setUploadLanguage(doc.language)
    canonicalUrlRef.current = doc.canonical_url
    uploadLanguageRef.current = doc.language
  }

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
      language: newSourceLanguage || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ingestion-sources', selectedChatbotId] })
      setNewUrl(''); setNewLabel(''); setNewInterval(24); setNewSourceLanguage(''); setSourceError('')
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
                  ? t('hub.tab_documents', 'Documentos')
                  : t('hub.tab_sources', 'Fuentes web')}
              </button>
            ))}
          </div>

          {/* ── Tab: Documentos ── */}
          {activeTab === 'documents' && (
            <div className="space-y-4">
              {/* Banner de modo retrieval */}
              {selectedChatbot && (
                <RetrievalBanner
                  mode={selectedChatbot.retrieval_mode}
                  totalTokens={totalTokens}
                  t={t as (k: string, d?: string) => string}
                />
              )}

              {/* Subida + controles */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
                <div className="flex flex-1 items-center gap-2">
                  <Link className="w-4 h-4 text-muted-foreground shrink-0" />
                  <input
                    type="url"
                    value={canonicalUrl}
                    onChange={e => setCanonicalUrl(e.target.value)}
                    placeholder={t('hub.canonical_url_placeholder', 'URL pública del documento (opcional)')}
                    className="flex-1 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <select
                  value={uploadLanguage}
                  onChange={e => setUploadLanguage(e.target.value)}
                  className="w-full sm:w-40 px-3 py-2 text-sm border rounded-md bg-background"
                  aria-label={t('hub.language_label', 'Idioma')}
                >
                  {LANGUAGE_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              {substituteDoc && (
                <div className="flex items-center gap-2 p-3 text-sm bg-yellow-50 border border-yellow-200 rounded-md">
                  <Upload className="w-4 h-4 text-yellow-600 shrink-0" />
                  <span>{t('hub.substituting', 'Sustituyendo')}:</span>
                  <strong className="truncate">{substituteDoc.title}</strong>
                  <button
                    type="button"
                    onClick={() => { setSubstituteDoc(null); setCanonicalUrl(''); setUploadLanguage('') }}
                    className="ml-auto text-xs text-muted-foreground hover:text-foreground"
                  >{tc('cancel')}</button>
                </div>
              )}

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

              {/* Tabla de documentos */}
              <div className="bg-card rounded-lg border overflow-hidden">
                <div className="flex items-center justify-between p-4 border-b bg-muted/20 gap-3 flex-wrap">
                  <h2 className="text-base font-medium">{t('hub.documents_table_title', 'Documentos del corpus')}</h2>
                  <div className="flex items-center gap-2 ml-auto">
                    {presentLanguages.length > 1 && (
                      <select
                        value={langFilter}
                        onChange={e => setLangFilter(e.target.value)}
                        className="px-2 py-1 text-xs border rounded-md bg-background"
                        aria-label={t('hub.filter_by_language', 'Filtrar por idioma')}
                      >
                        <option value="">{t('hub.all_languages', 'Todos los idiomas')}</option>
                        {presentLanguages.map(l => (
                          <option key={l} value={l}>{l.toUpperCase()}</option>
                        ))}
                      </select>
                    )}
                    {documents.length > 0 && (
                      <button
                        type="button"
                        onClick={() => clearMutation.mutate()}
                        disabled={clearMutation.isPending}
                        className="flex items-center gap-2 text-xs px-3 py-1.5 text-destructive border border-destructive/30 rounded hover:bg-destructive/10 transition-colors disabled:opacity-50"
                      >
                        <Trash2 className="w-3 h-3" />{t('hub.clear_collection', 'Limpiar colección')}
                      </button>
                    )}
                  </div>
                </div>

                {isLoadingDocs ? (
                  <div className="p-8 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />{tc('loading')}
                  </div>
                ) : filteredDocs.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground text-sm">
                    {t('hub.no_documents', 'No hay documentos ingestados para este chatbot.')}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-muted/10 text-left text-muted-foreground">
                          <th className="px-4 py-3 font-medium">{t('hub.doc_title', 'Título')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.doc_source', 'Fuente')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.doc_language', 'Idioma')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.doc_tokens', 'Tokens')}</th>
                          <th className="px-4 py-3 font-medium">{t('hub.doc_date', 'Fecha')}</th>
                          <th className="px-4 py-3" />
                        </tr>
                      </thead>
                      <tbody>
                        {filteredDocs.map(doc => (
                          <tr key={doc.id} className="border-b last:border-0 hover:bg-accent/20">
                            <td className="px-4 py-3 max-w-[220px]">
                              <div className="flex items-center gap-2">
                                <SourceKindIcon kind={doc.source_kind} />
                                <span className="truncate font-medium" title={doc.title}>{doc.title}</span>
                              </div>
                              {doc.canonical_url?.startsWith('http') && (
                                <a
                                  href={doc.canonical_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-xs text-primary hover:underline mt-0.5 ml-6 truncate"
                                  title={doc.canonical_url}
                                >
                                  <Link className="w-3 h-3 shrink-0" />
                                  {new URL(doc.canonical_url).hostname}
                                </a>
                              )}
                            </td>
                            <td className="px-4 py-3">
                              <SourceKindBadge kind={doc.source_kind} t={t} />
                            </td>
                            <td className="px-4 py-3">
                              <LanguageBadge language={doc.language} />
                            </td>
                            <td className="px-4 py-3 text-muted-foreground tabular-nums">
                              {formatTokens(doc.token_count)}
                            </td>
                            <td className="px-4 py-3 text-muted-foreground text-xs whitespace-nowrap">
                              {new Date(doc.created_at).toLocaleString()}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-1">
                                <button
                                  type="button"
                                  onClick={() => setPreviewDoc(doc.id)}
                                  title={t('hub.preview_doc', 'Ver contenido')}
                                  className="p-1 text-muted-foreground hover:text-primary transition-colors"
                                >
                                  <Eye className="w-4 h-4" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleSubstitute(doc)}
                                  title={t('hub.substitute_doc', 'Sustituir documento')}
                                  className="p-1 text-muted-foreground hover:text-primary transition-colors"
                                >
                                  <FileUp className="w-4 h-4" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setDeleteDocTarget(doc)}
                                  title={t('hub.delete_doc', 'Eliminar documento')}
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

              {/* Jobs (técnico) — Disclosure */}
              <div className="border rounded-lg overflow-hidden">
                <button
                  type="button"
                  onClick={() => setJobsOpen(v => !v)}
                  className="w-full flex items-center justify-between p-4 bg-muted/10 text-sm font-medium hover:bg-muted/20 transition-colors"
                >
                  <span>{t('hub.jobs_technical', 'Jobs (técnico)')}</span>
                  {jobsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {jobsOpen && (
                  isLoadingJobs ? (
                    <div className="p-6 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />{tc('loading')}
                    </div>
                  ) : jobs.length === 0 ? (
                    <div className="p-6 text-center text-muted-foreground text-sm">
                      {t('hub.no_jobs', 'No hay jobs de ingestión registrados.')}
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b bg-muted/10 text-left text-muted-foreground">
                            <th className="px-4 py-3 font-medium">{t('hub.job_file', 'Archivo')}</th>
                            <th className="px-4 py-3 font-medium">{t('hub.job_status', 'Estado')}</th>
                            <th className="px-4 py-3 font-medium">{t('hub.job_chunks', 'Chunks')}</th>
                            <th className="px-4 py-3 font-medium">{t('hub.job_date', 'Fecha')}</th>
                            <th className="px-4 py-3" />
                          </tr>
                        </thead>
                        <tbody>
                          {jobs.map(job => (
                            <tr key={job.id} className="border-b last:border-0 hover:bg-accent/20">
                              <td className="px-4 py-3 max-w-[200px] truncate text-xs" title={job.original_filename ?? job.source_url}>
                                {job.original_filename ?? job.source_url.split('/').pop() ?? 'Documento'}
                              </td>
                              <td className="px-4 py-3"><JobStatusBadge status={job.status} error={job.error_message} /></td>
                              <td className="px-4 py-3 text-xs text-muted-foreground">
                                {job.status === 'running'
                                  ? <div className="w-16"><Progress value={null} className="h-2" /></div>
                                  : job.chunks_processed}
                              </td>
                              <td className="px-4 py-3 text-xs text-muted-foreground">{new Date(job.created_at).toLocaleString()}</td>
                              <td className="px-4 py-3">
                                <button
                                  type="button"
                                  onClick={() => deleteJobMutation.mutate(job.id)}
                                  disabled={job.status === 'pending' || job.status === 'running'}
                                  className="p-1 text-muted-foreground hover:text-destructive disabled:opacity-30 transition-colors"
                                  title={t('hub.delete_job', 'Eliminar job')}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )
                )}
              </div>
            </div>
          )}

          {/* ── Tab: Fuentes web ── */}
          {activeTab === 'sources' && (
            <div className="space-y-4">
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
                  <select
                    value={newSourceLanguage}
                    onChange={e => setNewSourceLanguage(e.target.value)}
                    className="w-full sm:w-40 px-3 py-2 text-sm border rounded-md bg-background"
                    aria-label={t('hub.language_label', 'Idioma')}
                  >
                    {LANGUAGE_OPTIONS.map(o => (
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

      {/* ── Modal de preview ── */}
      {previewDoc && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 flex items-center justify-center bg-black/40 z-50 p-4">
          <div className="bg-card rounded-lg w-full max-w-3xl max-h-[80vh] flex flex-col shadow-xl">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-base font-semibold truncate">
                {isLoadingPreview ? tc('loading') : previewDetail?.title}
              </h3>
              <button
                type="button"
                onClick={() => setPreviewDoc(null)}
                className="p-1 text-muted-foreground hover:text-foreground"
              >✕</button>
            </div>
            <div className="overflow-y-auto p-4 flex-1">
              {isLoadingPreview ? (
                <div className="flex items-center justify-center gap-2 text-muted-foreground py-8">
                  <Loader2 className="w-5 h-5 animate-spin" />{tc('loading')}
                </div>
              ) : (
                <pre className="text-xs whitespace-pre-wrap font-mono text-foreground/80">
                  {previewDetail?.markdown_content}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Diálogos de confirmación ── */}
      {deleteDocTarget && (
        <ConfirmDialog
          title={t('hub.delete_doc_title', '¿Eliminar documento?')}
          description={<>{t('hub.delete_doc_text', 'Se eliminarán el documento y todos sus chunks indexados.')}{' '}<strong>{deleteDocTarget.title}</strong></>}
          confirmLabel={t('hub.delete_confirm', 'Sí, eliminar')}
          isPending={deleteDocMutation.isPending}
          onConfirm={() => deleteDocMutation.mutate(deleteDocTarget.id)}
          onCancel={() => setDeleteDocTarget(null)}
          tc={tc}
        />
      )}

      {deleteSourceTarget && (
        <ConfirmDialog
          title={t('hub.delete_source_title', '¿Eliminar fuente?')}
          description={<>{t('hub.delete_source_text', 'Se dejará de monitorizar esta URL. Los documentos ya ingestados se mantienen.')}{' '}<strong>{deleteSourceTarget.url}</strong></>}
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

// ── Sub-components ────────────────────────────────────────────────────────────

function RetrievalBanner({
  mode, totalTokens, t,
}: {
  mode: string
  totalTokens: number
  t: (k: string, d?: string) => string
}) {
  const modeLabel = RETRIEVAL_LABELS[mode] ?? mode
  const recommendation =
    mode === 'vector'      ? t('hub.retrieval_rec_vector', 'Usa RAG para documentos extensos.')
    : mode === 'long_context' ? t('hub.retrieval_rec_lc', 'El documento completo se envía al LLM en cada consulta.')
    : t('hub.retrieval_rec_agentic', 'El agente decide qué fragmentos leer.')

  return (
    <div className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm">
      <div className="flex-1">
        <span className="font-medium">{t('hub.retrieval_mode_label', 'Modo de retrieval')}: </span>
        <strong>{modeLabel}</strong>
        {totalTokens > 0 && (
          <span className="text-muted-foreground"> — {formatTokens(totalTokens)} tokens totales</span>
        )}
        <p className="text-muted-foreground mt-0.5 text-xs">{recommendation}</p>
      </div>
    </div>
  )
}

function SourceKindIcon({ kind }: { kind: string }) {
  if (kind === 'crawler') return <Globe className="w-4 h-4 text-muted-foreground shrink-0" />
  return <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
}

function SourceKindBadge({ kind, t }: { kind: string; t: (k: string, d: string) => string }) {
  if (kind === 'crawler')
    return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-purple-100 text-purple-700 border border-purple-200"><Globe className="w-3 h-3" />{t('hub.kind_crawler', 'Web')}</span>
  return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 border border-gray-200"><FileText className="w-3 h-3" />{t('hub.kind_upload', 'PDF')}</span>
}

function LanguageBadge({ language }: { language: string }) {
  const cls = LANG_BADGE[language] ?? 'bg-gray-100 text-gray-700 border-gray-200'
  return (
    <span className={`inline-flex items-center text-xs px-2 py-0.5 rounded border font-medium ${cls}`}>
      {language.toUpperCase()}
    </span>
  )
}

function JobStatusBadge({ status, error }: { status: string; error: string | null }) {
  switch (status) {
    case 'completed': return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-green-100 text-green-700 border border-green-200"><CheckCircle2 className="w-3 h-3" /> Completado</span>
    case 'running':   return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-blue-100 text-blue-700 border border-blue-200"><Loader2 className="w-3 h-3 animate-spin" /> Procesando</span>
    case 'failed':    return (
      <div>
        <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-red-100 text-red-700 border border-red-200"><AlertCircle className="w-3 h-3" /> Error</span>
        {error && <p className="text-xs text-red-600 mt-1 max-w-xs break-words">{error}</p>}
      </div>
    )
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
