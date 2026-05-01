const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface Chatbot {
  id: string
  name: string
  client_id: string
  llm_config_id: string
  system_prompt: string
  sources: string[]
  is_active: boolean
  retrieval_mode: 'vector' | 'long_context' | 'agentic'
  retrieval_top_k: number
  created_at: string
  updated_at: string
}

export interface ChatbotCreate {
  name: string
  client_id: string
  llm_config_id: string
  system_prompt: string
  sources?: string[]
  is_active?: boolean
  retrieval_mode?: 'vector' | 'long_context' | 'agentic'
  retrieval_top_k?: number
}

export interface ChatbotUpdate {
  name?: string
  system_prompt?: string
  sources?: string[]
  is_active?: boolean
  retrieval_mode?: 'vector' | 'long_context' | 'agentic'
  retrieval_top_k?: number
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function fetchChatbots(): Promise<Chatbot[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch chatbots')
  return res.json()
}

export async function createChatbot(data: ChatbotCreate): Promise<Chatbot> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create chatbot')
  return res.json()
}

export async function updateChatbot(id: string, data: ChatbotUpdate): Promise<Chatbot> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update chatbot')
  return res.json()
}

export async function deleteChatbot(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to delete chatbot')
}
