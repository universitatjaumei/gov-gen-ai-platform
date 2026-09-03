import { useTranslation } from 'react-i18next'
import { useOpcionesDeLengua } from '@/shared/api/generated/hub-opciones/hub-opciones'

/** El separador de `fixed:<código>`. Se compone y se parte aquí, en un solo sitio. */
const SEPARADOR = ':'

/**
 * El modo de política de lengua, elegido desde el contrato (LANG.2).
 *
 * **Dos cosas que el panel decía y no eran verdad** hasta aquí, y las dos desaparecen por
 * construcción al traer la lista del servidor:
 *
 * - Ofrecía **`strict`**, y la factoría del grafo nunca compuso `StrictLanguagePolicy`: era una
 *   opción que no hacía nada. Después de LANG.1 es peor, porque además el servidor la rechaza.
 * - Los valores por defecto de organización sugerían **`neutral`**, que no es ningún valor
 *   válido: es el nombre de la clase, y el modo se llama `none`.
 *
 * Es el defecto que PLAT.2 documentó como «el menú promete lo que la API niega».
 *
 * **El catálogo trae la lengua en el código del corpus**, que es `val` y no `ca`. Si el panel
 * enviara `fixed:ca` la validación del servidor lo aceptaría —la forma es correcta— y la
 * preferencia no casaría con ninguna versión de ninguna norma, en silencio.
 *
 * **`requiere_lengua` lo dice el servidor**, y no se deduce de que el valor sea «fixed»: el día
 * que haya un segundo modo paramétrico, esto no hay que tocarlo.
 */
export function SelectorDeModoDeLengua({
  valor,
  onChange,
  idPrefijo = 'modo-de-lengua',
}: {
  valor: string
  onChange: (valor: string) => void
  idPrefijo?: string
}) {
  const { t } = useTranslation('admin')
  const { data: catalogo } = useOpcionesDeLengua()

  // Mientras el catálogo no ha llegado no se pinta nada. Enseñar opciones propias sería
  // volver a escribir la lista en React, y un `onChange` de más pisaría el valor guardado.
  if (!catalogo) return null

  const [modoActual, lenguaActual] = valor.split(SEPARADOR)
  const modo = catalogo.modos.find((m) => m.valor === modoActual)
  const primeraLengua = catalogo.lenguas[0]?.codigo ?? ''

  function elegirModo(nuevo: string) {
    const elegido = catalogo!.modos.find((m) => m.valor === nuevo)
    // Al elegir un modo paramétrico se compone ya con una lengua: mandar `fixed:` a secas
    // sería un 422 al guardar, y el error saldría lejos de donde se eligió.
    onChange(
      elegido?.requiere_lengua
        ? `${nuevo}${SEPARADOR}${lenguaActual || primeraLengua}`
        : nuevo
    )
  }

  return (
    <>
      <div>
        <label htmlFor={`${idPrefijo}-modo`} className="text-sm font-medium">
          {t('hub.chatbot_language_mode')}
        </label>
        <select
          id={`${idPrefijo}-modo`}
          value={modoActual}
          onChange={(e) => elegirModo(e.target.value)}
          className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
        >
          {catalogo.modos.map((m) => (
            <option key={m.valor} value={m.valor}>
              {t(`hub.language_mode_${m.valor}` as Parameters<typeof t>[0])}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-muted-foreground">
          {t(`hub.language_mode_${modoActual}_ayuda` as Parameters<typeof t>[0])}
        </p>
      </div>
      {modo?.requiere_lengua && (
        <div>
          <label htmlFor={`${idPrefijo}-lengua`} className="text-sm font-medium">
            {t('hub.chatbot_language_fixed_code')}
          </label>
          <select
            id={`${idPrefijo}-lengua`}
            value={lenguaActual || primeraLengua}
            onChange={(e) => onChange(`${modoActual}${SEPARADOR}${e.target.value}`)}
            className="w-full mt-1 px-3 py-2 border rounded-md text-sm bg-background"
          >
            {catalogo.lenguas.map((l) => (
              <option key={l.codigo} value={l.codigo}>
                {l.etiqueta}
              </option>
            ))}
          </select>
        </div>
      )}
    </>
  )
}
