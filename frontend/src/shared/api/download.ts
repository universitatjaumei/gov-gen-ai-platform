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
): Promise<void> {
  const respuesta = await apiClient.get(ruta, { responseType: 'blob' })

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
