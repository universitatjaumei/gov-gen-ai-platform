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

/** Progreso del grafo: el NODO, y el texto del servidor solo como red de seguridad.
 *
 * UX.3: el servidor mandaba el mensaje ya escrito en castellano y el widget lo pintaba tal
 * cual, así que «Buscando en la base de conocimiento...» salía en castellano dentro de un
 * widget en valenciano. El idioma de una interfaz lo decide la interfaz: el servidor dice
 * *qué* está pasando —el nodo, que ya mandaba— y aquí se traduce. `msg` se conserva para
 * un nodo que todavía no tenga traducción: mejor el texto del servidor que un hueco.
 */
export interface NodeStatus {
  node: string
  msg: string
}

export interface UseChatReturn {
  messages: Message[]
  currentNodeStatus: NodeStatus | null
  isStreaming: boolean
  translationWarning: string | null
  sources: SourceRef[]
  interactionId: string | null
  sendMessage: (text: string) => Promise<void>
}

export function useChat(chatbotId: string, apiUrl: string, lang: string, widgetKey?: string): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [currentNodeStatus, setCurrentNodeStatus] = useState<NodeStatus | null>(null)
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
              setCurrentNodeStatus({ node: String(payload.node ?? ''), msg: String(payload.msg ?? '') })
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
            } else if (currentEvent === 'discard') {
              // HIB.B: el contrato de citas corre después de generar, así que cuando
              // rechaza sus tokens ya se han pintado. Por SSE no se retira lo enviado, así
              // que el servidor avisa y aquí se vacía la burbuja: el mensaje de rendición
              // llega justo después como un `token` normal.
              //
              // Vaciar y no borrar la burbuja: si se quitara, el `token` siguiente no
              // encontraría un mensaje de asistente al que añadirse y se perdería.
              setMessages(prev => {
                const last = prev[prev.length - 1]
                if (last?.role === 'assistant') {
                  return [...prev.slice(0, -1), { ...last, content: '' }]
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
