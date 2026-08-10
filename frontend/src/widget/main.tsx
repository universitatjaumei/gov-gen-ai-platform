import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import i18n from '@/shared/i18n'
import { injectThemeCSS } from '@/themes/ThemeProvider'
import { DEFAULT_THEME, mergeThemes } from '@/themes/types'
import { ChatWidget } from './components/ChatWidget'

export interface WidgetConfig {
  chatbotId: string
  lang: string
  apiUrl: string
  widgetKey?: string
}

export function readConfig(container: Element): WidgetConfig | null {
  const chatbotId = container.getAttribute('data-chatbot-id')
  if (!chatbotId) return null
  return {
    chatbotId,
    lang: container.getAttribute('data-lang') ?? 'es',
    apiUrl: container.getAttribute('data-api-url') ?? '/api/v1',
    widgetKey: container.getAttribute('data-widget-key') ?? undefined,
  }
}

export async function applyChatbotTheme(config: WidgetConfig): Promise<void> {
  try {
    const headers: Record<string, string> = {}
    if (config.widgetKey) headers['X-Widget-Key'] = config.widgetKey

    const response = await fetch(
      `${config.apiUrl}/hub/themes/for-chatbot/${config.chatbotId}`,
      { headers },
    )
    if (!response.ok) return

    const { config: partialTheme } = await response.json()
    injectThemeCSS(mergeThemes(DEFAULT_THEME, partialTheme ?? {}))
  } catch {
    // Sin tema o sin red: el widget se queda con los colores por defecto de ChatWidget.
  }
}

export function mountWidget(container: Element, config: WidgetConfig): () => void {
  i18n.changeLanguage(config.lang)
  void applyChatbotTheme(config)

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
        widgetKey={config.widgetKey}
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
