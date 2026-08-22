import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  useListUsersApiV1HubUsersGet,
  useCreateUserApiV1HubUsersPost,
  useUpdateUserApiV1HubUsersUserIdPatch,
  getListUsersApiV1HubUsersGetQueryKey,
} from '@/shared/api/generated/hub-users/hub-users'
import type { UsuarioRead } from '@/shared/api/generated/model'
import { useAutoridadDelRol } from '@/shared/auth/useAutoridadDelRol'

/** Los roles que ofrece el alta. Salen del contrato del servidor, que los valida. */
const ROLES = ['user', 'informer', 'admin', 'superadmin'] as const

/**
 * Quién existe en esta plataforma (IDE.4).
 *
 * No había ninguna pantalla de usuarios: para saber quién tenía cuenta, con qué rol o si había
 * entrado alguna vez hacía falta acceso a Postgres — que es justo lo que no se le puede pedir a
 * otra administración que despliegue esto.
 *
 * **Dos cosas que la pantalla dice y no solo hace.** Con la autoridad del rol en el IdP, editar
 * un rol a mano es tirar el trabajo porque lo pisa el siguiente inicio de sesión: se avisa en
 * vez de dejar que se descubra solo. Y el listado **no son todas las cuentas** —siguen
 * existiendo `SuperAdminAccount`, `AdminAccount` y `ClientAccount` sin unificar (IDE.2)—, así
 * que se dice, porque un listado que se lee como completo miente por omisión.
 */
export function UsuariosPage() {
  const { t } = useTranslation('admin')
  // Quién manda sobre el rol lo dice el servidor (IDE.1), como los módulos concedidos.
  const autoridadDelRol = useAutoridadDelRol()
  const queryClient = useQueryClient()
  const { data: personas, isLoading } = useListUsersApiV1HubUsersGet()
  const invalidar = () =>
    void queryClient.invalidateQueries({ queryKey: getListUsersApiV1HubUsersGetQueryKey() })

  const { mutate: crear, isPending: creando } = useCreateUserApiV1HubUsersPost()
  const { mutate: actualizar } = useUpdateUserApiV1HubUsersUserIdPatch()

  const [email, setEmail] = useState('')
  const [rol, setRol] = useState<string>('user')
  const [nombre, setNombre] = useState('')

  function darDeAlta(evento: React.FormEvent) {
    evento.preventDefault()
    crear(
      { data: { email, role: rol, display_name: nombre || null } },
      {
        onSuccess: () => {
          setEmail('')
          setNombre('')
          setRol('user')
          invalidar()
        },
      }
    )
  }

  function cambiarActividad(persona: UsuarioRead) {
    actualizar(
      { userId: persona.id, data: { is_active: !persona.is_active } },
      { onSuccess: invalidar }
    )
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold">{t('plataforma.usuarios.titulo')}</h2>
        <p className="text-sm text-muted-foreground">{t('plataforma.usuarios.alcance')}</p>
      </header>

      {autoridadDelRol === 'idp' && (
        <p role="status" className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
          {t('plataforma.usuarios.aviso_autoridad_idp')}
        </p>
      )}

      <form onSubmit={darDeAlta} className="flex flex-wrap items-end gap-3 rounded-md border p-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="usuario_email" className="text-sm font-medium">
            {t('plataforma.usuarios.correo')}
          </label>
          <input
            id="usuario_email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-md border px-2 py-1 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="usuario_nombre" className="text-sm font-medium">
            {t('plataforma.usuarios.nombre')}
          </label>
          <input
            id="usuario_nombre"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            className="rounded-md border px-2 py-1 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="usuario_rol" className="text-sm font-medium">
            {t('plataforma.usuarios.rol')}
          </label>
          <select
            id="usuario_rol"
            value={rol}
            onChange={(e) => setRol(e.target.value)}
            className="rounded-md border px-2 py-1 text-sm"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {t(`plataforma.usuarios.roles.${r}` as Parameters<typeof t>[0])}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={creando}
          className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
        >
          {t('plataforma.usuarios.dar_de_alta')}
        </button>
        {/* Sin campo de contraseña: el alta crea identidad y permisos, no una credencial.
            Quien entra, entra por SSO. Dicho aquí porque la ausencia se lee como un olvido. */}
        <p className="w-full text-xs text-muted-foreground">
          {t('plataforma.usuarios.sin_contrasena')}
        </p>
      </form>

      {isLoading ? (
        <p>{t('plataforma.usuarios.cargando')}</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2">{t('plataforma.usuarios.correo')}</th>
              <th>{t('plataforma.usuarios.nombre')}</th>
              <th>{t('plataforma.usuarios.rol')}</th>
              <th>{t('plataforma.usuarios.origen')}</th>
              <th>{t('plataforma.usuarios.ultimo_acceso')}</th>
              <th>{t('plataforma.usuarios.estado')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(personas ?? []).map((persona) => (
              <tr key={persona.id} className="border-b">
                <td className="py-2">{persona.email}</td>
                <td>{persona.display_name ?? '—'}</td>
                <td>{t(`plataforma.usuarios.roles.${persona.role}` as Parameters<typeof t>[0])}</td>
                <td>{t(`plataforma.usuarios.origenes.${persona.origen}` as Parameters<typeof t>[0])}</td>
                {/* «Nunca» y no una celda vacía: que alguien no haya entrado todavía es lo
                    normal en una fila creada a mano, no un dato que falte. */}
                <td>
                  {persona.last_login_at
                    ? new Date(persona.last_login_at).toLocaleDateString()
                    : t('plataforma.usuarios.nunca_entro')}
                </td>
                <td>
                  {persona.is_active
                    ? t('plataforma.usuarios.activa')
                    : t('plataforma.usuarios.desactivada')}
                </td>
                <td className="text-right">
                  {/* Desactivar, nunca borrar: quien ya entró tiene rastro en interacciones,
                      informes y concesiones, y borrarlo lo dejaría sin dueño. */}
                  <button
                    type="button"
                    onClick={() => cambiarActividad(persona)}
                    className="text-xs underline"
                  >
                    {persona.is_active
                      ? t('plataforma.usuarios.desactivar')
                      : t('plataforma.usuarios.reactivar')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
