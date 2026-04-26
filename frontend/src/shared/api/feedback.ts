const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface Interaction {
  id: string
  user_message: string
  assistant_message: string
  feedback_score: number | null
  feedback_text: string | null
  run_id: string | null
  created_at: string
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export async function fetchInteractions(
  chatbotId: string,
  opts: { onlyLowScores?: boolean; limit?: number } = {},
): Promise<Interaction[]> {
  const params = new URLSearchParams()
  if (opts.onlyLowScores) params.set('only_low_scores', 'true')
  if (opts.limit) params.set('limit', String(opts.limit))
  const query = params.toString() ? `?${params}` : ''
  const res = await fetch(
    `${API_BASE}/api/v1/hub/feedback/${chatbotId}/review${query}`,
    { headers: authHeaders() },
  )
  if (!res.ok) throw new Error('Failed to fetch interactions')
  return res.json()
}
