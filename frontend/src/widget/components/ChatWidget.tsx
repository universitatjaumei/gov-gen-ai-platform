import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useTranslation } from 'react-i18next'
import { useChat, type SourceRef } from '../hooks/useChat'

interface Props {
  chatbotId: string
  apiUrl: string
  lang: string
  token?: string
}

interface StarRatingProps {
  interactionId: string
  apiUrl: string
}

interface SourcePillsProps {
  sources: SourceRef[]
}

function SourcePills({ sources }: SourcePillsProps) {
  const { t } = useTranslation('chat')
  if (sources.length === 0) return null
  return (
    <nav aria-label={t('sources')} style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem', marginTop: '0.5rem' }}>
      {sources.map(src => (
        <a
          key={src.document_id}
          href={src.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            background: 'var(--source-pill-bg, var(--color-primary-light, #e0f2fe))',
            color: 'var(--source-pill-fg, var(--color-primary, #0369a1))',
            border: '1px solid var(--source-pill-border, var(--color-primary, #7dd3fc))',
            borderRadius: '999px',
            padding: '0.2rem 0.65rem',
            fontSize: '0.8rem',
            textDecoration: 'none',
            whiteSpace: 'nowrap',
          }}
        >
          {src.title}
        </a>
      ))}
    </nav>
  )
}

function StarRating({ interactionId, apiUrl }: StarRatingProps) {
  const [selected, setSelected] = useState<number | null>(null)
  const { t } = useTranslation('chat')

  const handleClick = async (score: number) => {
    setSelected(score)
    await fetch(`${apiUrl}/hub/feedback/${interactionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ score }),
    })
  }

  return (
    <div role="group" aria-label={t('feedback_rate')}>
      {[1, 2, 3, 4, 5].map(star => (
        <button
          key={star}
          type="button"
          aria-label={`${star} ${t('feedback_stars')}`}
          aria-pressed={selected === star}
          onClick={() => handleClick(star)}
          style={{ cursor: 'pointer', background: 'none', border: 'none', fontSize: '1.25rem' }}
        >
          {star <= (selected ?? 0) ? '★' : '☆'}
        </button>
      ))}
    </div>
  )
}

export function ChatWidget({ chatbotId, apiUrl, lang, token }: Props) {
  const [open, setOpen] = useState(true)
  const [input, setInput] = useState('')
  const { t } = useTranslation('chat')
  const {
    messages,
    currentNodeStatus,
    isStreaming,
    translationWarning,
    sources,
    interactionId,
    sendMessage,
  } = useChat(chatbotId, apiUrl, lang, token)

  const lastAssistantIdx = [...messages].map((m, i) => ({ m, i })).reverse().find(({ m }) => m.role === 'assistant')?.i ?? -1
  const showRating = !isStreaming && interactionId !== null && lastAssistantIdx !== -1

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput('')
    await sendMessage(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t('widget_open')}
        style={{ position: 'fixed', bottom: 'var(--widget-bottom, 1.5rem)', right: 'var(--widget-right, 1.5rem)', fontSize: '1.5rem', cursor: 'pointer' }}
      >
        💬
      </button>
    )
  }

  return (
    <div
      role="dialog"
      aria-label={t('widget_open')}
      style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
    >
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button type="button" onClick={() => setOpen(false)} aria-label={t('widget_close')}>
          ✕
        </button>
      </div>

      <div role="log" aria-live="polite" style={{ flex: 1, overflowY: 'auto' }}>
        {messages.map((msg, i) => (
          <div key={i} data-role={msg.role}>
            {msg.role === 'assistant' && translationWarning && i === lastAssistantIdx && (
              <div role="alert" style={{ background: '#fef3c7', padding: '0.5rem' }}>
                {translationWarning}
              </div>
            )}
            {msg.role === 'assistant'
              ? <ReactMarkdown>{msg.content}</ReactMarkdown>
              : <p>{msg.content}</p>
            }
            {msg.role === 'assistant' && i === lastAssistantIdx && !isStreaming && (
              <SourcePills sources={sources} />
            )}
          </div>
        ))}
      </div>

      {isStreaming && currentNodeStatus && (
        <p aria-live="polite">
          <em>{currentNodeStatus}</em>
        </p>
      )}

      {isStreaming && (
        <div role="status" aria-label={t('widget_loading')} aria-busy="true" />
      )}

      {showRating && (
        <StarRating interactionId={interactionId!} apiUrl={apiUrl} />
      )}

      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('placeholder')}
          disabled={isStreaming}
          style={{ flex: 1 }}
        />
        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={isStreaming || !input.trim()}
        >
          {t('send')}
        </button>
      </div>
    </div>
  )
}
