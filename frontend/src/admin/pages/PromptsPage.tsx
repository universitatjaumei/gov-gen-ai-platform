import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { fetchPromptTemplates, updatePromptTemplate, deletePromptTemplate, createPromptTemplate } from '@/shared/api/promptTemplates'
import type { PromptTemplate, PromptTemplateCreate } from '@/shared/api/promptTemplates'
import { fetchChatbots } from '@/shared/api/chatbots'

// Extract {variable} names from a template string
function extractVariables(text: string): string[] {
  const matches = text.matchAll(/\{(\w+)\}/g)
  const seen = new Set<string>()
  for (const m of matches) seen.add(m[1])
  return Array.from(seen)
}

// Render template text with {variable} spans highlighted (for the editor preview)
function HighlightedText({ text }: { text: string }) {
  const parts = text.split(/(\{\w+\})/g)
  return (
    <span>
      {parts.map((part, i) =>
        /^\{\w+\}$/.test(part) ? (
          <span
            key={i}
            data-testid="var-highlight"
            className="bg-yellow-100 rounded px-0.5 font-mono text-yellow-800"
          >
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </span>
  )
}

// Fill {variables} with example values for preview
function buildPreview(text: string): string {
  return text.replace(/\{(\w+)\}/g, (_match, name: string) => `[${name}]`)
}

const TIER_COLORS: Record<number, string> = {
  1: 'bg-green-100 text-green-800',
  2: 'bg-yellow-100 text-yellow-800',
  3: 'bg-red-100 text-red-800',
}

function TierChip({ tier, label }: { tier: number; label?: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${TIER_COLORS[tier] ?? 'bg-gray-100 text-gray-700'}`}>
      {label ?? `Tier ${tier}`}
    </span>
  )
}

export function PromptsPage() {
  const { t } = useTranslation('admin')
  const qc = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editText, setEditText] = useState('')
  const [editDefaultTier, setEditDefaultTier] = useState<number | null>(null)
  const [editOverrideTier, setEditOverrideTier] = useState<number | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [newForm, setNewForm] = useState<Partial<PromptTemplateCreate>>({})

  const { data: templates = [] } = useQuery({
    queryKey: ['prompt-templates'],
    queryFn: () => fetchPromptTemplates(),
  })

  const { data: chatbots = [] } = useQuery({
    queryKey: ['chatbots'],
    queryFn: fetchChatbots,
  })

  const chatbotName = (chatbot_id: string) =>
    chatbots.find((c) => c.id === chatbot_id)?.name ?? chatbot_id.slice(0, 8)

  const selected = templates.find((t) => t.id === selectedId) ?? null

  const effectiveTier = (tmpl: PromptTemplate) => tmpl.override_tier ?? tmpl.default_tier

  function handleSelect(tmpl: PromptTemplate) {
    setSelectedId(tmpl.id)
    setEditText(tmpl.template_text)
    setEditDefaultTier(tmpl.default_tier)
    setEditOverrideTier(tmpl.override_tier)
  }

  const saveMutation = useMutation({
    mutationFn: ({ id, text, defaultTier, overrideTier }: { id: string; text: string; defaultTier: number | null; overrideTier: number | null }) =>
      updatePromptTemplate(id, {
        template_text: text,
        ...(defaultTier !== null ? { default_tier: defaultTier } : {}),
        ...(overrideTier !== null ? { override_tier: overrideTier } : {}),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prompt-templates'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePromptTemplate(id),
    onSuccess: () => {
      setSelectedId(null)
      qc.invalidateQueries({ queryKey: ['prompt-templates'] })
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: PromptTemplateCreate) => createPromptTemplate(data),
    onSuccess: () => {
      setShowCreate(false)
      setNewForm({})
      qc.invalidateQueries({ queryKey: ['prompt-templates'] })
    },
  })

  function handleSave() {
    if (!selectedId) return
    saveMutation.mutate({ id: selectedId, text: editText, defaultTier: editDefaultTier, overrideTier: editOverrideTier })
  }

  return (
    <div className="flex gap-4 h-[calc(100vh-160px)]">
      {/* Left panel — template list */}
      <aside className="w-72 shrink-0 border rounded-lg overflow-y-auto flex flex-col">
        <div className="p-3 border-b flex items-center justify-between">
          <span className="font-medium text-sm">{t('hub.prompt_templates')}</span>
          <button
            onClick={() => setShowCreate(true)}
            className="text-xs px-2 py-1 rounded bg-primary text-primary-foreground hover:bg-primary/90"
          >
            + {t('hub.new_prompt_template')}
          </button>
        </div>

        {templates.length === 0 && (
          <p className="p-4 text-sm text-muted-foreground">{t('hub.no_prompt_templates')}</p>
        )}

        {templates.map((tmpl) => {
          const tier = effectiveTier(tmpl)
          return (
            <button
              key={tmpl.id}
              onClick={() => handleSelect(tmpl)}
              className={`w-full text-left px-3 py-2 border-b text-sm hover:bg-accent/50 transition-colors ${selectedId === tmpl.id ? 'bg-accent' : ''}`}
            >
              <div className="flex items-center justify-between gap-1">
                <span className="font-medium truncate">{tmpl.slug}</span>
                <span className="shrink-0 text-xs bg-muted text-muted-foreground rounded px-1.5">
                  v{tmpl.version}
                </span>
              </div>
              <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                <span className="text-xs text-muted-foreground">{chatbotName(tmpl.chatbot_id)}</span>
                <span className="text-xs bg-blue-100 text-blue-700 rounded px-1">{tmpl.language}</span>
                {tier !== null && <TierChip tier={tier} />}
              </div>
            </button>
          )
        })}
      </aside>

      {/* Right panel — editor */}
      {selected ? (
        <div className="flex-1 border rounded-lg overflow-y-auto flex flex-col gap-4 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-base">{selected.slug}</h2>
              <span className="text-xs bg-muted text-muted-foreground rounded px-1.5">
                v{selected.version}
              </span>
              {selected.override_tier !== null && (
                <span data-testid="effective-tier">
                  <TierChip tier={selected.override_tier} label={`Tier ${selected.override_tier} (override)`} />
                </span>
              )}
              {selected.override_tier === null && selected.default_tier !== null && (
                <span data-testid="effective-tier">
                  <TierChip tier={selected.default_tier} />
                </span>
              )}
            </div>
            <button
              onClick={() => deleteMutation.mutate(selected.id)}
              className="text-xs text-destructive hover:underline"
            >
              {t('hub.delete_prompt_template')}
            </button>
          </div>

          {/* Tier controls */}
          <div className="flex flex-wrap gap-4 text-sm">
            <div>
              <p className="text-xs text-muted-foreground mb-1">{t('hub.prompt_default_tier')}</p>
              <div className="flex gap-1">
                {[1, 2, 3].map((n) => (
                  <button
                    key={n}
                    onClick={() => setEditDefaultTier(n)}
                    className={`px-2 py-0.5 rounded text-xs font-medium border ${editDefaultTier === n ? 'bg-primary text-primary-foreground border-primary' : 'border-border hover:bg-accent/50'}`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">{t('hub.prompt_override_tier')}</p>
              <div className="flex gap-1 items-center">
                {[null, 1, 2, 3].map((n) => (
                  <button
                    key={n ?? 'none'}
                    onClick={() => setEditOverrideTier(n)}
                    className={`px-2 py-0.5 rounded text-xs font-medium border ${editOverrideTier === n ? 'bg-primary text-primary-foreground border-primary' : 'border-border hover:bg-accent/50'}`}
                  >
                    {n === null ? '—' : n}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Textarea editor */}
          <div>
            <p className="text-xs text-muted-foreground mb-1">{t('hub.prompt_text')}</p>
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={8}
              className="w-full rounded border px-3 py-2 text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          {/* Variable highlighting */}
          <div>
            <p className="text-xs text-muted-foreground mb-1">{t('hub.prompt_variables')}</p>
            <div className="rounded border px-3 py-2 text-sm font-mono bg-muted/30 whitespace-pre-wrap break-words">
              <HighlightedText text={editText} />
            </div>
          </div>

          {/* Preview with filled variables */}
          <div>
            <p className="text-xs text-muted-foreground mb-1">{t('hub.prompt_preview')}</p>
            <div
              data-testid="prompt-preview"
              className="rounded border px-3 py-2 text-sm bg-muted/20 whitespace-pre-wrap break-words"
            >
              {buildPreview(editText)}
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={saveMutation.isPending}
              className="px-4 py-2 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-50"
            >
              {t('hub.save_prompt_version')}
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
          {t('hub.select_prompt_template')}
        </div>
      )}

      {/* Create dialog */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" role="dialog">
          <div className="bg-background rounded-lg p-6 w-full max-w-md flex flex-col gap-4">
            <h3 className="font-semibold text-base">{t('hub.new_prompt_template')}</h3>
            <div className="flex flex-col gap-3 text-sm">
              <label className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">Chatbot</span>
                <select
                  className="border rounded px-2 py-1.5"
                  value={newForm.chatbot_id ?? ''}
                  onChange={(e) => setNewForm((f) => ({ ...f, chatbot_id: e.target.value }))}
                >
                  <option value="">—</option>
                  {chatbots.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">{t('hub.prompt_slug')}</span>
                <input
                  className="border rounded px-2 py-1.5"
                  value={newForm.slug ?? ''}
                  onChange={(e) => setNewForm((f) => ({ ...f, slug: e.target.value }))}
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">{t('hub.language_label')}</span>
                <select
                  className="border rounded px-2 py-1.5"
                  value={newForm.language ?? 'es'}
                  onChange={(e) => setNewForm((f) => ({ ...f, language: e.target.value }))}
                >
                  <option value="es">es</option>
                  <option value="ca">ca</option>
                  <option value="en">en</option>
                </select>
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">{t('hub.prompt_text')}</span>
                <textarea
                  rows={4}
                  className="border rounded px-2 py-1.5 font-mono text-xs resize-y"
                  value={newForm.template_text ?? ''}
                  onChange={(e) => setNewForm((f) => ({ ...f, template_text: e.target.value }))}
                />
              </label>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setShowCreate(false); setNewForm({}) }}
                className="px-3 py-1.5 rounded border text-sm"
              >
                {t('hub.cancel')}
              </button>
              <button
                onClick={() => {
                  if (newForm.chatbot_id && newForm.slug && newForm.language && newForm.template_text) {
                    createMutation.mutate(newForm as PromptTemplateCreate)
                  }
                }}
                disabled={createMutation.isPending}
                className="px-3 py-1.5 rounded bg-primary text-primary-foreground text-sm hover:bg-primary/90 disabled:opacity-50"
              >
                {t('hub.create')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
