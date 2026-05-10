// TODO CF.4: migrar funciones fetch a hooks de Orval
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

import type {
  PromptTemplateRead,
  PromptTemplateCreate,
  PromptTemplateUpdate,
} from './generated/model'

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function fetchPromptTemplates(chatbot_id?: string): Promise<PromptTemplateRead[]> {
  const qs = chatbot_id ? `?chatbot_id=${chatbot_id}` : ''
  const res = await fetch(`${API_BASE}/api/v1/hub/prompt-templates/${qs}`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch prompt templates')
  return res.json()
}

export async function createPromptTemplate(data: PromptTemplateCreate): Promise<PromptTemplateRead> {
  const res = await fetch(`${API_BASE}/api/v1/hub/prompt-templates/`, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create prompt template')
  return res.json()
}

export async function updatePromptTemplate(
  id: string,
  data: PromptTemplateUpdate,
): Promise<PromptTemplateRead> {
  const res = await fetch(`${API_BASE}/api/v1/hub/prompt-templates/${id}`, {
    method: 'PATCH',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update prompt template')
  return res.json()
}

export async function deletePromptTemplate(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/hub/prompt-templates/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to delete prompt template')
}
