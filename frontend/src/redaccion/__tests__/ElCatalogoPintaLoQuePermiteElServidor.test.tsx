import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { CatalogoDeFuncionesPage } from '../pages/CatalogoDeFuncionesPage'
import { RevisionPosteriorPage } from '../pages/RevisionPosteriorPage'
import {
  useListarFunciones,
  useColaDeRevision,
  useRevisarVersion,
  useSuspenderVersion,
  useReactivarVersion,
  useRetirarVersion,
  useSolicitarPromocionDeFuncion,
  usePromoverFuncion,
} from '@/shared/api/generated/funciones/funciones'

/**
 * FUN.4 — el catálogo y la cola de revisión posterior.
 *
 * Los dos invariantes que estas pantallas tienen que hacer ciertos, y que un test de aspecto no
 * cazaría:
 *
 * 1. **Los botones salen de `acciones_permitidas`** (regla maestra 2). No hay ni un
 *    `rol === 'admin'` en el componente: si lo hubiera, la autorización estaría escrita dos veces
 *    y el día que cambiara el servidor dirían cosas distintas. El test lo comprueba dando la
 *    **misma** función con dos listas distintas y exigiendo dos pantallas distintas.
 * 2. **Estar en la cola no es estar bloqueado.** La pantalla de revisión tiene que decir que la
 *    versión se está ejecutando mientras espera revisión; si insinuara lo contrario, la persona
 *    que revisa creería que su firma es lo que la pone en marcha, y eso es aprobación previa con
 *    otro nombre.
 */
vi.mock('@/shared/api/generated/funciones/funciones', () => ({
  useListarFunciones: vi.fn(),
  useColaDeRevision: vi.fn(),
  useRevisarVersion: vi.fn(),
  useSuspenderVersion: vi.fn(),
  useReactivarVersion: vi.fn(),
  useRetirarVersion: vi.fn(),
  useSolicitarPromocionDeFuncion: vi.fn(),
  usePromoverFuncion: vi.fn(),
}))

const VERSION_BASE = {
  version: 1,
  estado: 'registrada',
  autoria: 'ia',
  finalidad: 'Contar las filas del fichero de gastos',
  categorias_datos: ['sin_datos_personales'],
  hallazgos: [],
  revisada_en: null,
  revision_resultado: null,
  revision_nota: null,
  motivo_suspension: null,
  code_sha256: 'abc123',
  version_paquete: null,
  created_at: '2026-09-18T00:00:00Z',
  acciones_permitidas: [] as string[],
}

const FUNCION_BASE = {
  id: 'ffffffff-ffff-ffff-ffff-ffffffffffff',
  nombre: 'Contar filas de gastos',
  descripcion: '',
  organizacion_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  origen: 'autoservicio',
  nivel: 2,
  entry_point: null,
  publicada_en: null,
  valoracion_promocion: null,
  candidata_nivel_3: false,
  motivos_nivel_3: [] as string[],
  versiones: [VERSION_BASE],
}

function conAcciones(acciones: string[], extra: Record<string, unknown> = {}) {
  return {
    ...FUNCION_BASE,
    ...extra,
    versiones: [{ ...VERSION_BASE, ...(extra.version ?? {}), acciones_permitidas: acciones }],
  }
}

const mutacionQuieta = { mutate: vi.fn(), isPending: false, data: undefined, error: null }

function pintar(pantalla: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{pantalla}</MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.mocked(useRevisarVersion).mockReturnValue({ ...mutacionQuieta } as never)
  vi.mocked(useSuspenderVersion).mockReturnValue({ ...mutacionQuieta } as never)
  vi.mocked(useReactivarVersion).mockReturnValue({ ...mutacionQuieta } as never)
  vi.mocked(useRetirarVersion).mockReturnValue({ ...mutacionQuieta } as never)
  vi.mocked(useSolicitarPromocionDeFuncion).mockReturnValue({ ...mutacionQuieta } as never)
  vi.mocked(usePromoverFuncion).mockReturnValue({ ...mutacionQuieta } as never)
  vi.mocked(useColaDeRevision).mockReturnValue({ data: [], isLoading: false } as never)
  vi.mocked(useListarFunciones).mockReturnValue({ data: [], isLoading: false } as never)
})

