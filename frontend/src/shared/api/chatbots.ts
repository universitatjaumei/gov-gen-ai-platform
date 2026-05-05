const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface Chatbot {
  id: string
  name: string
  client_id: string
  llm_config_id: string
  system_prompt: string
  sources: string[]
  is_active: boolean
  retrieval_mode: 'RAG' | 'MD_LONG_CONTEXT' | 'MD_AGENT_SELECTOR'
  retrieval_top_k: number
  use_prompt_caching: boolean
  cache_ttl: number
  kind: 'atomic' | 'router'
  parent_chatbot_id: string | null
  public_graph_profile: string
  language_mode: string
  quality_threshold: number
  min_retrieval_results: number
  min_retrieval_score: number
  reranker_enabled: boolean
  answer_template: string
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
  retrieval_mode?: 'RAG' | 'MD_LONG_CONTEXT' | 'MD_AGENT_SELECTOR'
  retrieval_top_k?: number
  use_prompt_caching?: boolean
  cache_ttl?: number
  kind?: 'atomic' | 'router'
  public_graph_profile?: string
  language_mode?: string
  quality_threshold?: number
  min_retrieval_results?: number
  min_retrieval_score?: number
  reranker_enabled?: boolean
  answer_template?: string
}

export interface ChatbotUpdate {
  name?: string
  system_prompt?: string
  sources?: string[]
  is_active?: boolean
  retrieval_mode?: 'RAG' | 'MD_LONG_CONTEXT' | 'MD_AGENT_SELECTOR'
  retrieval_top_k?: number
  use_prompt_caching?: boolean
  cache_ttl?: number
  kind?: 'atomic' | 'router'
  parent_chatbot_id?: string | null
  public_graph_profile?: string
  language_mode?: string
  quality_threshold?: number
  min_retrieval_results?: number
  min_retrieval_score?: number
  reranker_enabled?: boolean
  answer_template?: string
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

export interface AssignChildPayload {
  child_chatbot_id: string
}

export interface CorpusStats {
  total_documents: number
  total_tokens: number
  by_language: Record<string, number>
  recommended_mode: 'RAG' | 'MD_LONG_CONTEXT' | 'MD_AGENT_SELECTOR'
  recommendation_reason: string
}

export interface RegenerateChunksResponse {
  task_id: string
  message: string
  documents_processed: number
  chunks_created: number
}

export async function fetchChatbotCorpusStats(id: string): Promise<CorpusStats> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}/corpus-stats`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch chatbot corpus stats')
  return res.json()
}

export async function regenerateChatbotChunks(
  id: string,
): Promise<RegenerateChunksResponse> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}/regenerate-chunks`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to regenerate chatbot chunks')
  return res.json()
}

export async function fetchChatbotChildren(id: string): Promise<Chatbot[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/chatbots/${id}/children`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch chatbot children')
  return res.json()
}

export async function assignChatbotChild(
  id: string,
  payload: AssignChildPayload,
): Promise<Chatbot> {
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
