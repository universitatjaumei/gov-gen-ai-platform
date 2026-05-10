// TODO CF.4: migrar funciones fetch a hooks de Orval
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

import type {
  LLMConfigRead,
  LLMConfigCreate,
  LLMConfigUpdate,
  HubProviderOut,
  HubProviderCreate,
  HubProviderUpdate,
} from './generated/model'

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function fetchLLMConfigs(): Promise<LLMConfigRead[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch LLM configs')
  return res.json()
}

export async function createLLMConfig(data: LLMConfigCreate): Promise<LLMConfigRead> {
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

export async function updateLLMConfig(id: string, data: LLMConfigUpdate): Promise<LLMConfigRead> {
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

export async function fetchAvailableModels(provider: string): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs/available-models/${provider}`, {
    headers: authHeaders(),
  })
  if (!res.ok) {
    console.warn(`Failed to fetch models for ${provider}`)
    return []
  }
  const data = await res.json()
  return data.models || []
}

export async function fetchProviders(): Promise<HubProviderOut[]> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs/providers`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to fetch providers')
  return res.json()
}

export async function createProvider(data: HubProviderCreate): Promise<HubProviderOut> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs/providers`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Failed to create provider')
  }
  return res.json()
}

export async function updateProvider(id: string, data: HubProviderUpdate): Promise<HubProviderOut> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs/providers/${id}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Failed to update provider')
  }
  return res.json()
}

export async function deleteProvider(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/hub/llm-configs/providers/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Failed to delete provider')
  }
}
