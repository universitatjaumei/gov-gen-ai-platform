import { z } from 'zod'
import type { ChatbotCreate } from '@/shared/api/generated/model'

export const chatbotCreateSchema = z.object({
  name: z.string().min(1),
  kind: z.enum(['atomic', 'router']),
  system_prompt: z.string().min(1),
  is_active: z.boolean(),
  retrieval_mode: z.enum(['RAG', 'MD_LONG_CONTEXT', 'MD_AGENT_SELECTOR']),
  retrieval_top_k: z.number().int().min(1).max(50),
  use_prompt_caching: z.boolean(),
  cache_ttl: z.number().int().min(60).max(86_400),
  public_graph_profile: z.string(),
  language_mode: z.string(),
  quality_threshold: z.number().min(0).max(1),
  min_retrieval_results: z.number().int().min(1).max(20),
  min_retrieval_score: z.number().min(0).max(1),
  reranker_enabled: z.boolean(),
  answer_template: z.string(),
})

export type FormValues = z.infer<typeof chatbotCreateSchema>

// Type-level contract: if ChatbotCreate renames or removes any of these fields,
// tsc --noEmit will fail here before any test runs.
type _ContractCheck = Pick<ChatbotCreate,
  | 'name' | 'system_prompt' | 'is_active' | 'retrieval_mode'
  | 'retrieval_top_k' | 'use_prompt_caching' | 'cache_ttl'
  | 'public_graph_profile' | 'language_mode' | 'quality_threshold'
  | 'min_retrieval_results' | 'min_retrieval_score' | 'reranker_enabled'
  | 'answer_template'
> extends Omit<FormValues, 'kind'> ? true : false
const _: _ContractCheck = true
void _
