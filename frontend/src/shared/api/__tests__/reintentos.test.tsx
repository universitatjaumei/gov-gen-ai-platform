import { describe, it, expect } from 'vitest'
import { noReintentarSiElServidorYaDecidio } from '@/shared/api/reintentos'

/**
 * INF.3 — un 4xx no se reintenta.
 *
 * `retry: 2` estaba puesto para todas las consultas, así que un 409 —«hay que aprobar dos
 * apartados», una respuesta deliberada del servidor— se pedía tres veces antes de que la
 * pantalla pudiera decir nada. Reintentar una decisión no la cambia: solo retrasa el mensaje
 * varios segundos, y en ese hueco la pantalla no está ni cargando ni en error.
 */
describe('INF.3 — reintentos', () => {
  it('should_not_retry_a_conflict', () => {
    expect(noReintentarSiElServidorYaDecidio(0, { response: { status: 409 } })).toBe(false)
  })

  it('should_not_retry_any_client_error', () => {
    for (const status of [400, 401, 403, 404, 409, 422]) {
      expect(noReintentarSiElServidorYaDecidio(0, { response: { status } })).toBe(false)
    }
  })

  it('should_retry_a_server_error_and_a_network_failure', () => {
    // Un 500 o una caída de red sí pueden ser pasajeros.
    expect(noReintentarSiElServidorYaDecidio(0, { response: { status: 500 } })).toBe(true)
    expect(noReintentarSiElServidorYaDecidio(0, new Error('Network Error'))).toBe(true)
  })

  it('should_stop_retrying_after_two_attempts', () => {
    expect(noReintentarSiElServidorYaDecidio(2, { response: { status: 500 } })).toBe(false)
  })
})
