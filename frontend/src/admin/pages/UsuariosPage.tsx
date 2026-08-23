import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  useListUsersApiV1HubUsersGet,
  useCreateUserApiV1HubUsersPost,
  useUpdateUserApiV1HubUsersUserIdPatch,
  useDeleteUserApiV1HubUsersUserIdDelete,
  getListUsersApiV1HubUsersGetQueryKey,
} from '@/shared/api/generated/hub-users/hub-users'
import type { UsuarioRead } from '@/shared/api/generated/model'
import { useAutoridadDelRol } from '@/shared/auth/useAutoridadDelRol'
import { useOrganizacionElegida } from '@/shared/organizacion/useOrganizacionElegida'

/** El `origen` de las cuentas que vienen de `superadminaccount` y no de `hub_users` (REV.8). */
const ORIGEN_DE_ARRANQUE = 'superadmin'

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
  const { mutate: eliminar } = useDeleteUserApiV1HubUsersUserIdDelete()

  const [email, setEmail] = useState('')
  const [rol, setRol] = useState<string>('user')
  const [nombre, setNombre] = useState('')
  /** La fila que espera confirmación de borrado. Estado de la pantalla, no del servidor. */
  const [porConfirmar, setPorConfirmar] = useState<string | null>(null)
  /** El alta arranca en la organizacion sobre la que ya se esta trabajando (REV.10). */
  const { organizaciones, elegida } = useOrganizacionElegida()
  const [organizacionDelAlta, setOrganizacionDelAlta] = useState('')
  useEffect(() => {
    if (!organizacionDelAlta && elegida) setOrganizacionDelAlta(elegida)
  }, [elegida, organizacionDelAlta])

  /**
   * El nombre de la organización de una fila, o que no tiene ninguna (REV.10).
   *
   * «Sin organización» y no una celda vacía: es una fila que hay que arreglar, no un dato que
   * falte. Y si el id apunta a algo que ya no está, se enseña el id en bruto en vez de
   * esconderlo: es la pista de que hay una fila huérfana.
   */
  function nombreDeOrganizacion(id: string | null | undefined): string {
    if (!id) return t('plataforma.usuarios.sin_organizacion')
    return organizaciones.find((o) => o.id === id)?.name ?? id
  }

  function darDeAlta(evento: React.FormEvent) {
    evento.preventDefault()
    crear(
      {
        data: {
          email,
          role: rol,
          display_name: nombre || null,
          organizacion_id: organizacionDelAlta || null,
        },
      },
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

  function borrarPersona(persona: UsuarioRead) {
    setPorConfirmar(null)
    eliminar({ userId: persona.id }, { onSuccess: invalidar })
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
        {organizaciones.length > 0 && (
          <div className="flex flex-col gap-1">
            <label htmlFor="usuario_organizacion" className="text-sm font-medium">
              {t('plataforma.usuarios.organizacion')}
            </label>
            <select
              id="usuario_organizacion"
              value={organizacionDelAlta}
              onChange={(e) => setOrganizacionDelAlta(e.target.value)}
              className="rounded-md border px-2 py-1 text-sm"
            >
              {organizaciones.map((o) => (
                <option key={o.id} value={o.id}>{o.name}</option>
              ))}
            </select>
          </div>
        )}
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
              <th>{t('plataforma.usuarios.organizacion')}</th>
              <th>{t('plataforma.usuarios.origen')}</th>
              <th>{t('plataforma.usuarios.ultimo_acceso')}</th>
              <th>{t('plataforma.usuarios.estado')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(personas ?? []).map((persona) => (
              <tr
                key={persona.id}
                data-testid={`persona-${persona.email}`}
                className="border-b"
              >
                <td className="py-2">{persona.email}</td>
                <td>{persona.display_name ?? '—'}</td>
                <td>{t(`plataforma.usuarios.roles.${persona.role}` as Parameters<typeof t>[0])}</td>
                {/* REV.10 — la columna que faltaba. `organizacion_id` existía con su clave
                    ajena desde AUTH.2 y la pantalla ni lo enseñaba ni lo pedía, así que se
                    podía dar de alta a gente sin organización sin enterarse. «Sin
                    organización» y no una celda vacía: es una fila que arreglar, no un dato
                    que falte. */}
                <td>{nombreDeOrganizacion(persona.organizacion_id)}</td>
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
                <td className="space-y-1 text-right">
                  {porConfirmar === persona.id ? (
                    /* Confirmación en la propia fila: borrar es la única acción de esta
                       pantalla que no se puede deshacer. */
                    <span className="flex flex-wrap items-center justify-end gap-2">
                      <span className="text-xs text-muted-foreground">
                        {t('plataforma.usuarios.confirmar_pregunta')}
                      </span>
                      <button
                        type="button"
                        onClick={() => borrarPersona(persona)}
                        className="text-xs font-medium text-destructive underline"
                      >
                        {t('plataforma.usuarios.confirmar')}
                      </button>
                      <button
                        type="button"
                        onClick={() => setPorConfirmar(null)}
                        className="text-xs underline"
                      >
                        {t('plataforma.usuarios.cancelar')}
                      </button>
                    </span>
                  ) : (
                    <span className="flex flex-wrap items-center justify-end gap-3">
                      {/* La cuenta de arranque vive en otra tabla: desactivarla desde aquí
                          daría un 404 y parecería un fallo de la pantalla. */}
                      {persona.origen !== ORIGEN_DE_ARRANQUE && (
                        <button
                          type="button"
                          onClick={() => cambiarActividad(persona)}
                          className="text-xs underline"
                        >
                          {persona.is_active
                            ? t('plataforma.usuarios.desactivar')
                            : t('plataforma.usuarios.reactivar')}
                        </button>
                      )}
                      {/* **Lo decide el servidor**, no esta pantalla: `puede_borrarse` viene en
                          el contrato. Calcularlo aquí por `last_login_at` pondría la misma
                          regla en dos sitios, y un día dirían cosas distintas. */}
                      {persona.puede_borrarse && (
                        <button
                          type="button"
                          onClick={() => setPorConfirmar(persona.id)}
                          className="text-xs text-destructive underline"
                        >
                          {t('plataforma.usuarios.eliminar')}
                        </button>
                      )}
                    </span>
                  )}
                  {/* El motivo, y no sólo la ausencia del botón: una fila sin acciones y sin
                      explicación se lee como «aquí no se puede hacer nada», y quien administra
                      no sabe si es una regla o algo roto. */}
                  {!persona.puede_borrarse && persona.motivo_no_borrable && (
                    <span className="block text-xs text-muted-foreground">
                      {persona.motivo_no_borrable}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
