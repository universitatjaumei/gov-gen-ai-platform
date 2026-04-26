import { describe, test, expect, vi, beforeAll, afterEach } from 'vitest'
import { act } from '@testing-library/react'
import { readConfig, mountWidget } from '../main'
import i18n from '@/shared/i18n'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

describe('Widget main', () => {
  let changeLanguageSpy: ReturnType<typeof vi.spyOn<typeof i18n, 'changeLanguage'>>

  afterEach(() => {
    document.body.innerHTML = ''
    changeLanguageSpy?.mockRestore()
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

    expect(container.querySelector('[role="dialog"]')).not.toBeNull()
  })

  test('should_use_lang_from_data_attribute', async () => {
    changeLanguageSpy = vi.spyOn(i18n, 'changeLanguage')

    const container = document.createElement('div')
    container.setAttribute('data-chatbot-id', 'abc-123')
    container.setAttribute('data-lang', 'ca')
    document.body.appendChild(container)

    const config = readConfig(container)

    await act(async () => {
      mountWidget(container, config!)
    })

    expect(changeLanguageSpy).toHaveBeenCalledWith('ca')
  })

  test('should_update_lang_on_postmessage_from_parent', async () => {
    changeLanguageSpy = vi.spyOn(i18n, 'changeLanguage')

    const container = document.createElement('div')
    container.setAttribute('data-chatbot-id', 'abc-123')
    container.setAttribute('data-lang', 'es')
    document.body.appendChild(container)

    const config = readConfig(container)
    let cleanup: (() => void) | undefined

    await act(async () => {
      cleanup = mountWidget(container, config!)
    })

    changeLanguageSpy.mockClear()

    window.dispatchEvent(
      new MessageEvent('message', {
        data: { type: 'govgenai:setLang', lang: 'en' },
      }),
    )

    expect(changeLanguageSpy).toHaveBeenCalledWith('en')
    cleanup?.()
  })

  test('should_hide_widget_if_chatbot_id_missing', () => {
    const container = document.createElement('div')

    const config = readConfig(container)
    expect(config).toBeNull()
  })
})
