import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, Trash2, FileText, AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react'

import { fetchChatbots } from '@/shared/api/chatbots'
import { fetchIngestionJobs, uploadDocument, clearCollection, type IngestionJob } from '@/shared/api/ingestion'
import { Progress } from '@/components/ui/progress'

export function DocumentsPage() {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')
  const qc = useQueryClient()

  const [selectedChatbotId, setSelectedChatbotId] = useState<string>('')
  const [clearTarget, setClearTarget] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string>('')

  // 1. Fetch Chatbots for the selector
  const { data: chatbots = [], isLoading: isLoadingChatbots } = useQuery({
    queryKey: ['chatbots'],
    queryFn: fetchChatbots,
  })

  // Set default chatbot when loaded
  if (!selectedChatbotId && chatbots.length > 0) {
    setSelectedChatbotId(chatbots[0].id)
  }

  // 2. Fetch Jobs with Polling
  const { data: jobs = [], isLoading: isLoadingJobs } = useQuery({
    queryKey: ['ingestion-jobs', selectedChatbotId],
    queryFn: () => fetchIngestionJobs(selectedChatbotId),
    enabled: !!selectedChatbotId,
    refetchInterval: (query) => {
      // Poll every 3 seconds if any job is pending or running
      const hasActiveJobs = query.state.data?.some(j => j.status === 'pending' || j.status === 'running')
      return hasActiveJobs ? 3000 : false
    },
  })

  // 3. Mutations
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(selectedChatbotId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ingestion-jobs', selectedChatbotId] })
      setUploadError('')
    },
    onError: (err: Error) => {
      setUploadError(err.message)
    }
  })

  const clearMutation = useMutation({
    mutationFn: () => clearCollection(selectedChatbotId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ingestion-jobs', selectedChatbotId] })
      setClearTarget(null)
    }
  })

  // 4. Dropzone setup
  const onDrop = useCallback((acceptedFiles: File[]) => {
    setUploadError('')
    for (const file of acceptedFiles) {
      if (file.size > 10 * 1024 * 1024) {
        setUploadError('El archivo supera el límite de 10 MB.')
        continue
      }
      uploadMutation.mutate(file)
    }
  }, [uploadMutation])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true
  })

  return (
    <div className="space-y-6">
      {/* Header & Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">{t('hub.documents_title', 'Documentos e Ingestión')}</h1>
          <p className="text-sm text-muted-foreground">{t('hub.documents_desc', 'Sube documentos PDF para alimentar la base de conocimiento del chatbot.')}</p>
        </div>
        
        {chatbots.length > 0 && (
          <select
            value={selectedChatbotId}
            onChange={(e) => setSelectedChatbotId(e.target.value)}
            className="px-3 py-2 border rounded-md text-sm bg-background w-full sm:w-64"
          >
            {chatbots.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        )}
      </div>

      {!selectedChatbotId ? (
        <div className="p-8 text-center border border-dashed rounded-lg text-muted-foreground">
          {isLoadingChatbots ? tc('loading') : t('hub.select_chatbot_first', 'Crea o selecciona un chatbot primero')}
        </div>
      ) : (
        <>
          {/* Dropzone Area */}
          <div
            {...getRootProps()}
            className={`p-10 border-2 border-dashed rounded-xl flex flex-col items-center justify-center text-center cursor-pointer transition-colors ${
              isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/30'
            }`}
          >
            <input {...getInputProps()} />
            <UploadCloud className="w-10 h-10 text-muted-foreground mb-4" />
            <p className="text-sm font-medium mb-1">
              {t('hub.drag_drop', 'Arrastra y suelta tus archivos PDF aquí')}
            </p>
            <p className="text-xs text-muted-foreground">
              {t('hub.max_size_10mb', 'Tamaño máximo: 10 MB por archivo. Solo formato PDF.')}
            </p>
          </div>
          
          {uploadError && (
            <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
              <AlertCircle className="w-4 h-4" />
              {uploadError}
            </div>
          )}

          {/* Jobs Table */}
          <div className="bg-card rounded-lg border overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b bg-muted/20">
              <h2 className="text-base font-medium">{t('hub.ingestion_history', 'Historial de Ingestión')}</h2>
              {jobs.length > 0 && (
                <button
                  type="button"
                  onClick={() => setClearTarget(selectedChatbotId)}
                  className="flex items-center gap-2 text-xs px-3 py-1.5 text-destructive border border-destructive/30 rounded hover:bg-destructive/10 transition-colors"
                >
                  <Trash2 className="w-3 h-3" />
                  {t('hub.clear_collection', 'Limpiar colección')}
                </button>
              )}
            </div>
            
            {isLoadingJobs ? (
              <div className="p-8 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> {tc('loading')}
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
                      <th className="px-4 py-3 font-medium">{t('hub.job_status', 'Estado')}</th>
                      <th className="px-4 py-3 font-medium">{t('hub.job_chunks', 'Chunks')}</th>
                      <th className="px-4 py-3 font-medium">{t('hub.job_date', 'Fecha')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map(job => (
                      <tr key={job.id} className="border-b last:border-0 hover:bg-accent/20">
                        <td className="px-4 py-3 max-w-[200px] truncate" title={job.source_url}>
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                            <span className="truncate">{job.source_url.split('/').pop()?.split('\\').pop() || 'Documento'}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <JobStatusBadge status={job.status} error={job.error_message} />
                        </td>
                        <td className="px-4 py-3">
                          {job.status === 'running' ? (
                            <div className="w-24">
                              <Progress value={undefined} className="h-2" />
                            </div>
                          ) : (
                            job.chunks_processed
                          )}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {new Date(job.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* Clear Confirmation Dialog */}
      {clearTarget && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 flex items-center justify-center bg-black/40 z-50 p-4">
          <div className="bg-card rounded-lg p-6 w-full max-w-md shadow-lg space-y-4">
            <h3 className="text-lg font-semibold text-destructive">{t('hub.clear_warning_title', '¿Vaciar base de conocimiento?')}</h3>
            <p className="text-sm text-muted-foreground">
              {t('hub.clear_warning_text', 'Esta acción eliminará todos los documentos procesados y chunks de este chatbot. No se puede deshacer.')}
            </p>
            <div className="flex gap-2 justify-end pt-4">
              <button
                type="button"
                onClick={() => setClearTarget(null)}
                className="px-4 py-2 border rounded-md text-sm font-medium"
              >
                {tc('cancel')}
              </button>
              <button
                type="button"
                onClick={() => clearMutation.mutate()}
                disabled={clearMutation.isPending}
                className="px-4 py-2 bg-destructive text-destructive-foreground rounded-md text-sm font-medium disabled:opacity-50 flex items-center gap-2"
              >
                {clearMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                {t('hub.clear_confirm', 'Sí, vaciar')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function JobStatusBadge({ status, error }: { status: string, error: string | null }) {
  switch (status) {
    case 'completed':
      return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-green-100 text-green-700 border border-green-200"><CheckCircle2 className="w-3 h-3"/> Completado</span>
    case 'running':
      return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-blue-100 text-blue-700 border border-blue-200"><Loader2 className="w-3 h-3 animate-spin"/> Procesando</span>
    case 'failed':
      return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-red-100 text-red-700 border border-red-200" title={error || ''}><AlertCircle className="w-3 h-3"/> Error</span>
    case 'pending':
    default:
      return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded bg-gray-100 text-gray-700 border border-gray-200"><Clock className="w-3 h-3"/> En cola</span>
  }
}
