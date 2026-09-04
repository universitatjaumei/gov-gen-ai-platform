import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useCategoriasDeDatos,
  useListarActividad,
} from '@/shared/api/generated/actividad/actividad'
import { descargarConAutorizacion } from '@/shared/api/download'
import { useOrganizacionElegida } from '@/shared/organizacion/useOrganizacionElegida'

/**
 * El registro de usos de IA de la organización (REG.6).
 *
 * La plataforma sabe todo de las conversaciones que pasan por ella y nada de las que no. Esta
 * pantalla enseña lo que declaran las herramientas de fuera —asistentes de escritorio, agentes de
 * código, integraciones propias— a través de `POST /api/v1/actividad`, al servicio de la
 * conservación de registros del AI Act y del registro de actividades de tratamiento del RGPD.
 *
 * **Lo que se ve son metadatos, y nunca el contenido.** No es una decisión de esta pantalla: el
 * contrato del evento rechaza cualquier campo de contenido, así que no hay texto que enseñar ni
 * que ocultar. Si algún día alguien pide «ver el prompt», la respuesta está en el contrato, no
 * aquí.
 *
 * **Nada del vocabulario está escrito en el frontend.** Las herramientas, los agentes y las
 * categorías de datos los declara quien registra: se pintan tal cual. Un catálogo aquí obligaría
 * a desplegar el panel cada vez que alguien conectara una herramienta nueva.
 *
 * **Los filtros los aplica el servidor.** Filtrar en el cliente daría un resultado distinto según
 * la página en la que estuvieras, y sobre un registro que alguien audita eso no es una molestia:
 * es una respuesta falsa.
 */
/**
 * El instante en que empieza o acaba un día del calendario **de quien mira la pantalla**.
 *
 * El `<input type="date">` da `AAAA-MM-DD`: un día del calendario, sin hora ni zona. El servidor
 * filtra por instantes. Componer `${fecha}T00:00:00Z` a mano parece equivalente y no lo es: fija
 * el límite en UTC, y para alguien en Madrid «desde el 1 de septiembre» empezaría a las dos de la
 * madrugada del 1 — dejando fuera, en silencio, las dos primeras horas del día que pidió. Sobre
 * un registro que alguien audita, una omisión que no se ve es peor que un error que se ve.
 *
 * Se construye con el constructor de `Date` sin `Z`, que interpreta la fecha en la zona del
 * navegador, y se manda en ISO. El rango es **cerrado por los dos extremos**: quien escribe
 * «hasta el 3» cuenta con lo que pasó el 3 por la tarde.
 */
function instanteDelDia(fecha: string, extremo: 'inicio' | 'fin'): string {
  const hora = extremo === 'inicio' ? '00:00:00.000' : '23:59:59.999'
  return new Date(`${fecha}T${hora}`).toISOString()
}