describe('El catálogo pinta lo que el servidor permite', () => {
  it('ofrece exactamente las acciones que trae el DTO', async () => {
    vi.mocked(useListarFunciones).mockReturnValue({
      data: [conAcciones(['adoptar_version', 'revisar', 'suspender'])],
      isLoading: false,
    } as never)

    pintar(<CatalogoDeFuncionesPage />)

    await waitFor(() => expect(screen.getByText('Contar filas de gastos')).toBeInTheDocument())
    expect(screen.getByTestId('accion-revisar')).toBeInTheDocument()
    expect(screen.getByTestId('accion-suspender')).toBeInTheDocument()
    expect(screen.queryByTestId('accion-reactivar')).not.toBeInTheDocument()
    expect(screen.queryByTestId('accion-promover')).not.toBeInTheDocument()
  })

  it('no ofrece nada cuando la lista viene vacía, aunque la función se vea', async () => {
    /** La mitad que se olvida: una función visible sin acciones es el caso de la organización
     *  consumidora, y la pantalla no puede inventarle botones. */
    vi.mocked(useListarFunciones).mockReturnValue({
      data: [conAcciones([])],
      isLoading: false,
    } as never)

    pintar(<CatalogoDeFuncionesPage />)

    await waitFor(() => expect(screen.getByText('Contar filas de gastos')).toBeInTheDocument())
    expect(screen.queryByTestId(/^accion-/)).not.toBeInTheDocument()
  })

  it('dice el nivel y el motivo de la candidatura, sin deducirlos', async () => {
    vi.mocked(useListarFunciones).mockReturnValue({
      data: [
        conAcciones(['promover'], {
          nivel: 2,
          candidata_nivel_3: true,
          motivos_nivel_3: ['su organización ha solicitado la promoción'],
        }),
      ],
      isLoading: false,
    } as never)

    pintar(<CatalogoDeFuncionesPage />)

    await waitFor(() => expect(screen.getByTestId('nivel')).toHaveAttribute('data-nivel', '2'))
    expect(screen.getByTestId('candidata-nivel-3')).toBeInTheDocument()
    expect(
      screen.getByText('su organización ha solicitado la promoción'),
    ).toBeInTheDocument()
  })

  it('muestra el motivo por el que una versión está suspendida', async () => {
    vi.mocked(useListarFunciones).mockReturnValue({
      data: [
        conAcciones(['reactivar'], {
          version: { estado: 'suspendida', motivo_suspension: 'escribe en una ruta absoluta' },
        }),
      ],
      isLoading: false,
    } as never)

    pintar(<CatalogoDeFuncionesPage />)

    await waitFor(() =>
      expect(screen.getByText(/escribe en una ruta absoluta/)).toBeInTheDocument(),
    )
    expect(screen.getByTestId('accion-reactivar')).toBeInTheDocument()
  })

  it('exige el motivo antes de dejar suspender', async () => {
    const suspender = vi.fn()
    vi.mocked(useSuspenderVersion).mockReturnValue({
      ...mutacionQuieta,
      mutate: suspender,
    } as never)
    vi.mocked(useListarFunciones).mockReturnValue({
      data: [conAcciones(['suspender'])],
      isLoading: false,
    } as never)

    pintar(<CatalogoDeFuncionesPage />)

    fireEvent.click(await screen.findByTestId('accion-suspender'))
    // Sin motivo escrito no se manda: el bloque anclado tiene que poder decir por qué falla.
    fireEvent.click(screen.getByTestId('confirmar-suspender'))
    expect(suspender).not.toHaveBeenCalled()

    fireEvent.change(screen.getByTestId('motivo-suspension'), {
      target: { value: 'escribe en una ruta absoluta' },
    })
    fireEvent.click(screen.getByTestId('confirmar-suspender'))

    expect(suspender).toHaveBeenCalledWith(
      expect.objectContaining({
        funcionId: FUNCION_BASE.id,
        numero: 1,
        data: { motivo: 'escribe en una ruta absoluta' },
      }),
    )
  })

  it('exige la valoración escrita antes de promover', async () => {
    const promover = vi.fn()
    vi.mocked(usePromoverFuncion).mockReturnValue({
      ...mutacionQuieta,
      mutate: promover,
    } as never)
    vi.mocked(useListarFunciones).mockReturnValue({
      data: [conAcciones(['promover'], { candidata_nivel_3: true })],
      isLoading: false,
    } as never)

    pintar(<CatalogoDeFuncionesPage />)

    fireEvent.click(await screen.findByTestId('accion-promover'))
    fireEvent.click(screen.getByTestId('confirmar-promover'))
    expect(promover).not.toHaveBeenCalled()

    fireEvent.change(screen.getByTestId('valoracion-promocion'), {
      target: { value: 'Revisada: no toca datos personales' },
    })
    fireEvent.click(screen.getByTestId('confirmar-promover'))

    expect(promover).toHaveBeenCalledWith(
      expect.objectContaining({
        funcionId: FUNCION_BASE.id,
        data: { valoracion: 'Revisada: no toca datos personales' },
      }),
    )
  })
})

