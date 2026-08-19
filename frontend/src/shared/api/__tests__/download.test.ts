import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiClient } from '../client'
import { descargarConAutorizacion } from '../download'

/**
 * Descargar un fichero que la API protege (CUR.5).
 *
 * Del usuario, probando el informe de auditoría: «los botones de descargar DOCX o PDF fallan.
 * Aparece un error de export.json el fitxer no es troba disponible». El endpoint está bien; el
 * enlace no puede pedirlo: un `<a href download>` es una navegación del navegador y **no lleva la
 * cabecera de autorización**, así que el servidor responde 401 y Chrome muestra su propio error de
 * descarga —que no menciona el 401 y parece un fichero que no existe—.
 *
 * La descarga tiene que ir por el mismo cliente que el resto de la aplicación, que es el único que
 * pone el token.
 */

const RUTA = '/api/v1/hub/sites/s1/report/export?format=docx'

describe('descargar un fichero protegido', () => {
  let clicado: HTMLAnchorElement | null = null

  beforeEach(() => {
    clicado = null
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:falso')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      clicado = this
    })
  })

  afterEach(() => vi.restoreAllMocks())

  it('pide el fichero al cliente autenticado, no al navegador', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ data: new Blob(['x']), headers: {} })

    await descargarConAutorizacion(RUTA, 'informe.docx')

    expect(get).toHaveBeenCalledWith(RUTA, { responseType: 'blob' })
  })

  it('entrega el fichero al navegador con el nombre que manda el servidor', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: new Blob(['x']),
      headers: { 'content-disposition': 'attachment; filename="informe_calidad_s1.docx"' },
    })

    await descargarConAutorizacion(RUTA, 'por-defecto.docx')

    expect(clicado?.download).toBe('informe_calidad_s1.docx')
  })

  it('usa el nombre por defecto cuando el servidor no manda ninguno', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: new Blob(['x']), headers: {} })

    await descargarConAutorizacion(RUTA, 'por-defecto.docx')

    expect(clicado?.download).toBe('por-defecto.docx')
  })

  it('libera el objeto temporal: una descarga no deja el fichero en memoria', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: new Blob(['x']), headers: {} })

    await descargarConAutorizacion(RUTA, 'informe.docx')

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:falso')
  })

  it('con cuerpo va por POST: hay ficheros que no son un recurso, son un resultado', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: new Blob(['a,b']), headers: {} })
    const get = vi.spyOn(apiClient, 'get')

    await descargarConAutorizacion('/api/v1/hub/site-reconnaissance', 'sitemap.csv', {
      root_url: 'https://www.uji.es/',
      formato: 'csv',
    })

    expect(post).toHaveBeenCalledWith(
      '/api/v1/hub/site-reconnaissance',
      { root_url: 'https://www.uji.es/', formato: 'csv' },
      { responseType: 'blob' },
    )
    expect(get).not.toHaveBeenCalled()
  })

  it('un fallo del servidor se propaga: quien llama tiene que poder decirlo en pantalla', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('No hay informe'))

    await expect(descargarConAutorizacion(RUTA, 'informe.docx')).rejects.toThrow('No hay informe')
  })
})
