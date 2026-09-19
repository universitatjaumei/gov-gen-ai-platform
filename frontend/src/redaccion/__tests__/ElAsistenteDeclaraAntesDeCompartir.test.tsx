import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { ScriptProposalWizardPage } from '../pages/ScriptProposalWizardPage'
import {
  useProposeScript,
  useDescribeTestData,
  usePreviewPdfSpans,
  useAnonymizeTestData,
  useTestScriptProposal,
  useValidateTestResult,
  useSaveScriptToPrivateTemplate,
  useSubmitScriptForReview,
} from '@/shared/api/generated/redaccion-scripts/redaccion-scripts'

/**
 * El defecto: **el asistente no declaraba nada, y el registro lo exige desde FUN.3.**
 *
 * `handleSave` hacía `mutate({ proposalId }, {})` —sin cuerpo—, así que el endpoint construía una
 * `DeclaracionResponsable()` vacía, `ContratoFuncion` la rechazaba por no tener finalidad, y el
 * botón «Guardar» respondía **422 `DECLARACION_INCOMPLETA`**. O sea: la única pantalla que da de
 * alta una función llevaba roto todo el bloque FUN, y no es un detalle de formulario — es el acto
 * de compartir del nivel 2 de la Instrucció 02/2026, que **no existe sin declaración**.
 *
 * **Las dos suites siguieron en verde**, y por eso el test se escribe así y no de otra manera:
 *
 * - el de backend sólo cubría el camino **con** declaración (lo actualicé yo en FUN.3, y al
 *   arreglar el test dejé de mirar quién llamaba);
 * - el de frontend usaba `toHaveBeenCalledWith(objectContaining({ proposalId }))`, y
 *   `objectContaining` **no comprueba lo que falta**. Aquí se afirma el cuerpo entero a
 *   propósito: es la única forma de que «no manda la declaración» sea un rojo.
 */
vi.mock('@/shared/api/generated/redaccion-scripts/redaccion-scripts', () => ({
  useProposeScript: vi.fn(),
  useDescribeTestData: vi.fn(),
  usePreviewPdfSpans: vi.fn(),
  useAnonymizeTestData: vi.fn(),
  useTestScriptProposal: vi.fn(),
  useValidateTestResult: vi.fn(),
  useSaveScriptToPrivateTemplate: vi.fn(),
  useSubmitScriptForReview: vi.fn(),
}))

const quieto = { mutate: vi.fn(), isPending: false, data: undefined, error: null }

let guardar: ReturnType<typeof vi.fn>

function pintar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ScriptProposalWizardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

/** Lleva el asistente hasta el paso 7 con la prueba ya validada, que es su estado real al
 *  guardar: sin `validated` el botón está deshabilitado por otra razón y el test no mediría
 *  la declaración. */
function enElUltimoPaso() {
  // El asistente salta al paso 7 solo cuando la propuesta y la prueba han tenido exito: se
  // reproduce con `isSuccess`, que es lo que miran sus dos `useEffect`.
  vi.mocked(useProposeScript).mockReturnValue({
    ...quieto,
    isSuccess: true,
    data: {
      proposal_id: 'prop-1',
      code: 'result = {}',
      audit_result: { approved: true, risk_level: 'SAFE', findings: [] },
    },
  } as never)
  vi.mocked(useTestScriptProposal).mockReturnValue({
    ...quieto,
    isSuccess: true,
    data: { result: { tables: [], metrics: [], free_text: 'ok' } },
  } as never)
  vi.mocked(useValidateTestResult).mockReturnValue({
    ...quieto,
    data: { validated: true },
  } as never)
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  guardar = vi.fn()
  vi.mocked(useProposeScript).mockReturnValue({ ...quieto } as never)
  vi.mocked(useDescribeTestData).mockReturnValue({ ...quieto } as never)
  vi.mocked(usePreviewPdfSpans).mockReturnValue({ ...quieto } as never)
  vi.mocked(useAnonymizeTestData).mockReturnValue({ ...quieto } as never)
  vi.mocked(useTestScriptProposal).mockReturnValue({ ...quieto } as never)
  vi.mocked(useValidateTestResult).mockReturnValue({ ...quieto } as never)
  vi.mocked(useSaveScriptToPrivateTemplate).mockReturnValue({
    ...quieto,
    mutate: guardar,
  } as never)
  vi.mocked(useSubmitScriptForReview).mockReturnValue({ ...quieto } as never)
})

