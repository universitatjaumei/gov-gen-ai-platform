import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useListChatbotsApiV1HubChatbotsGet } from '@/shared/api/generated/hub-chatbots/hub-chatbots'
import {
  fetchPromptTemplates,
  updatePromptTemplate,
} from '@/shared/api/promptTemplates'
import {
  fetchLLMConfigs,
  updateLLMConfig,
  testLLMConfig,
} from '@/shared/api/llmConfigs'
import type { PromptTemplateRead, LLMConfigRead } from '@/shared/api/generated/model'

function HighlightedVars({ text }: { text: string }) {
  const parts = text.split(/(\{\w+\})/g)
  return (
    <span aria-hidden>
      {parts.map((part, i) =>
        /^\{\w+\}$/.test(part) ? (
          <span key={i} className="bg-yellow-100 text-yellow-800 rounded px-0.5 font-mono text-xs">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </span>
  )
}

export function AIBrainPage() {
  const { t } = useTranslation('admin')
  const qc = useQueryClient()

  const [chatbotId, setChatbotId] = useState<string>('')

  // ── Chatbots ──────────────────────────────────────────────────────
  const { data: chatbots = [] } = useListChatbotsApiV1HubChatbotsGet()

  // ── Prompt templates ──────────────────────────────────────────────
  const { data: templates = [] } = useQuery<PromptTemplateRead[]>({
    queryKey: ['prompt-templates', chatbotId],
    queryFn: () => fetchPromptTemplates(chatbotId),
    enabled: !!chatbotId,
  })

  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')
  const [editText, setEditText] = useState('')
  const [savedVersion, setSavedVersion] = useState<number | null>(null)

  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId) ?? templates[0] ?? null

  const handleSelectTemplate = (tmpl: PromptTemplateRead) => {
    setSelectedTemplateId(tmpl.id)
    setEditText(tmpl.template_text)
    setSavedVersion(null)
  }

  const savePromptMutation = useMutation({
    mutationFn: (text: string) =>
      updatePromptTemplate(selectedTemplate!.id, { template_text: text }),
    onSuccess: (updated) => {
      setSavedVersion(updated.version)
      qc.invalidateQueries({ queryKey: ['prompt-templates', chatbotId] })
    },
  })

  // ── LLM configs ───────────────────────────────────────────────────
  const { data: llmConfigs = [] } = useQuery<LLMConfigRead[]>({
    queryKey: ['llm-configs'],
    queryFn: fetchLLMConfigs,
  })

  const [selectedConfigId, setSelectedConfigId] = useState<string>('')

  const setDefaultModelMutation = useMutation({
    mutationFn: (id: string) => updateLLMConfig(id, { is_default: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['llm-configs'] }),
  })

  // ── Sandbox ───────────────────────────────────────────────────────
  const [sandboxResult, setSandboxResult] = useState<string | null>(null)

  const testModelMutation = useMutation({
    mutationFn: (id: string) => testLLMConfig(id),
    onSuccess: (res) =>
      setSandboxResult(t('hub.brain_sandbox_ok', { ms: res.latency_ms })),
    onError: () => setSandboxResult(t('hub.brain_sandbox_fail')),
  })

  const activeConfigId = selectedConfigId || llmConfigs.find((c) => c.is_default)?.id || ''

  return (
    <div className="space-y-6">
      {/* Chatbot selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-foreground">
          {t('hub.chatbot_name')}
        </label>
        <select
          data-testid="chatbot-select"
          className="border rounded-md px-3 py-1.5 text-sm bg-background"
          value={chatbotId}
          onChange={(e) => {
            setChatbotId(e.target.value)
            setSelectedTemplateId('')
            setEditText('')
            setSavedVersion(null)
            setSandboxResult(null)
          }}
        >
          <option value="">{t('hub.brain_select_chatbot')}</option>
          {chatbots.map((cb) => (
            <option key={cb.id} value={cb.id}>
              {cb.name}
            </option>
          ))}
        </select>
      </div>

      {chatbotId && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* ── Prompt editor ── */}
          <section className="space-y-3 border rounded-lg p-4">
            <h2 className="text-sm font-semibold">{t('hub.brain_prompt_editor')}</h2>

            {templates.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('hub.brain_no_templates')}</p>
            ) : (
              <>
                {templates.length > 1 && (
                  <select
                    className="border rounded-md px-2 py-1 text-xs w-full bg-background"
                    value={selectedTemplate?.id ?? ''}
                    onChange={(e) => {
                      const tmpl = templates.find((t) => t.id === e.target.value)
                      if (tmpl) handleSelectTemplate(tmpl)
                    }}
                  >
                    {templates.map((tmpl) => (
                      <option key={tmpl.id} value={tmpl.id}>
                        {tmpl.slug} ({tmpl.language})
                      </option>
                    ))}
                  </select>
                )}

                {selectedTemplate && editText === '' && (
                  // Auto-populate on first render of a template
                  void handleSelectTemplate(selectedTemplate)
                )}

                <textarea
                  data-testid="prompt-textarea"
                  className="w-full h-48 border rounded-md p-2 text-sm font-mono resize-y bg-background"
                  value={editText || selectedTemplate?.template_text || ''}
                  onChange={(e) => setEditText(e.target.value)}
                />

                <div className="text-xs text-muted-foreground">
                  {selectedTemplate && <HighlightedVars text={editText || selectedTemplate.template_text} />}
                </div>

                <div className="flex items-center gap-3">
                  <button
                    data-testid="save-prompt-btn"
                    className="px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-sm disabled:opacity-50"
                    disabled={savePromptMutation.isPending || !selectedTemplate}
                    onClick={() => savePromptMutation.mutate(editText)}
                  >
                    {savePromptMutation.isPending
                      ? t('common.saving', 'Guardando…')
                      : t('hub.brain_save_prompt')}
                  </button>

                  {savedVersion !== null && (
                    <span data-testid="saved-version" className="text-xs text-muted-foreground">
                      {t('hub.brain_prompt_version')} {savedVersion}
                    </span>
                  )}
                </div>
              </>
            )}
          </section>

          {/* ── Model selector ── */}
          <section className="space-y-3 border rounded-lg p-4">
            <h2 className="text-sm font-semibold">{t('hub.brain_model_selector')}</h2>

            <select
              data-testid="model-select"
              className="border rounded-md px-3 py-1.5 text-sm w-full bg-background"
              value={selectedConfigId}
              onChange={(e) => setSelectedConfigId(e.target.value)}
            >
              <option value="">{t('hub.brain_model_select_label')}</option>
              {llmConfigs.map((cfg) => (
                <option key={cfg.id} value={cfg.id}>
                  {cfg.label} — {cfg.provider}/{cfg.model_name}
                  {cfg.is_default ? ' ✓' : ''}
                </option>
              ))}
            </select>

            <button
              data-testid="set-default-btn"
              className="px-3 py-1.5 rounded-md bg-secondary text-secondary-foreground text-sm disabled:opacity-50"
              disabled={!selectedConfigId || setDefaultModelMutation.isPending}
              onClick={() => setDefaultModelMutation.mutate(selectedConfigId)}
            >
              {t('hub.brain_set_default')}
            </button>

            {/* Sandbox */}
            <div className="border-t pt-3 space-y-2">
              <p className="text-xs font-medium">{t('hub.brain_sandbox')}</p>
              <button
                data-testid="sandbox-test-btn"
                className="px-3 py-1.5 rounded-md border text-sm disabled:opacity-50"
                disabled={!activeConfigId || testModelMutation.isPending}
                onClick={() => testModelMutation.mutate(activeConfigId)}
              >
                {testModelMutation.isPending
                  ? t('hub.brain_sandbox_testing')
                  : t('hub.brain_sandbox_test')}
              </button>
              {sandboxResult && (
                <p data-testid="sandbox-result" className="text-xs text-muted-foreground">
                  {sandboxResult}
                </p>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
