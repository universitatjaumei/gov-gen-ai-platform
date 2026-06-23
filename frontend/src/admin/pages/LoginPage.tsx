import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/shared/auth'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function LoginPage() {
  const SAML_ENABLED = import.meta.env.VITE_SAML_ENABLED === 'true'
  const { t } = useTranslation('admin')
  const { t: ta } = useTranslation('auth')
  const { login } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError('')
    setLoading(true)
    const form = new FormData(e.currentTarget)
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/token/admin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.get('email'), password: form.get('password') }),
      })
      if (!res.ok) throw new Error()
      const { access_token } = await res.json() as { access_token: string }
      login(access_token)
      navigate(params.get('from') ?? '/hub', { replace: true })
    } catch {
      setError(t('login.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm space-y-4 p-8 rounded-lg border bg-card shadow-sm">
        <h1 className="text-2xl font-semibold">{t('login.title')}</h1>
        {SAML_ENABLED && (
          <>
            <button
              type="button"
              onClick={() => { window.location.href = `${API_BASE}/api/v1/auth/saml/login` }}
              className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-md text-sm font-medium"
            >
              {ta('sso_button')}
            </button>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="h-px flex-1 bg-border" />
              {ta('sso_divider')}
              <span className="h-px flex-1 bg-border" />
            </div>
          </>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
        {error && <p role="alert" className="text-destructive text-sm">{error}</p>}
        <div className="space-y-1">
          <label htmlFor="email" className="text-sm font-medium">{t('login.email')}</label>
          <input id="email" name="email" type="email" required autoComplete="email"
            className="w-full px-3 py-2 border rounded-md text-sm bg-background" />
        </div>
        <div className="space-y-1">
          <label htmlFor="password" className="text-sm font-medium">{t('login.password')}</label>
          <input id="password" name="password" type="password" required autoComplete="current-password"
            className="w-full px-3 py-2 border rounded-md text-sm bg-background" />
        </div>
        <button type="submit" disabled={loading}
          className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-md text-sm font-medium disabled:opacity-50">
          {t('login.submit')}
        </button>
        </form>
      </div>
    </div>
  )
}
