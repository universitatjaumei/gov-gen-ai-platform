import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

// La base se lee aquí y no de `shared/api/client`: importar aquel módulo arrastraría axios al
// bundle del widget, que es un IIFE aparte y hoy no lo lleva. Es la misma expresión que usa
// `client.ts`, y esta petición no necesita interceptor porque va sin credencial.
const BASE_DE_LA_API: string = import.meta.env.VITE_API_URL ?? ''

/**
 * El enlace al código fuente que exige el §13 de la AGPL (AIS.6).
 *
 * **Por qué es configuración y no una URL fija.** El §13 obliga a quien ejecuta una versión
 * **modificada** a ofrecer *el fuente de esa versión* —el fork, en el commit desplegado— a los
 * usuarios de esa instancia. Una URL escrita aquí apuntaría al principal, así que cualquier
 * despliegue modificado estaría incumpliendo mientras cree que cumple. Por eso sale de
 * `SOURCE_URL`, que la pone quien despliega.
 *
 * **Y por qué también en el widget.** La obligación es frente a *los usuarios que interactúan
 * remotamente*, y la ciudadanía que usa el chatbot embebido lo es. Es el caso que el README
 * señala como «el que se olvida», así que este componente sirve a los dos sitios.
 *
 * Vacío = no se pinta nada. Quien despliega el código **sin modificar** no queda sujeto a esta
 * obligación concreta, así que forzar un enlace ahí sería inventarse un requisito.
 */
interface EnlaceAlFuenteProps {
  className?: string
  /**
   * Estilo en línea, para el widget.
   *
   * El widget se embebe en webs ajenas y por eso se pinta con estilos en línea en vez de con
   * clases: una clase de Tailwind no existe en el sitio anfitrión, así que el enlace saldría
   * sin formato. No es una preferencia, es la misma razón por la que el resto del componente
   * lo hace así.
   */
  style?: React.CSSProperties
}

export function EnlaceAlFuente({ className, style }: EnlaceAlFuenteProps) {
  const { t } = useTranslation('common')
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    let vivo = true
    // Sin react-query a propósito: esto lo consume también el widget, que es un bundle aparte
    // y no monta el proveedor. Es una petición por carga y sin credencial.
    //
    // Envuelto en `async` y con `try` alrededor de la propia llamada, no sólo con `.catch()`:
    // el widget se embebe en webs ajenas, donde `fetch` puede estar parcheado, restringido por
    // CSP o devolver algo que no es una promesa. Con la cadena `.then()` a pelo, un `fetch` que
    // no devolviera promesa lanzaba `Cannot read properties of undefined (reading 'then')`
    // **de forma síncrona dentro del efecto**, o sea que se llevaba por delante el árbol entero
    // en vez de dejar el enlace sin pintar. Lo destapó CI: 25 tests del widget en rojo.
    //
    // La regla que ya estaba escrita abajo —«que no se pueda leer no rompe la pantalla»— es la
    // correcta; lo que fallaba es que la forma del código no la cumplía en todos los casos.
    const leer = async () => {
      try {
        const respuesta = await fetch(`${BASE_DE_LA_API}/api/v1/instancia`)
        if (!respuesta?.ok) return
        const datos = await respuesta.json()
        if (vivo) setUrl(datos?.source_url ?? null)
      } catch {
        // El enlace no aparece y ya está.
      }
    }
    void leer()
    return () => {
      vivo = false
    }
  }, [])

  if (!url) return null

  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer noopener"
      className={className ?? 'text-xs text-muted-foreground underline hover:no-underline'}
      style={style}
      data-testid="enlace-al-fuente"
    >
      {t('licencia.codigo_fuente')}
    </a>
  )
}
