import { describe, it, beforeAll, afterEach, vi } from 'vitest'
import { render } from '@testing-library/react'
import i18n from '@/shared/i18n'
import { ChatWidget } from '@/widget/components/ChatWidget'
import { expectNoA11yViolations } from '@/test/a11y'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ChatWidget — WCAG 2.2 AA baseline', () => {
  it('should_have_no_critical_a11y_violations_on_idle_state', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => ({ name: 'Bot Demo' }) }),
    )
    const { container } = render(
      <ChatWidget
        chatbotId="bot-0001-0000-0000-000000000001"
        apiUrl="/api/v1"
        lang="es"
      />,
    )
    await expectNoA11yViolations(container)
  })
})
