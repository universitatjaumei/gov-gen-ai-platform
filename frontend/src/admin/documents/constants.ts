/**
 * Vocabulario fijo de la pantalla de documentos.
 *
 * Los arrays guardan **claves de traducción**, no texto: la etiqueta se resuelve con `t()` al
 * pintar. Guardarla ya traducida los congelaría en el idioma que estuviera activo al cargar el
 * módulo —un `const` de nivel de módulo se evalúa una sola vez—, así que cambiar de idioma no
 * los actualizaría. Es la regla que pide CAL.4.
 */

export const LANGUAGE_OPTIONS = [
  { value: '',   labelKey: 'hub.language_auto' },
  { value: 'es', labelKey: 'hub.language_es' },
  { value: 'ca', labelKey: 'hub.language_ca' },
  { value: 'en', labelKey: 'hub.language_en' },
]

export const LANG_BADGE: Record<string, string> = {
  es: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  ca: 'bg-red-100 text-red-800 border-red-200',
  en: 'bg-blue-100 text-blue-800 border-blue-200',
}

/** Modo de recuperación → clave de su etiqueta. Un modo desconocido se pinta tal cual. */
export const RETRIEVAL_LABEL_KEYS: Record<string, string> = {
  vector:            'hub.retrieval_vector',
  RAG:               'hub.retrieval_rag',
  MD_LONG_CONTEXT:   'hub.retrieval_long_context',
  MD_AGENT_SELECTOR: 'hub.retrieval_agentic',
}
