/**
 * Hooks para la API de auditoría NER (Fase 13.2).
 * Deploy: edge
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const BASE = '/api/v1/redaccion/workspaces'

export interface AnonymizationSummaryData {
  mode: string
  counts_by_type: Record<string, number>
  total_spans: number
  last_run_at: string
  current_workspace_mode: string
}

export interface AnonymizationModePayload {
  mode: string
}

async function fetchJson(url: string, init?: RequestInit) {
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export function useGetAnonymizationSummary(workspaceId: string) {
  return useQuery<AnonymizationSummaryData>({
    queryKey: ['anonymization-summary', workspaceId],
    queryFn: () => fetchJson(`${BASE}/${workspaceId}/anonymization-summary`),
    enabled: Boolean(workspaceId),
  })
}

export function usePatchAnonymizationMode(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: AnonymizationModePayload) =>
      fetchJson(`${BASE}/${workspaceId}/anonymization-mode`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['anonymization-summary', workspaceId] })
    },
  })
}

export function useReAnalyzeAnonymization(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      fetchJson(`${BASE}/${workspaceId}/re-analyze`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['anonymization-summary', workspaceId] })
    },
  })
}