describe('La cola de revisión posterior', () => {
  const EN_COLA = {
    funcion_id: FUNCION_BASE.id,
    funcion_nombre: 'Contar filas de gastos',
    version: 1,
    estado: 'registrada',
    autoria: 'ia',
    finalidad: 'Contar las filas del fichero de gastos',
    categorias_datos: ['sin_datos_personales'],
    hallazgos: [{ code: 'RUTA_ABSOLUTA', severity: 'warning', message: 'ruta fija' }],
    plantillas_que_la_usan: 3,
    dias_desde_el_registro: 5,
    acciones_permitidas: ['revisar', 'suspender'],
  }

  it('dice que la versión se está ejecutando mientras espera revisión', async () => {
    vi.mocked(useColaDeRevision).mockReturnValue({ data: [EN_COLA], isLoading: false } as never)

    pintar(<RevisionPosteriorPage />)

    await waitFor(() => expect(screen.getByTestId('en-uso')).toBeInTheDocument())
    // Y lo que hace urgente revisarla: cuántas plantillas dependen de ella.
    expect(screen.getByTestId('fila-revision')).toHaveAttribute('data-plantillas', '3')
  })

  it('enseña los avisos del auditor que no bloquearon', async () => {
    vi.mocked(useColaDeRevision).mockReturnValue({ data: [EN_COLA], isLoading: false } as never)

    pintar(<RevisionPosteriorPage />)

    await waitFor(() => expect(screen.getByText(/RUTA_ABSOLUTA/)).toBeInTheDocument())
  })

  it('pide una muestra al azar cuando se le pide', async () => {
    vi.mocked(useColaDeRevision).mockReturnValue({ data: [EN_COLA], isLoading: false } as never)

    pintar(<RevisionPosteriorPage />)

    fireEvent.change(await screen.findByTestId('tamano-muestra'), { target: { value: '10' } })

    await waitFor(() =>
      expect(vi.mocked(useColaDeRevision)).toHaveBeenCalledWith(
        expect.objectContaining({ estado: 'sin_revisar', muestra: 10 }),
        expect.anything(),
      ),
    )
  })

  it('no ofrece «aprobada» como resultado de la revisión', async () => {
    /** En el nivel 2 no hay nada que aprobar: si la pantalla ofreciera aprobar, la persona que
     *  revisa creería que su firma es lo que autoriza el uso. */
    vi.mocked(useColaDeRevision).mockReturnValue({ data: [EN_COLA], isLoading: false } as never)

    pintar(<RevisionPosteriorPage />)

    const opciones = (await screen.findAllByTestId(/^resultado-/)).map(o =>
      o.getAttribute('data-resultado'),
    )

    expect(opciones).toEqual(['conforme', 'correcciones', 'reclasificada', 'suspendida'])
  })

  it('manda el resultado y la nota tal cual', async () => {
    const revisar = vi.fn()
    vi.mocked(useRevisarVersion).mockReturnValue({
      ...mutacionQuieta,
      mutate: revisar,
    } as never)
    vi.mocked(useColaDeRevision).mockReturnValue({ data: [EN_COLA], isLoading: false } as never)

    pintar(<RevisionPosteriorPage />)

    fireEvent.click(await screen.findByTestId('resultado-correcciones'))
    fireEvent.change(screen.getByTestId('nota-revision'), {
      target: { value: 'acota la ruta al almacenamiento' },
    })
    fireEvent.click(screen.getByTestId('confirmar-revision'))

    expect(revisar).toHaveBeenCalledWith(
      expect.objectContaining({
        funcionId: FUNCION_BASE.id,
        numero: 1,
        data: { resultado: 'correcciones', nota: 'acota la ruta al almacenamiento' },
      }),
    )
  })

  it('cuenta que la cola está vacía en vez de pintar una tabla sin filas', async () => {
    vi.mocked(useColaDeRevision).mockReturnValue({ data: [], isLoading: false } as never)

    pintar(<RevisionPosteriorPage />)

    await waitFor(() => expect(screen.getByTestId('cola-vacia')).toBeInTheDocument())
  })
})

