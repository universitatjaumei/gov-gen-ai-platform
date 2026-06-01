// TODO CF.4: migrar a hooks Orval cuando openapi.json se regenere con /redaccion/copilot/*.
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

import type { CopilotActionKind } from '../useFocusStore'

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export interface CopilotSourceRef {
  path: string
  chunk_idx: number
  excerpt: string
  module: 'redaccion' | 'chatbots' | 'general'
}

export interface CopilotAnswerResponse {
  answer: string
  source_refs: CopilotSourceRef[]
}

export interface CopilotTranslateResponse {
  kind: CopilotActionKind
  payload: Record<string, unknown>
}

export async function askCopilot(params: {
  question: string
  module?: 'redaccion' | 'chatbots' | 'general' | null
  top_k?: number
}): Promise<CopilotAnswerResponse> {
  const res = await fetch(`${API_BASE}/api/v1/redaccion/copilot/ask`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({
      question: params.question,
      module: params.module ?? null,
      top_k: params.top_k ?? 4,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Copilot ask failed')
  }
  return res.json()
}

export async function translateCopilot(params: {
  instruction: string
  target_kind: CopilotActionKind
  sample_schema?: Record<string, unknown>
}): Promise<CopilotTranslateResponse> {
  const res = await fetch(`${API_BASE}/api/v1/redaccion/copilot/translate`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({
      instruction: params.instruction,
      target_kind: params.target_kind,
      sample_schema: params.sample_schema,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? 'Copilot translate failed')
  }
  return res.json()
}
