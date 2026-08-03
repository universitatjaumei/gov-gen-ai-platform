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
  // FIX.1: el modelo se elige en el formulario. Antes era una constante del fichero de la
  // página, así que no se podía cambiar y una edición cualquiera lo reasignaba en silencio.
  llm_config_id: z.string().min(1),
  // Solo se usa al crear: `ChatbotUpdate` no admite cambiar de organización.
  organizacion_id: z.string().min(1),
  // SEC.4.1: ventana de vigencia y techo acumulado. Cadena vacía = «sin límite», y se
  // traduce a `null` al enviar: el backend distingue «no hay ventana» de «ventana con
  // fecha», y mandar '' rompería la validación de fecha en vez de significar «ninguna».
  //
  // `availability` NO está aquí a propósito: es estado derivado que calcula el servidor.
  // Aceptarlo en el formulario dejaría al cliente declarar si su chatbot está caducado.
  valid_from: z.string(),
  valid_until: z.string(),
  total_token_budget: z.number().int().min(0),
  unavailable_message: z.string().max(500),
})

export type FormValues = z.infer<typeof chatbotCreateSchema>

// Type-level contract: if ChatbotCreate renames or removes any field used in the form,
// tsc --noEmit will fail here before any test runs.
type _ContractCheck = keyof Omit<FormValues, 'kind'> extends keyof ChatbotCreate ? true : false
const _: _ContractCheck = true
void _
