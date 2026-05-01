const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface LLMConfig {
  id: string
  provider: string
  model_name: string
  temperature: number
  max_tokens: number
  api_key_secret_name: string | null
  tier: number
  label: string
  is_default: boolean
}

export interface LLMConfigCreate {
  provider: string
  model_name: string
  temperature?: number
  max_tokens?: number
  api_key_secret_name?: string | null
  tier?: number
  label?: string
  is_default?: boolean
}

export interface LLMConfigUpdate {
  label?: string
  tier?: number
  model_name?: string
  api_key_secret_name?: string | null
  is_default?: boolean
  temperature?: number
  max_tokens?: number
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function fetchLLMConfigs(): Promise<LLMConfig[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch LLM configs')
  return res.json()
}

export async function createLLMConfig(data: LLMConfigCreate): Promise<LLMConfig> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Failed to create LLM config')
  }
  return res.json()
}

export async function updateLLMConfig(id: string, data: LLMConfigUpdate): Promise<LLMConfig> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs/${id}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Failed to update LLM config')
  }
  return res.json()
}

export async function deleteLLMConfig(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Failed to delete LLM config')
  }
}

export async function testLLMConfig(id: string): Promise<{ ok: boolean; latency_ms: number }> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs/${id}/test`, {
    method: 'POST',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Connection test failed')
  }
  return res.json()
}
