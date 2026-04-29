const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export interface IngestionJob {
  id: string
  chatbot_id: string
  source_url: string
  original_filename: string | null
  canonical_url: string | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  chunks_processed: number
  error_message: string | null
  created_at: string
}

export async function fetchIngestionJobs(chatbotId: string): Promise<IngestionJob[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/ingestion/${chatbotId}/jobs`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch jobs')
  const data = await res.json()
  return data.jobs
}

export async function uploadDocument(chatbotId: string, file: File, canonicalUrl?: string, language?: string): Promise<any> {
  const formData = new FormData()
  formData.append('chatbot_id', chatbotId)
  formData.append('file', file)
  if (canonicalUrl) formData.append('canonical_url', canonicalUrl)
  if (language) formData.append('language', language)

  const token = localStorage.getItem('access_token')
  const res = await fetch(`${API_BASE}/api/v1/hub/ingestion/upload`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => null)
    throw new Error(errorData?.detail || `Error al subir el archivo (${res.status})`)
  }

  return res.json()
}

export async function deleteJob(chatbotId: string, jobId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/hub/ingestion/${chatbotId}/jobs/${jobId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to delete job')
  return res.json()
}

export interface IngestionSource {
  id: string
  chatbot_id: string
  url: string
  label: string | null
  check_interval_hours: number
  last_checked_at: string | null
  last_content_hash: string | null
  status: 'active' | 'paused' | 'error'
  error_message: string | null
  created_at: string
}

export async function fetchSources(chatbotId: string): Promise<IngestionSource[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/ingestion/${chatbotId}/sources`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch sources')
  return (await res.json()).sources
}

export async function createSource(
  chatbotId: string,
  body: { url: string; label?: string; check_interval_hours?: number; language?: string },
): Promise<IngestionSource> {
  const res = await fetch(`${API_BASE}/api/v1/hub/ingestion/${chatbotId}/sources`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(err?.detail || `Error al crear fuente (${res.status})`)
  }
  return (await res.json()).source
}

export async function updateSource(
  chatbotId: string,
  sourceId: string,
  body: { label?: string | null; check_interval_hours?: number; status?: 'active' | 'paused' },
): Promise<IngestionSource> {
  const res = await fetch(`${API_BASE}/api/v1/hub/ingestion/${chatbotId}/sources/${sourceId}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error('Failed to update source')
  return (await res.json()).source
}

export async function deleteSource(chatbotId: string, sourceId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/hub/ingestion/${chatbotId}/sources/${sourceId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to delete source')
  return res.json()
}

export async function triggerSourceCheck(chatbotId: string, sourceId: string): Promise<any> {
  const res = await fetch(
    `${API_BASE}/api/v1/hub/ingestion/${chatbotId}/sources/${sourceId}/check`,
    { method: 'POST', headers: authHeaders() },
  )
  if (!res.ok) throw new Error('Failed to trigger check')
  return res.json()
}

export async function clearCollection(chatbotId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/v1/hub/ingestion/${chatbotId}/chunks`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to clear collection')
  return res.json()
}

export interface HubDocument {
  id: string
  chatbot_id: string
  title: string
  canonical_url: string
  language: string
  source_kind: 'upload' | 'crawler' | 'manual'
  token_count: number
  created_at: string
  updated_at: string
}

export interface HubDocumentDetail extends HubDocument {
  markdown_content: string
}

export async function fetchDocuments(chatbotId: string, language?: string): Promise<HubDocument[]> {
  const params = language ? `?language=${encodeURIComponent(language)}` : ''
  const res = await fetch(
    `${API_BASE}/api/v1/hub/ingestion/${chatbotId}/documents${params}`,
    { headers: authHeaders() },
  )
  if (!res.ok) throw new Error('Failed to fetch documents')
  return (await res.json()).documents
}

export async function fetchDocument(chatbotId: string, documentId: string): Promise<HubDocumentDetail> {
  const res = await fetch(
    `${API_BASE}/api/v1/hub/ingestion/${chatbotId}/documents/${documentId}`,
    { headers: authHeaders() },
  )
  if (!res.ok) throw new Error('Failed to fetch document')
  return res.json()
}

export async function deleteDocument(chatbotId: string, documentId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/v1/hub/ingestion/${chatbotId}/documents/${documentId}`,
    { method: 'DELETE', headers: authHeaders() },
  )
  if (!res.ok) throw new Error('Failed to delete document')
}
