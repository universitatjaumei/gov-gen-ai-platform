/**
 * Cuándo merece la pena reintentar una consulta (INF.3).
 *
 * `retry: 2` estaba puesto para **todas** las consultas, así que un 409 —«hay que aprobar dos
 * apartados», que es una decisión deliberada del servidor y no una avería— se pedía tres veces
 * antes de que la pantalla pudiera decir nada. Reintentar una decisión no la cambia: solo
 * retrasa el mensaje, y mientras espera, la consulta no está ni cargando ni en error, así que
 * la pantalla no puede pintar ni «cargando» ni el motivo. Es un hueco de varios segundos en el
 * que la interfaz parece muerta, que es justo lo que este bloque está quitando.
 *
 * Un 5xx o una caída de red sí pueden ser pasajeros: esos se reintentan.
 */
export function noReintentarSiElServidorYaDecidio(intentos: number, fallo: unknown): boolean {
  const estado = (fallo as { response?: { status?: number } })?.response?.status
  if (typeof estado === 'number' && estado >= 400 && estado < 500) return false
  return intentos < 2
}
