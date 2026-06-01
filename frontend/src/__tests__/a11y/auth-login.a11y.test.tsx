import { describe, it, beforeAll } from 'vitest'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AuthProvider } from '@/shared/auth'
import { LoginPage } from '@/admin/pages/LoginPage'
import { expectNoA11yViolations } from '@/test/a11y'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

describe('LoginPage — WCAG 2.2 AA baseline', () => {
  it('should_have_no_critical_a11y_violations', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await expectNoA11yViolations(container)
  })
})
