import { useState, useCallback, useRef } from 'react'

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export interface SourceRef {
  document_id: string
  title: string
  url: string
  score: number
}

export interface UseChatReturn {
  messages: Message[]
  currentNodeStatus: string | null
  isStreaming: boolean
  translationWarning: string | null
  sources: SourceRef[]
  interactionId: string | null
  sendMessage: (text: string) => Promise<void>
}

export function useChat(chatbotId: string, apiUrl: string, lang: string, widgetKey?: string): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [currentNodeStatus, setCurrentNodeStatus] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [translationWarning, setTranslationWarning] = useState<string | null>(null)
  const [sources, setSources] = useState<SourceRef[]>([])
  const [interactionId, setInteractionId] = useState<string | null>(null)
  const isStreamingRef = useRef(false)

  const sendMessage = useCallback(async (text: string) => {
    if (isStreamingRef.current) return
    isStreamingRef.current = true
    setIsStreaming(true)
    setCurrentNodeStatus(null)
    setTranslationWarning(null)
    setSources([])
    setInteractionId(null)
    setMessages(prev => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '' },
    ])

    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (widgetKey) headers['X-Widget-Key'] = widgetKey
      const response = await fetch(`${apiUrl}/hub/chat/${chatbotId}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: text, lang }),
      })

      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent = ''

      while (true) {
        const { done, value: chunk } = await reader.read()
        if (done) break

        buffer += decoder.decode(chunk, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (line === '') {
            currentEvent = ''
            continue
          }
          const colon = line.indexOf(':')
          if (colon === -1) continue
          const field = line.slice(0, colon).trim()
          const sseValue = line.slice(colon + 1).trim()

          if (field === 'event') {
            currentEvent = sseValue
          } else if (field === 'data') {
            const payload = JSON.parse(sseValue) as Record<string, unknown>
            if (currentEvent === 'status') {
              setCurrentNodeStatus(payload.msg as string)
            } else if (currentEvent === 'token') {
              setMessages(prev => {
                const last = prev[prev.length - 1]
                if (last?.role === 'assistant') {
                  return [
                    ...prev.slice(0, -1),
                    { ...last, content: last.content + (payload.delta as string) },
                  ]
                }
                return prev
              })
            } else if (currentEvent === 'done') {
              setSources((payload.sources as SourceRef[]) ?? [])
              setInteractionId(payload.interaction_id as string)
              if (payload.language_fallback) {
                setTranslationWarning(payload.translation_warning as string | null)
              }
              isStreamingRef.current = false
              setIsStreaming(false)
              setCurrentNodeStatus(null)
            } else if (currentEvent === 'error') {
              isStreamingRef.current = false
              setIsStreaming(false)
              setCurrentNodeStatus(null)
            }
          }
        }
      }
    } catch {
      isStreamingRef.current = false
      setIsStreaming(false)
      setCurrentNodeStatus(null)
    }
  }, [chatbotId, apiUrl, lang, widgetKey])

  return { messages, currentNodeStatus, isStreaming, translationWarning, sources, interactionId, sendMessage }
}
