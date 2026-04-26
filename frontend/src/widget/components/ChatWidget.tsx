import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useChat } from '../hooks/useChat'

interface Props {
  chatbotId: string
  apiUrl: string
  lang: string
}

interface StarRatingProps {
  interactionId: string
  apiUrl: string
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

export function ChatWidget({ chatbotId, apiUrl, lang }: Props) {
  const [open, setOpen] = useState(true)
  const [input, setInput] = useState('')
  const { t } = useTranslation('chat')
  const {
    messages,
    currentNodeStatus,
    isStreaming,
    translationWarning,
    interactionId,
    sendMessage,
  } = useChat(chatbotId, apiUrl, lang)

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
            <p>{msg.content}</p>
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
