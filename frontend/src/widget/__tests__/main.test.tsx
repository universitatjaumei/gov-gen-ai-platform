import { describe, test, expect, vi, afterEach } from 'vitest'
import { act } from '@testing-library/react'
import { readConfig, mountWidget } from '../main'
import i18n from '@/shared/i18n'

vi.mock('@/shared/i18n', () => ({
  default: { changeLanguage: vi.fn() },
}))

describe('Widget main', () => {
  afterEach(() => {
    document.body.innerHTML = ''
    vi.clearAllMocks()
  })

  test('should_mount_widget_from_data_attributes', async () => {
    const container = document.createElement('div')
    container.setAttribute('data-chatbot-id', 'abc-123')
    container.setAttribute('data-lang', 'es')
    container.setAttribute('data-api-url', 'https://api.example.com')
    document.body.appendChild(container)

    const config = readConfig(container)
    expect(config).not.toBeNull()

    await act(async () => {
      mountWidget(container, config!)
    })

    expect(container.querySelector('[data-testid="widget-root"]')).not.toBeNull()
  })

  test('should_use_lang_from_data_attribute', async () => {
    const container = document.createElement('div')
    container.setAttribute('data-chatbot-id', 'abc-123')
    container.setAttribute('data-lang', 'ca')
    document.body.appendChild(container)

    const config = readConfig(container)

    await act(async () => {
      mountWidget(container, config!)
    })

    expect(vi.mocked(i18n.changeLanguage)).toHaveBeenCalledWith('ca')
  })

  test('should_update_lang_on_postmessage_from_parent', async () => {
    const container = document.createElement('div')
    container.setAttribute('data-chatbot-id', 'abc-123')
    container.setAttribute('data-lang', 'es')
    document.body.appendChild(container)

    const config = readConfig(container)
    let cleanup: (() => void) | undefined

    await act(async () => {
      cleanup = mountWidget(container, config!)
    })

    vi.clearAllMocks()

    window.dispatchEvent(
      new MessageEvent('message', {
        data: { type: 'govgenai:setLang', lang: 'en' },
      }),
    )

    expect(vi.mocked(i18n.changeLanguage)).toHaveBeenCalledWith('en')
    cleanup?.()
  })

  test('should_hide_widget_if_chatbot_id_missing', () => {
    const container = document.createElement('div')

    const config = readConfig(container)
    expect(config).toBeNull()
  })
})
