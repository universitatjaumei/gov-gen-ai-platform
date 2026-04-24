import { apiFetch } from './client'

export interface IngestionJob {
  id: string
  chatbot_id: string
  source_url: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  chunks_processed: number
  error_message: string | null
  created_at: string
}

export async function fetchIngestionJobs(chatbotId: string): Promise<IngestionJob[]> {
  const data = await apiFetch(`/hub/ingestion/${chatbotId}/jobs`)
  return data.jobs
}

export async function uploadDocument(chatbotId: string, file: File): Promise<any> {
  const formData = new FormData()
  formData.append('chatbot_id', chatbotId)
  formData.append('file', file)

  // Use native fetch to handle FormData properly instead of JSON-based apiFetch
  const token = localStorage.getItem('govgenai_token')
  const res = await fetch(`http://localhost:8000/api/v1/hub/ingestion/upload`, {
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

export async function clearCollection(chatbotId: string): Promise<any> {
  return apiFetch(`/hub/ingestion/${chatbotId}/chunks`, {
    method: 'DELETE',
  })
}