export function RegistroActividadPage() {
  const { t, i18n } = useTranslation('admin')

  const [herramienta, setHerramienta] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [pagina, setPagina] = useState(1)

  const TAMANO = 25

  /** Los parámetros de la consulta, sin los filtros vacíos.
   *
   * Un `herramienta=` vacío sería un filtro que el servidor tiene que decidir ignorar; mejor que
   * la petición diga lo que se pide y no lo que se dejó de pedir.
   */
  const parametros = useMemo(() => {
    const p: Record<string, string | number> = { page: pagina, size: TAMANO }
    if (herramienta) p.herramienta = herramienta
    if (desde) p.desde = instanteDelDia(desde, 'inicio')
    if (hasta) p.hasta = instanteDelDia(hasta, 'fin')
    return p
  }, [herramienta, desde, hasta, pagina])

  const { data, isLoading } = useListarActividad(parametros)

  /* El catálogo de categorías (REG.8), sólo para poner la etiqueta legible.
   *
   * Un código que no esté en el catálogo se enseña **crudo, tal como llegó**: el servidor acepta
   * cualquiera a propósito, así que llegarán, y esconderlos ocultaría la única señal de que al
   * catálogo le falta una entrada. Verlos ahí es lo que hace que alguien lo cure.
   *
   * **La organización se manda siempre que se sepa.** El catálogo es de cada organización, y un
   * superadministrador no tiene «la suya»: el servidor le responde 400 pidiéndole que la indique.
   * Sin esto, la pantalla pedía el catálogo sin decirla, recibía ese 400 y caía a los códigos
   * crudos — que es exactamente lo que se veía en el navegador, y lo que el test de esta pantalla
   * no podía ver porque mockea el hook. La elección es la del selector del panel, que ya se
   * recuerda entre pantallas. */
  const { elegida: organizacionElegida } = useOrganizacionElegida()
  const { data: categorias } = useCategoriasDeDatos(
    organizacionElegida ? { organizacion_id: organizacionElegida } : {},
    // Sin organización no hay catálogo que pedir, y pedirlo sólo dejaría un 400 en la consola de
    // quien mire. La tabla funciona igual: enseña los códigos tal cual.
    { query: { enabled: Boolean(organizacionElegida) } },
  )
  const etiquetaDeCategoria = useMemo(() => {
    const porCodigo = new Map((categorias ?? []).map((c) => [c.codigo, c.nombre]))
    return (codigo: string) => porCodigo.get(codigo) ?? codigo
  }, [categorias])

  const eventos = data?.items ?? []
  const total = data?.total ?? 0
  const hayMas = pagina * TAMANO < total
  const hayFiltro = Boolean(herramienta || desde || hasta)

  /** Cambiar un filtro vuelve a la primera página: la 3 de otro filtro no significa nada. */
  function filtrar(cambio: () => void) {
    cambio()
    setPagina(1)
  }

  function exportar() {
    const query = new URLSearchParams()
    if (herramienta) query.set('herramienta', herramienta)
    if (desde) query.set('desde', instanteDelDia(desde, 'inicio'))
    if (hasta) query.set('hasta', instanteDelDia(hasta, 'fin'))
    const cola = query.toString()

    // Por el cliente que pone el token, no por un `<a download>`: una navegación del navegador
    // no lleva la cabecera de autorización y el 401 llega disfrazado de fichero inexistente.
    void descargarConAutorizacion(
      `/api/v1/actividad/export${cola ? `?${cola}` : ''}`,
      'actividad_ia.csv',
    )
  }

  const fecha = (iso: string) => new Date(iso).toLocaleString(i18n.language)

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold">{t('registro.titulo')}</h2>
        <p className="text-sm text-muted-foreground">{t('registro.descripcion')}</p>
      </header>

      <div className="flex flex-wrap items-end gap-3 rounded-md border p-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="registro_herramienta" className="text-sm font-medium">
            {t('registro.herramienta')}
          </label>
          {/* Campo libre y no un desplegable: las herramientas las declara quien registra, así
              que el frontend no tiene de dónde sacar la lista sin inventarla. */}
          <input
            id="registro_herramienta"
            value={herramienta}
            onChange={(e) => filtrar(() => setHerramienta(e.target.value))}
            className="rounded-md border px-2 py-1 text-sm"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="registro_desde" className="text-sm font-medium">
            {t('registro.desde')}
          </label>
          <input
            id="registro_desde"
            type="date"
            value={desde}
            onChange={(e) => filtrar(() => setDesde(e.target.value))}
            className="rounded-md border px-2 py-1 text-sm"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="registro_hasta" className="text-sm font-medium">
            {t('registro.hasta')}
          </label>
          <input
            id="registro_hasta"
            type="date"
            value={hasta}
            onChange={(e) => filtrar(() => setHasta(e.target.value))}
            className="rounded-md border px-2 py-1 text-sm"
          />
        </div>

        <button
          type="button"
          onClick={exportar}
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
        >
          {t('registro.exportar')}
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">{t('registro.cargando')}</p>
      ) : eventos.length === 0 ? (
        /* Dos vacíos que no son el mismo, y decirlo importa.

           Un registro **sin nada** es el estado normal antes de que nadie haya conectado una
           herramienta, y ahí la explicación útil es cómo se empieza. Un **filtro sin
           coincidencias** es otra cosa: hay actividad, pero no ésa. Enseñar «todavía no hay
           actividad registrada» a quien acaba de filtrar es decirle algo falso, y lo natural es
           que concluya que el registro no funciona en vez de que su filtro no acierta. */
        <p className="rounded-md border border-dashed p-6 text-sm text-muted-foreground">
          {hayFiltro ? t('registro.sin_resultados') : t('registro.vacio')}
        </p>
      ) : (
        <>
          <table className="w-full text-sm">
            <caption className="sr-only">{t('registro.titulo')}</caption>
            <thead>
              <tr className="border-b text-left">
                <th scope="col" className="py-2">
                  {t('registro.ocurrido_en')}
                </th>
                <th scope="col">{t('registro.herramienta')}</th>
                <th scope="col">{t('registro.agente')}</th>
                <th scope="col">{t('registro.actor')}</th>
                <th scope="col">{t('registro.finalidad')}</th>
                <th scope="col">{t('registro.modelo')}</th>
                <th scope="col">{t('registro.categorias')}</th>
              </tr>
            </thead>
            <tbody>
              {eventos.map((evento) => (
                <tr key={evento.id} className="border-b align-top">
                  <td className="py-2 whitespace-nowrap">{fecha(evento.ocurrido_en)}</td>
                  <td>{evento.herramienta}</td>
                  <td className="text-muted-foreground">{evento.agente ?? '—'}</td>
                  <td className="font-mono text-xs">{evento.actor}</td>
                  <td>{evento.finalidad}</td>
                  <td className="text-muted-foreground">{evento.modelo_usado ?? '—'}</td>
                  <td className="text-xs text-muted-foreground">
                    {evento.categorias_datos.length > 0
                      ? evento.categorias_datos.map(etiquetaDeCategoria).join(', ')
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex items-center gap-3 text-sm">
            <span className="text-muted-foreground">
              {t('registro.total', { count: total })}
            </span>
            <button
              type="button"
              disabled={pagina === 1}
              onClick={() => setPagina((p) => p - 1)}
              className="rounded-md border px-3 py-1 disabled:opacity-50"
            >
              {t('registro.anterior')}
            </button>
            <button
              type="button"
              disabled={!hayMas}
              onClick={() => setPagina((p) => p + 1)}
              className="rounded-md border px-3 py-1 disabled:opacity-50"
            >
              {t('registro.siguiente')}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
