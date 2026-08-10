import { useDropzone } from 'react-dropzone'
import { useTranslation } from 'react-i18next'
import { AlertCircle, Link, Upload, UploadCloud } from 'lucide-react'

import type { HubDocumentOut } from '@/shared/api/generated/model'
import { LANGUAGE_OPTIONS } from './constants'

/**
 * Entrada del corpus: URL canónica, idioma y zona de arrastre.
 *
 * La URL y el idioma se piden **antes** de soltar el fichero porque son metadatos del
 * documento y el fichero puede no traerlos. Cuando se está sustituyendo un documento
 * existente, los dos vienen rellenos de él y el banner lo deja claro.
 *
 * **EXT.1**: al corpus solo entra Markdown conforme al contrato, no PDF. Lo que se cita ante
 * un ciudadano tiene que venir del pipeline de curación —que es donde está el OCR y donde la
 * conversión se revisa—, porque una extracción mala aquí es una cita errónea que no detecta
 * nadie. Para aportar un documento como contexto de una consulta, esa es otra vía.
 *
 * No conoce la mutación de subida: entrega los ficheros aceptados y ya.
 */
export function UploadDropzone({
  canonicalUrl,
  onCanonicalUrlChange,
  uploadLanguage,
  onUploadLanguageChange,
  substituteDoc,
  onCancelSubstitute,
  onDrop,
  uploadError,
}: {
  canonicalUrl: string
  onCanonicalUrlChange: (value: string) => void
  uploadLanguage: string
  onUploadLanguageChange: (value: string) => void
  substituteDoc: HubDocumentOut | null
  onCancelSubstitute: () => void
  onDrop: (files: File[]) => void
  uploadError: string
}) {
  const { t } = useTranslation('admin')
  const { t: tc } = useTranslation('common')

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/markdown': ['.md', '.markdown'] },
    multiple: true,
  })

  return (
    <>
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
        <div className="flex flex-1 items-center gap-2">
          <Link className="w-4 h-4 text-muted-foreground shrink-0" />
          <input
            type="url"
            value={canonicalUrl}
            onChange={e => onCanonicalUrlChange(e.target.value)}
            placeholder={t('hub.canonical_url_placeholder')}
            className="flex-1 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <select
          value={uploadLanguage}
          onChange={e => onUploadLanguageChange(e.target.value)}
          className="w-full sm:w-40 px-3 py-2 text-sm border rounded-md bg-background"
          aria-label={t('hub.language_label')}
        >
          {LANGUAGE_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{t(o.labelKey)}</option>
          ))}
        </select>
      </div>

      {substituteDoc && (
        <div className="flex items-center gap-2 p-3 text-sm bg-yellow-50 border border-yellow-200 rounded-md">
          <Upload className="w-4 h-4 text-yellow-600 shrink-0" />
          <span>{t('hub.substituting')}:</span>
          <strong className="truncate">{substituteDoc.title}</strong>
          <button
            type="button"
            onClick={onCancelSubstitute}
            className="ml-auto text-xs text-muted-foreground hover:text-foreground"
          >{tc('cancel')}</button>
        </div>
      )}

      <div
        {...getRootProps()}
        className={`p-10 border-2 border-dashed rounded-xl flex flex-col items-center justify-center text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/30'
        }`}
      >
        <input {...getInputProps()} />
        <UploadCloud className="w-10 h-10 text-muted-foreground mb-4" />
        <p className="text-sm font-medium mb-1">{t('hub.drag_drop')}</p>
        <p className="text-xs text-muted-foreground">{t('hub.max_size_10mb')}</p>
        {/* EXT.1: decir por qué solo Markdown, y no dejar que se descubra con un 415. */}
        <p className="text-xs text-muted-foreground mt-2 max-w-md">
          {t('hub.corpus_markdown_only')}
        </p>
      </div>

      {uploadError && (
        <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
          <AlertCircle className="w-4 h-4" />{uploadError}
        </div>
      )}
    </>
  )
}
