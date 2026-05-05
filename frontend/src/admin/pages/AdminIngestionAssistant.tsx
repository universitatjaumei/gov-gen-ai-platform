import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { analyzeHtml, createSource, type AnalysisResult } from '@/shared/api/ingestion'

interface Props {
  chatbotId: string
}

export function AdminIngestionAssistant({ chatbotId }: Props) {
  const { t } = useTranslation('admin')

  const [html, setHtml] = useState('')
  const [urlHint, setUrlHint] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [hasPreview, setHasPreview] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  async function handleAnalyze() {
    setError(null)
    setAnalyzing(true)
    try {
      const res = await analyzeHtml(html, urlHint)
      setResult(res)
      setHasPreview(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setAnalyzing(false)
    }
  }

  async function handleSave() {
    if (!result || !urlHint) return
    setSaving(true)
    setError(null)
    try {
      await createSource(chatbotId, {
        url: urlHint,
        config_json: { proposed_selectors: result.proposed_selectors },
      })
      setSaved(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">
        {t('ingestion.assistant.title', 'Asistente de Ingestión')}
      </h1>

      <div className="space-y-2">
        <label htmlFor="url-hint" className="block text-sm font-medium text-gray-700">
          {t('ingestion.assistant.urlLabel', 'URL de la fuente')}
        </label>
        <input
          id="url-hint"
          type="url"
          value={urlHint}
          onChange={e => setUrlHint(e.target.value)}
          placeholder="https://www.uji.es/normativa"
          className="w-full border rounded px-3 py-2 text-sm"
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="html-input" className="block text-sm font-medium text-gray-700">
          {t('ingestion.assistant.htmlLabel', 'HTML de la página')}
        </label>
        <textarea
          id="html-input"
          value={html}
          onChange={e => setHtml(e.target.value)}
          rows={10}
          placeholder="<html>...</html>"
          className="w-full border rounded px-3 py-2 text-sm font-mono"
        />
      </div>

      <button
        onClick={handleAnalyze}
        disabled={analyzing || !html.trim()}
        className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
      >
        {analyzing
          ? t('ingestion.assistant.analyzing', 'Analizando...')
          : t('ingestion.assistant.analyzeBtn', 'Analizar')}
      </button>

      {error && (
        <p className="text-red-600 text-sm">{error}</p>
      )}

      {hasPreview && result && (
        <div className="border rounded p-4 bg-gray-50 space-y-3">
          <h2 className="font-semibold text-gray-800">
            {t('ingestion.assistant.previewTitle', 'Selectores propuestos')}
          </h2>
          <p className="text-sm text-gray-500">
            {t('ingestion.assistant.confidence', 'Confianza')}: {Math.round(result.confidence * 100)}%
          </p>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-left border-b">
                <th className="py-1 pr-4">{t('ingestion.assistant.field', 'Campo')}</th>
                <th className="py-1 pr-4">{t('ingestion.assistant.selector', 'Selector CSS')}</th>
                <th className="py-1">{t('ingestion.assistant.sample', 'Muestra')}</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(result.proposed_selectors).map(([key, selector]) => (
                <tr key={key} className="border-b last:border-0">
                  <td className="py-1 pr-4 font-mono text-gray-700">{key}</td>
                  <td className="py-1 pr-4 font-mono text-blue-700">{selector ?? '—'}</td>
                  <td className="py-1 text-gray-600 truncate max-w-xs">
                    {result.sample_extraction[key] ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {saved && (
        <p className="text-green-600 text-sm">
          {t('ingestion.assistant.saved', 'Fuente guardada correctamente.')}
        </p>
      )}

      <button
        onClick={handleSave}
        disabled={!hasPreview || saving || saved}
        className="px-4 py-2 bg-green-600 text-white rounded disabled:opacity-50"
      >
        {saving
          ? t('ingestion.assistant.saving', 'Guardando...')
          : t('ingestion.assistant.saveBtn', 'Guardar Fuente')}
      </button>
    </div>
  )
}
