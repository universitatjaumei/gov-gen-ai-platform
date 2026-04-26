import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import i18n from '@/shared/i18n'
import { ChatWidget } from './components/ChatWidget'

export interface WidgetConfig {
  chatbotId: string
  lang: string
  apiUrl: string
}

export function readConfig(container: Element): WidgetConfig | null {
  const chatbotId = container.getAttribute('data-chatbot-id')
  if (!chatbotId) return null
  return {
    chatbotId,
    lang: container.getAttribute('data-lang') ?? 'es',
    apiUrl: container.getAttribute('data-api-url') ?? '/api/v1',
  }
}

export function mountWidget(container: Element, config: WidgetConfig): () => void {
  i18n.changeLanguage(config.lang)

  const handleMessage = (event: MessageEvent) => {
    if (event.data?.type === 'govgenai:setLang' && typeof event.data.lang === 'string') {
      i18n.changeLanguage(event.data.lang)
    }
  }

  window.addEventListener('message', handleMessage)

  createRoot(container).render(
    <StrictMode>
      <ChatWidget
        chatbotId={config.chatbotId}
        apiUrl={config.apiUrl}
        lang={config.lang}
      />
    </StrictMode>,
  )

  return () => window.removeEventListener('message', handleMessage)
}

const container = document.getElementById('govgenai-widget')
if (container) {
  const config = readConfig(container)
  if (config) mountWidget(container, config)
}
