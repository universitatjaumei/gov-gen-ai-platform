import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useCambiarMiPassword } from '@/shared/api/generated/auth/auth'

/** El mínimo del contrato del servidor (`MINIMO_CONTRASENA` en `auth_router.py`).
 *
 *  Dicho antes de gastar una petición, no en vez de la del servidor: quien manda es el 422. */
const MINIMO = 12

const esquema = z.object({
  password_actual: z.string().min(1),
  password_nueva: z.string().min(MINIMO),
})
type Valores = z.infer<typeof esquema>

/**
 * Cambiar la propia contraseña (USR.7), en el menú de la propia cuenta.
 *
 * **No existía en ningún rol**, y la consecuencia se vio el 2026-09-01: las seis cuentas del
 * piloto se crearon con la misma contraseña y ninguno de sus dueños podía cambiarla, así que
 * cualquiera de los seis podía entrar como otro.
 *
 * **Pide la actual, también a un superadministrador.** No es ceremonia del formulario: es lo que
 * el servidor exige, y por el mismo motivo — con el token basta para actuar, pero no tiene que
 * bastar para quedarse la cuenta.
 *
 * El error del servidor no se interpreta: un 401 aquí significa «la actual no es ésa», y se dice
 * así en vez de traducir el `detail`, que es el mismo para los dos casos que el servidor no
 * distingue a propósito.
 */
export function CambiarMiContrasena({ className }: { className?: string }) {
  const { t } = useTranslation('auth')
  const [abierto, setAbierto] = useState(false)
  const [hecho, setHecho] = useState(false)
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Valores>({ resolver: zodResolver(esquema) })

  const { mutate, isPending, isError } = useCambiarMiPassword()

  function cerrar() {
    reset({ password_actual: '', password_nueva: '' })
    setAbierto(false)
  }

  const enviar = handleSubmit((valores) => {
    mutate(
      { data: valores },
      {
        onSuccess: () => {
          setHecho(true)
          cerrar()
        },
      },
    )
    // El valor no se queda en el formulario ni cuando falla: si la actual era incorrecta, se
    // vuelve a escribir. Es una contraseña, no un borrador.
    reset({ password_actual: '', password_nueva: '' })
  })

  if (!abierto) {
    return (
      <div className={className}>
        <button
          type="button"
          onClick={() => {
            setHecho(false)
            setAbierto(true)
          }}
          className="w-full text-left hover:text-sidebar-accent-foreground transition-colors"
        >
          {t('cambiar_contrasena.abrir')}
        </button>
        {hecho && (
          <p role="status" className="mt-1 text-xs opacity-80">
            {t('cambiar_contrasena.hecho')}
          </p>
        )}
      </div>
    )
  }

  return (
    <form onSubmit={enviar} className={`space-y-2 ${className ?? ''}`}>
      <div className="space-y-1">
        <label htmlFor="password_actual" className="block text-xs">
          {t('cambiar_contrasena.actual')}
        </label>
        <input
          id="password_actual"
          type="password"
          autoComplete="current-password"
          {...register('password_actual')}
          className="w-full rounded-md border px-2 py-1 text-sm text-foreground"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="password_nueva" className="block text-xs">
          {t('cambiar_contrasena.nueva')}
        </label>
        <input
          id="password_nueva"
          type="password"
          autoComplete="new-password"
          {...register('password_nueva')}
          className="w-full rounded-md border px-2 py-1 text-sm text-foreground"
        />
      </div>
      {errors.password_nueva && (
        <p role="alert" className="text-xs">
          {t('cambiar_contrasena.corta', { minimo: MINIMO })}
        </p>
      )}
      {isError && (
        <p role="alert" className="text-xs">
          {t('cambiar_contrasena.actual_incorrecta')}
        </p>
      )}
      <div className="flex gap-3">
        <button type="submit" disabled={isPending} className="text-xs underline disabled:opacity-50">
          {t('cambiar_contrasena.guardar')}
        </button>
        <button type="button" onClick={cerrar} className="text-xs underline">
          {t('cambiar_contrasena.cancelar')}
        </button>
      </div>
    </form>
  )
}