describe('El asistente declara antes de compartir', () => {
  it('pide la finalidad y las categorías en el último paso', async () => {
    enElUltimoPaso()
    pintar()

    await waitFor(() => expect(screen.getByTestId('declaracion-finalidad')).toBeInTheDocument())
    expect(screen.getByTestId('declaracion-categorias')).toBeInTheDocument()
    // Y dice por qué se pide, no sólo qué: es el acto de compartir, no un campo más.
    const porque = screen.getByTestId('declaracion-porque')
    expect(porque).toBeInTheDocument()
    // **El texto, no sólo el nodo.** Una clave i18n que falte se pinta como
    // `declaracion.porque` y el test del nodo pasaría igual: es el riesgo que este bloque
    // tiene, porque la pantalla es nueva y sus claves también.
    expect(porque.textContent).toContain('lo comparte con tu servicio')
    expect(porque.textContent).not.toContain('declaracion.')
  })

  it('no deja guardar sin finalidad', async () => {
    enElUltimoPaso()
    pintar()
    fireEvent.click(await screen.findByTestId('btn-save'))

    expect(guardar).not.toHaveBeenCalled()
  })

  it('manda la declaración en el cuerpo, y el cuerpo completo', async () => {
    enElUltimoPaso()
    pintar()
    fireEvent.change(await screen.findByTestId('declaracion-finalidad'), {
      target: { value: 'Extraer la tabla de gastos del ERP' },
    })
    fireEvent.change(screen.getByTestId('declaracion-nombre'), {
      target: { value: 'Extraer gastos' },
    })
    fireEvent.click(screen.getByTestId('categoria-datos_economicos_y_financieros'))
    fireEvent.click(screen.getByTestId('btn-save'))

    // `toEqual` y no `objectContaining`: lo que este test existe para cazar es **lo que falta**.
    expect(guardar).toHaveBeenCalledWith(
      {
        proposalId: 'prop-1',
        data: {
          finalidad: 'Extraer la tabla de gastos del ERP',
          categorias_datos: ['datos_economicos_y_financieros'],
          nombre: 'Extraer gastos',
        },
      },
      {},
    )
  })

  it('ofrece las categorías que el servidor conoce, sin escribirlas a mano', async () => {
    /** El vocabulario es el de REG y es **abierto**: la pantalla ofrece las conocidas y deja
     *  añadir una que no esté, porque cerrar la lista en el cliente convertiría un vocabulario
     *  revisable en un `Enum` de React. */
    enElUltimoPaso()
    pintar()
    const opciones = await screen.findAllByTestId(/^categoria-/)

    expect(opciones.length).toBeGreaterThan(3)
    expect(screen.getByTestId('categoria-otra')).toBeInTheDocument()
  })

  it('tampoco deja enviar a revisión de plataforma sin declarar', async () => {
    /** El otro camino del mismo paso. `submit-for-review` acaba en `approve`, que también
     *  registra en el catálogo desde FUN.3: si uno pide declaración y el otro no, el hueco se
     *  muda de sitio en vez de cerrarse. */
    const enviar = vi.fn()
    vi.mocked(useSubmitScriptForReview).mockReturnValue({
      ...quieto,
      mutate: enviar,
    } as never)
    enElUltimoPaso()
    pintar()

    fireEvent.change(await screen.findByTestId('select-target-owner-kind'), {
      target: { value: 'platform' },
    })
    fireEvent.click(screen.getByTestId('btn-submit-for-review'))

    expect(enviar).not.toHaveBeenCalled()
  })
})
