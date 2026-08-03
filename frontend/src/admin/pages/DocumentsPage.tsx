import { useState, useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useDropzone } from 'react-dropzone'
import {
  UploadCloud, Trash2, FileText, AlertCircle, CheckCircle2,
  Clock, Loader2, Link, Globe, RefreshCw,
  Eye, FileUp, ChevronDown, ChevronUp, Upload,
} from 'lucide-react'

import {
  useListChatbotsApiV1HubChatbotsGet,
  useRecalculateCorpusEndpointApiV1HubChatbotsChatbotIdRecalculateCorpusPost,
} from '@/shared/api/generated/hub-chatbots/hub-chatbots'
import {
  useListDocumentsApiV1HubIngestionChatbotIdDocumentsGet,
  useGetDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdGet,
  useDeleteDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdDelete,
  useGetIngestionJobsApiV1HubIngestionChatbotIdJobsGet,
  useDeleteIngestionJobApiV1HubIngestionChatbotIdJobsJobIdDelete,
  useUploadDocumentApiV1HubIngestionUploadPost,
  useClearChatbotCollectionApiV1HubIngestionChatbotIdChunksDelete,
  getListDocumentsApiV1HubIngestionChatbotIdDocumentsGetQueryKey,
  getGetIngestionJobsApiV1HubIngestionChatbotIdJobsGetQueryKey,
} from '@/shared/api/generated/hub-ingestion/hub-ingestion'
import type {
  ChatbotRead,
  RecalculateCorpusOut,
  HubDocumentOut,
} from '@/shared/api/generated/model'
import { Progress } from '@/components/ui/progress'

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
  vector:            'Vectorial',
  RAG:               'Vectorial (RAG)',
  MD_LONG_CONTEXT:   'Contexto largo',
  MD_AGENT_SELECTOR: 'Agéntico',
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
  const [jobsOpen, setJobsOpen] = useState(false)

  const [langFilter, setLangFilter] = useState<string>('')
  const [previewDoc, setPreviewDoc] = useState<string | null>(null)
  const [deleteDocTarget, setDeleteDocTarget] = useState<HubDocumentOut | null>(null)
  const [substituteDoc, setSubstituteDoc] = useState<HubDocumentOut | null>(null)
  const [uploadError, setUploadError] = useState<string>('')
  const [recalculateConfirmOpen, setRecalculateConfirmOpen] = useState(false)
  const [recalculateError, setRecalculateError] = useState('')
  const [recalculateResult, setRecalculateResult] = useState<RecalculateCorpusOut | null>(null)
  const [canonicalUrl, setCanonicalUrl] = useState<string>('')
  const canonicalUrlRef = useRef<string>('')
  const [uploadLanguage, setUploadLanguage] = useState<string>('')
  const uploadLanguageRef = useRef<string>('')

  // ── Chatbots ────────────────────────────────────────────────────────────────
  const { data: chatbotsRaw, isLoading: isLoadingChatbots } = useListChatbotsApiV1HubChatbotsGet()
  const chatbots: ChatbotRead[] = (chatbotsRaw as unknown as ChatbotRead[] | undefined) ?? []

  if (!selectedChatbotId && chatbots.length > 0) {
    setSelectedChatbotId(chatbots[0].id)
  }

  const selectedChatbot = chatbots.find(c => c.id === selectedChatbotId)

  const documentsQueryKey = getListDocumentsApiV1HubIngestionChatbotIdDocumentsGetQueryKey(selectedChatbotId)
  const jobsQueryKey = getGetIngestionJobsApiV1HubIngestionChatbotIdJobsGetQueryKey(selectedChatbotId)

  const invalidateCorpus = () => {
    qc.invalidateQueries({ queryKey: documentsQueryKey })
    qc.invalidateQueries({ queryKey: jobsQueryKey })
  }

  // ── Documentos ──────────────────────────────────────────────────────────────
  // Se piden todos y se filtra en cliente: el desplegable de idiomas se construye
  // con los que hay en el corpus, y el total de tokens del banner es el del corpus
  // entero. Filtrar en el servidor dejaría ambas cosas midiendo el subconjunto.
  const { data: documentsData, isLoading: isLoadingDocs } =
    useListDocumentsApiV1HubIngestionChatbotIdDocumentsGet(
      selectedChatbotId,
      undefined,
      { query: { enabled: !!selectedChatbotId } },
    )
  const documents: HubDocumentOut[] = documentsData?.documents ?? []

  const { data: previewDetail, isLoading: isLoadingPreview } =
    useGetDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdGet(
      selectedChatbotId,
      previewDoc ?? '',
      { query: { enabled: !!previewDoc } },
    )

  const deleteDocMutation = useDeleteDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdDelete({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: documentsQueryKey })
        setDeleteDocTarget(null)
      },
    },
  })

  // Idiomas presentes en el corpus (para el desplegable de filtro)
  const presentLanguages = Array.from(new Set(documents.map(d => d.language))).sort()

  const filteredDocs = langFilter
    ? documents.filter(d => d.language === langFilter)
    : documents

  const totalTokens = documents.reduce((sum, d) => sum + d.token_count, 0)
  const estimatedMinutes = Math.max(1, Math.ceil(totalTokens / 120_000))

  // ── Jobs (técnico) ──────────────────────────────────────────────────────────
  const { data: jobsData, isLoading: isLoadingJobs } =
    useGetIngestionJobsApiV1HubIngestionChatbotIdJobsGet(
      selectedChatbotId,
      {
        query: {
          enabled: !!selectedChatbotId && jobsOpen,
          refetchInterval: (query) => {
            const hasActive = query.state.data?.jobs?.some(
              j => j.status === 'pending' || j.status === 'running',
            )
            return hasActive ? 3000 : false
          },
        },
      },
    )
  const jobs = jobsData?.jobs ?? []

  const deleteJobMutation = useDeleteIngestionJobApiV1HubIngestionChatbotIdJobsJobIdDelete({
    mutation: { onSuccess: () => qc.invalidateQueries({ queryKey: jobsQueryKey }) },
  })

  // ── Subida ──────────────────────────────────────────────────────────────────
  const uploadMutation = useUploadDocumentApiV1HubIngestionUploadPost({
    mutation: {
      onSuccess: () => {
        invalidateCorpus()
        setUploadError('')
        setSubstituteDoc(null)
      },
      onError: (err: Error) => setUploadError(err.message),
    },
  })

  const clearMutation = useClearChatbotCollectionApiV1HubIngestionChatbotIdChunksDelete({
    mutation: { onSuccess: invalidateCorpus },
  })

  const recalculateMutation =
    useRecalculateCorpusEndpointApiV1HubChatbotsChatbotIdRecalculateCorpusPost({
      mutation: {
        onSuccess: (data) => {
          setRecalculateError('')
          setRecalculateResult(data)
          setRecalculateConfirmOpen(false)
          invalidateCorpus()
        },
        onError: (err: Error) => setRecalculateError(err.message),
      },
    })

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setUploadError('')
    canonicalUrlRef.current = canonicalUrl
    uploadLanguageRef.current = uploadLanguage
    for (const file of acceptedFiles) {
      if (file.size > 10 * 1024 * 1024) { setUploadError('El archivo supera el límite de 10 MB.'); continue }
      uploadMutation.mutate({
        data: {
          chatbot_id: selectedChatbotId,
          file,
          canonical_url: canonicalUrlRef.current || undefined,
          language: uploadLanguageRef.current || undefined,
        },
      })
    }
  }, [uploadMutation, canonicalUrl, uploadLanguage, selectedChatbotId])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
  })

  const handleSubstitute = (doc: HubDocumentOut) => {
    setSubstituteDoc(doc)
    setCanonicalUrl(doc.canonical_url)
    setUploadLanguage(doc.language)
    canonicalUrlRef.current = doc.canonical_url
    uploadLanguageRef.current = doc.language
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Cabecera y selector de chatbot */}
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

          {recalculateMutation.isPending && (
            <div className="rounded-md border p-3 bg-muted/20">
              <p className="text-xs text-muted-foreground mb-2">
                {t('hub.recalculate_in_progress', 'Recalculando corpus...')}
              </p>
              <Progress value={null} className="h-2" />
            </div>
          )}

          {recalculateResult && (
            <div className="rounded-md border p-3 bg-green-50 border-green-200">
              <p className="text-xs text-green-800">
                {recalculateResult.message} · docs: {recalculateResult.documents_queued} · chunks +{recalculateResult.chunks_created} / -{recalculateResult.chunks_deleted}
              </p>
            </div>
          )}

          {recalculateError && (
            <div className="rounded-md border p-3 bg-destructive/10 border-destructive/30">
              <p className="text-xs text-destructive">{recalculateError}</p>
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
                  <>
                    <button
                      type="button"
                      onClick={() => {
                        setRecalculateError('')
                        setRecalculateConfirmOpen(true)
                      }}
                      disabled={recalculateMutation.isPending}
                      className="flex items-center gap-2 text-xs px-3 py-1.5 border rounded hover:bg-accent transition-colors disabled:opacity-50"
                    >
                      <RefreshCw className="w-3 h-3" />{t('hub.recalculate_corpus', 'Recalcular corpus')}
                    </button>
                    <button
                      type="button"
                      onClick={() => clearMutation.mutate({ chatbotId: selectedChatbotId })}
                      disabled={clearMutation.isPending}
                      className="flex items-center gap-2 text-xs px-3 py-1.5 text-destructive border border-destructive/30 rounded hover:bg-destructive/10 transition-colors disabled:opacity-50"
                    >
                      <Trash2 className="w-3 h-3" />{t('hub.clear_collection', 'Limpiar colección')}
                    </button>
                  </>
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
                          {doc.created_at ? new Date(doc.created_at).toLocaleString() : '—'}
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

          {/* Jobs (técnico) — desplegable */}
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
                          <td className="px-4 py-3"><JobStatusBadge status={job.status} error={job.error_message ?? null} /></td>
                          <td className="px-4 py-3 text-xs text-muted-foreground">
                            {job.status === 'running'
                              ? <div className="w-16"><Progress value={null} className="h-2" /></div>
                              : job.chunks_processed}
                          </td>
                          <td className="px-4 py-3 text-xs text-muted-foreground">{new Date(job.created_at).toLocaleString()}</td>
                          <td className="px-4 py-3">
                            <button
                              type="button"
                              onClick={() => deleteJobMutation.mutate({ chatbotId: selectedChatbotId, jobId: job.id })}
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
          onConfirm={() => deleteDocMutation.mutate({ chatbotId: selectedChatbotId, documentId: deleteDocTarget.id })}
          onCancel={() => setDeleteDocTarget(null)}
          tc={tc}
        />
      )}

      {recalculateConfirmOpen && (
        <ConfirmDialog
          title={t('hub.recalculate_title', '¿Recalcular corpus?')}
          description={
            selectedChatbot?.retrieval_mode === 'RAG'
              ? (
                <>
                  {t('hub.recalculate_vector_text', 'Se re-generarán embeddings para todos los documentos.')}{' '}
                  <strong>{documents.length}</strong> docs · ~{formatTokens(totalTokens)} tokens · ~{estimatedMinutes} min.
                </>
              )
              : (
                <>
                  {t('hub.recalculate_non_vector_text', 'Se eliminarán los chunks vectoriales; los documentos markdown se mantienen.')}{' '}
                  <strong>{documents.length}</strong> docs.
                </>
              )
          }
          confirmLabel={t('hub.recalculate_confirm', 'Sí, recalcular')}
          isPending={recalculateMutation.isPending}
          onConfirm={() => recalculateMutation.mutate({ chatbotId: selectedChatbotId })}
          onCancel={() => setRecalculateConfirmOpen(false)}
          tc={tc}
        />
      )}
    </div>
  )
}

// ── Sub-componentes ───────────────────────────────────────────────────────────

function RetrievalBanner({
  mode, totalTokens, t,
}: {
  mode: string
  totalTokens: number
  t: (k: string, d?: string) => string
}) {
  const modeLabel = RETRIEVAL_LABELS[mode] ?? mode
  const recommendation =
    mode === 'RAG'             ? t('hub.retrieval_rec_vector', 'Usa RAG para documentos extensos.')
    : mode === 'MD_LONG_CONTEXT' ? t('hub.retrieval_rec_lc', 'El documento completo se envía al LLM en cada consulta.')
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
