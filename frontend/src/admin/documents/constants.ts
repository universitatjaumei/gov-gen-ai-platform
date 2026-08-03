/**
 * Etiquetas fijas de la pantalla de documentos.
 *
 * Siguen siendo literales a propósito: sacarlas a i18n es el trabajo de **CAL.4**, que las
 * nombra explícitamente (`LANGUAGE_OPTIONS`, `RETRIEVAL_LABELS`) y exige resolverlas con
 * `t()` en el render, no dejarlas fijas en el array. Adelantarlo aquí mezclaría dos prompts.
 */

export const LANGUAGE_OPTIONS = [
  { value: '',   label: 'Auto-detectar' },
  { value: 'es', label: 'Español' },
  { value: 'ca', label: 'Català' },
  { value: 'en', label: 'English' },
]

export const LANG_BADGE: Record<string, string> = {
  es: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  ca: 'bg-red-100 text-red-800 border-red-200',
  en: 'bg-blue-100 text-blue-800 border-blue-200',
}

export const RETRIEVAL_LABELS: Record<string, string> = {
  vector:            'Vectorial',
  RAG:               'Vectorial (RAG)',
  MD_LONG_CONTEXT:   'Contexto largo',
  MD_AGENT_SELECTOR: 'Agéntico',
}
