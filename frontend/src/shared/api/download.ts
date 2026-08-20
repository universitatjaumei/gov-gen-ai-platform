import { apiClient } from './client'

/**
 * Descargar un fichero que la API protege (CUR.5).
 *
 * Un `<a href download>` apuntando a la API es una navegación del navegador, y una navegación **no
 * lleva la cabecera de autorización**: el servidor responde 401 y Chrome enseña su propio error de
 * descarga, que no menciona el 401 y parece un fichero que no existe. Es lo que le pasó al usuario
 * con los botones de DOCX y PDF del informe de auditoría.
 *
 * El fichero se pide por el mismo cliente que el resto de la aplicación —el único que pone el
 * token— y se entrega al navegador desde memoria.
 */
export async function descargarConAutorizacion(
  ruta: string,
  nombrePorDefecto: string,
  cuerpo?: unknown,
): Promise<void> {
  // Con cuerpo va por POST: el CSV del reconocimiento (CUR.6) no es un recurso que exista en una
  // URL, es el resultado de un recorrido que se pide con sus parámetros.
  let respuesta
  try {
    respuesta = cuerpo
      ? await apiClient.post(ruta, cuerpo, { responseType: 'blob' })
      : await apiClient.get(ruta, { responseType: 'blob' })
  } catch (fallo) {
    // INF.3 — con `responseType: 'blob'` el cuerpo de **error** también llega como Blob, así que
    // `error.response.data.detail` es `undefined` y el motivo del rechazo es ilegible: quien
    // llama no puede distinguir «hay que aprobar dos apartados» de un fallo cualquiera. Es la
    // razón de fondo por la que «Exportar a Word» no decía nada. Se reconstruye el JSON.
    throw await conCuerpoLegible(fallo)
  }

  const url = URL.createObjectURL(respuesta.data as Blob)
  try {
    const enlace = document.createElement('a')
    enlace.href = url
    // El nombre lo decide el servidor cuando lo declara: es quien sabe si el «PDF» acabó siendo
    // un DOCX (el fallback sin LibreOffice de VER.7).
    enlace.download = nombreDeLaRespuesta(respuesta.headers) ?? nombrePorDefecto
    enlace.click()
  } finally {
    URL.revokeObjectURL(url)
  }
}

/** El `filename` de `Content-Disposition`, si viene. */
function nombreDeLaRespuesta(cabeceras: unknown): string | null {
  const cabecera = (cabeceras as Record<string, string> | undefined)?.['content-disposition']
  if (!cabecera) return null
  const coincidencia = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cabecera)
  return coincidencia ? decodeURIComponent(coincidencia[1]) : null
}

/**
 * El mismo error, pero con el cuerpo parseado si venía como Blob.
 *
 * Axios con `responseType: 'blob'` entrega también el cuerpo de error como Blob, así que el
 * `detail` que el servidor manda —`pending_block_ids`, `missing_slots`— queda inalcanzable para
 * quien captura el fallo. Se lee el Blob como texto y se sustituye `response.data` por el JSON;
 * si no es JSON, se devuelve el error tal cual, sin inventar nada.
 */
async function conCuerpoLegible(fallo: unknown): Promise<unknown> {
  const respuesta = (fallo as { response?: { data?: unknown } })?.response
  if (!respuesta || !(respuesta.data instanceof Blob)) return fallo

  try {
    respuesta.data = JSON.parse(await respuesta.data.text())
  } catch {
    // Un cuerpo que no es JSON no dice nada más de lo que ya dice el código de estado.
  }
  return fallo
}