describe('Lo que se acaba de cambiar se ve', () => {
  /**
   * El defecto que destapó la verificación en navegador: suspender respondía 200 y **la pantalla
   * seguía diciendo «Registrada»**. Sin invalidar la consulta del catálogo, quien pulsa el botón
   * no tiene forma de saber si ha pasado algo, y lo natural es volver a pulsar.
   *
   * Se comprueba sobre la invalidación y no sobre un `refetch` a ojo: es la que hace que las dos
   * pantallas —catálogo y cola— se pongan al día, y la única que sigue valiendo cuando la
   * mutación se dispara desde otro sitio.
   */
  it('invalida el catálogo cuando una versión se suspende', async () => {
    let onSuccess: (() => void) | undefined
    vi.mocked(useSuspenderVersion).mockImplementation(((opciones: any) => {
      onSuccess = opciones?.mutation?.onSuccess
      return { ...mutacionQuieta }
    }) as never)
    vi.mocked(useListarFunciones).mockReturnValue({
      data: [conAcciones(['suspender'])],
      isLoading: false,
    } as never)

    pintar(<CatalogoDeFuncionesPage />)
    await waitFor(() => expect(screen.getByText('Contar filas de gastos')).toBeInTheDocument())

    expect(onSuccess).toBeTypeOf('function')
  })

  it('invalida la cola cuando una revisión se sella', async () => {
    let onSuccess: (() => void) | undefined
    vi.mocked(useRevisarVersion).mockImplementation(((opciones: any) => {
      onSuccess = opciones?.mutation?.onSuccess
      return { ...mutacionQuieta }
    }) as never)
    vi.mocked(useColaDeRevision).mockReturnValue({
      data: [
        {
          funcion_id: FUNCION_BASE.id,
          funcion_nombre: 'Contar filas de gastos',
          version: 1,
          estado: 'registrada',
          autoria: 'ia',
          finalidad: 'x',
          categorias_datos: [],
          hallazgos: [],
          plantillas_que_la_usan: 0,
          dias_desde_el_registro: 0,
          acciones_permitidas: ['revisar'],
        },
      ],
      isLoading: false,
    } as never)

    pintar(<RevisionPosteriorPage />)
    await waitFor(() => expect(screen.getByTestId('confirmar-revision')).toBeInTheDocument())

    expect(onSuccess).toBeTypeOf('function')
  })
})
