import type { ReactNode } from 'react'
import { Navigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { primeraRutaConcedida, useModulos } from './useModulos'

/**
 * Una zona de la aplicación que exige tener su módulo concedido (INF.7).
 *
 * El servidor ya rechaza con 403 los endpoints del módulo; esto evita que alguien llegue a una
 * pantalla que solo puede enseñar errores. Las dos capas son necesarias: quitar el enlace del
 * menú no impide escribir la URL, y dejar la pantalla accesible sin datos es peor que decir
 * que no hay acceso.
 *
 * **Mientras no se sabe, no se echa a nadie.** Tratar «todavía no ha llegado la lista» como
 * «no tienes acceso» expulsaría a la gente de su propia pantalla en cada recarga.
 */
export function RutaDeModulo({ modulo, children }: { modulo: string; children: ReactNode }) {
  const { t } = useTranslation('common')
  const { modulos, cargando } = useModulos()

  if (cargando) return <div className="p-4">{t('loading')}</div>
  if (!modulos.includes(modulo)) return <Navigate to="/sin-acceso" replace />
  return <>{children}</>
}

/**
 * A dónde entra alguien que acaba de identificarse.
 *
 * Era `/hub/chatbots` fijo para todo el mundo. Con el módulo abierto a toda la organización eso
 * significa aterrizar en los chatbots institucionales sin tener nada que hacer ahí.
 */
export function Aterrizaje() {
  const { t } = useTranslation('common')
  const { modulos, cargando } = useModulos()

  if (cargando) return <div className="p-4">{t('loading')}</div>
  return <Navigate to={primeraRutaConcedida(modulos)} replace />
}

/**
 * Una dirección que no existe (REV.5).
 *
 * El comodín `*` de las rutas montaba `Aterrizaje`, así que **cualquier URL equivocada acababa
 * en el primer módulo concedido**, sin decir que la dirección no existía. Lo destapó la cola de
 * vigencia: los documentos del corpus cargados desde carpeta llevan un nombre de fichero en
 * `canonical_url`, el enlace lo resolvía como ruta relativa y la pestaña nueva aterrizaba en
 * Informes — que es `informes`, el primero de `RUTA_DEL_MODULO`. Parecía un fallo del módulo de
 * informes y era un 404 disfrazado de redirección.
 *
 * Aterrizar es lo correcto en la raíz, donde no se ha pedido nada concreto. En una ruta que no
 * existe, no: hay que decirlo.
 */
export function NoEncontrado() {
  const { t } = useTranslation('admin')
  return (
    <div className="p-8 max-w-lg" data-testid="no-encontrado">
      <h1 className="text-lg font-medium mb-2">{t('no_encontrado.titulo')}</h1>
      <p className="text-sm text-muted-foreground">{t('no_encontrado.texto')}</p>
      {/* El comodín vive fuera del layout, así que aquí no hay menú lateral al que remitir:
          sin esta salida, la pantalla es un callejón del que sólo se sale escribiendo una URL.
          `Link` y no `<a>`, para no recargar la aplicación entera. */}
      <Link to="/" className="mt-3 inline-block text-sm text-primary underline">
        {t('no_encontrado.volver')}
      </Link>
    </div>
  )
}

/** Sin ningún módulo concedido no hay a dónde ir, y hay que decirlo en vez de rebotar. */
export function SinAcceso() {
  const { t } = useTranslation('admin')
  return (
    <div className="p-8 max-w-lg" data-testid="sin-acceso">
      <h1 className="text-lg font-medium mb-2">{t('sin_acceso.titulo')}</h1>
      <p className="text-sm text-muted-foreground">{t('sin_acceso.texto')}</p>
    </div>
  )
}
