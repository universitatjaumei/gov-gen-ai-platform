// TODO CF.4: migrar funciones fetch a hooks de Orval
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

import type {
  ChatbotRead,
  ChatbotCreate,
  ChatbotUpdate,
  AssignChildIn,
  CorpusStatsOut,
  RegenerateChunksOut,
} from './generated/model'

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function fetchChatbots(): Promise<ChatbotRead[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch chatbots')
  return res.json()
}

export async function createChatbot(data: ChatbotCreate): Promise<ChatbotRead> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create chatbot')
  return res.json()
}

export async function updateChatbot(id: string, data: ChatbotUpdate): Promise<ChatbotRead> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update chatbot')
  return res.json()
}

export async function fetchChatbotCorpusStats(id: string): Promise<CorpusStatsOut> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}/corpus-stats`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch chatbot corpus stats')
  return res.json()
}

export async function regenerateChatbotChunks(id: string): Promise<RegenerateChunksOut> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}/regenerate-chunks`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to regenerate chatbot chunks')
  return res.json()
}

export async function fetchChatbotChildren(id: string): Promise<ChatbotRead[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}/children`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch chatbot children')
  return res.json()
}

export async function assignChatbotChild(
  id: string,
  payload: AssignChildIn,
): Promise<ChatbotRead> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}/children`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error('Failed to assign chatbot child')
  return res.json()
}

export async function unassignChatbotChild(
  id: string,
  childId: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}/children/${childId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to unassign chatbot child')
}

export async function deleteChatbot(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to delete chatbot')
}
