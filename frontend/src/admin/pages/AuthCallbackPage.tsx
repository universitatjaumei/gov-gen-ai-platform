import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/shared/auth'

/**
 * Destino del ACS de SAML (SAML_FRONTEND_RETURN_URL). El backend redirige aquí con
 * el JWT en el fragment (#token=…) para que no quede en logs de servidor/proxy.
 */
export function AuthCallbackPage() {
  const { t } = useTranslation('auth')
  const { login } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState(false)

  useEffect(() => {
    const hash = window.location.hash.replace(/^#/, '')
    const token = new URLSearchParams(hash).get('token')
    if (token) {
      login(token)
      navigate('/hub', { replace: true })
    } else {
      setError(true)
    }
  }, [login, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      {error ? (
        <p role="alert" className="text-destructive text-sm">{t('callback_error')}</p>
      ) : (
        <p role="status" className="text-muted-foreground text-sm">{t('callback_loading')}</p>
      )}
    </div>
  )
}
