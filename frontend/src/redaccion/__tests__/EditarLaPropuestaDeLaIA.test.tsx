import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { AIBlockReviewPanel } from '../components/AIBlockReviewPanel'
import {
  useGetWorkspaceById,
  usePatchWorkspaceBlock,
} from '@/shared/api/generated/hub-redaccion/hub-redaccion'
import { useEditBlock } from '@/shared/api/generated/redaccion-workspaces/redaccion-workspaces'

/**
 * SEG.4 — el técnico puede editar lo que propuso la IA, no sólo aprobarlo o rechazarlo.
 *
 * El backend ya sabía hacerlo: `editBlock` sobreescribe el contenido y guarda el original en un
 * evento de auditoría con su actor. Lo que faltaba era la pantalla — el hook generado existía y
 * **no lo llamaba nadie**, así que la única supervisión posible era aprobar o rechazar en bloque,
 * y el usuario lo señaló como limitación antes de probar el módulo.
 */
vi.mock('@/shared/api/generated/hub-redaccion/hub-redaccion', () => ({
  useGetWorkspaceById: vi.fn(),
  usePatchWorkspaceBlock: vi.fn(),
}))

vi.mock('@/shared/api/generated/redaccion-workspaces/redaccion-workspaces', () => ({
  useEditBlock: vi.fn(),
}))

const WS = '11111111-1111-1111-1111-111111111111'

const BLOQUE_DE_IA = {
  block_id: 'v_matricula',
  kind: 'AI_ASSISTED_TEXT',
  status: 'needs_review',
  content: {
    text: 'La matrícula desciende un 6 % respecto al curso anterior.',
    model_used: 'gemini-2.5-flash',
    prompt_version: 'valoracion_de_tendencia_v1',
    context_scope: 'anchored',
    context_block_ids: ['t_matricula'],
  },
  retry_attempts: 0,
  updated_at: '2026-08-18T10:00:00Z',
}

function mockearApi(overrides: Record<string, unknown> = {}) {
  vi.mocked(useGetWorkspaceById).mockReturnValue({
    data: { id: WS, status: 'in_review', blocks: [BLOQUE_DE_IA], ...(overrides.workspace as object) },
    isLoading: false,
  } as never)
  vi.mocked(usePatchWorkspaceBlock).mockReturnValue({
    mutate: overrides.patch ?? vi.fn(),
    isPending: false,
  } as never)
  vi.mocked(useEditBlock).mockReturnValue({
    mutate: overrides.edit ?? vi.fn(),
    isPending: false,
  } as never)
}

function pintar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <AIBlockReviewPanel workspaceId={WS} />
    </QueryClientProvider>,
  )
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.clearAllMocks()
})

describe('editar la propuesta de la IA', () => {
  it('should_ofrecer_editar_ademas_de_aprobar_y_rechazar', () => {
    mockearApi()
    pintar()

    expect(screen.getByTestId('btn-editar-v_matricula')).toBeInTheDocument()
    expect(screen.getByTestId('btn-approve-v_matricula')).toBeInTheDocument()
  })

  it('should_abrir_el_texto_completo_para_editarlo', () => {
    /** El panel lo mostraba recortado a tres líneas: no se puede revisar lo que no se ve. */
    mockearApi()
    pintar()

    fireEvent.click(screen.getByTestId('btn-editar-v_matricula'))

    const area = screen.getByTestId('editor-v_matricula') as HTMLTextAreaElement
    expect(area.value).toBe('La matrícula desciende un 6 % respecto al curso anterior.')
  })

  it('should_guardar_el_texto_editado', async () => {
    const edit = vi.fn()
    mockearApi({ edit })
    pintar()

    fireEvent.click(screen.getByTestId('btn-editar-v_matricula'))
    fireEvent.change(screen.getByTestId('editor-v_matricula'), {
      target: { value: 'La matrícula desciende, en línea con la oferta.' },
    })
    fireEvent.click(screen.getByTestId('btn-guardar-v_matricula'))

    await waitFor(() =>
      expect(edit).toHaveBeenCalledWith(
        expect.objectContaining({
          workspaceId: WS,
          blockId: 'v_matricula',
          data: expect.objectContaining({
            content: expect.objectContaining({
              text: 'La matrícula desciende, en línea con la oferta.',
            }),
          }),
        }),
        expect.anything(),
      ),
    )
  })

  it('should_no_guardar_un_texto_vacio', () => {
    /** Un apartado en blanco aprobado es peor que uno mal redactado: pasa desapercibido. */
    mockearApi()
    pintar()

    fireEvent.click(screen.getByTestId('btn-editar-v_matricula'))
    fireEvent.change(screen.getByTestId('editor-v_matricula'), { target: { value: '   ' } })

    expect(screen.getByTestId('btn-guardar-v_matricula')).toBeDisabled()
  })

  it('should_poder_cancelar_sin_guardar', () => {
    const edit = vi.fn()
    mockearApi({ edit })
    pintar()

    fireEvent.click(screen.getByTestId('btn-editar-v_matricula'))
    fireEvent.change(screen.getByTestId('editor-v_matricula'), { target: { value: 'otro' } })
    fireEvent.click(screen.getByTestId('btn-cancelar-v_matricula'))

    expect(edit).not.toHaveBeenCalled()
    expect(screen.queryByTestId('editor-v_matricula')).not.toBeInTheDocument()
  })

  it('should_ensenar_lo_que_propuso_la_ia_despues_de_editar', () => {
    /** Si el original no está a la vista, la edición es irreversible en la práctica. */
    mockearApi({
      workspace: {
        blocks: [{
          ...BLOQUE_DE_IA,
          content: {
            ...BLOQUE_DE_IA.content,
            text: 'Texto del técnico.',
            original_ai_text: 'La matrícula desciende un 6 % respecto al curso anterior.',
            edited_by: 'tecnico@uji.es',
            edited_at: '2026-08-18T11:00:00Z',
          },
        }],
      },
    })
    pintar()

    const original = screen.getByTestId('original-ia-v_matricula')
    expect(original.textContent).toContain('desciende un 6 %')
  })

  it('should_decir_quien_edito', () => {
    mockearApi({
      workspace: {
        blocks: [{
          ...BLOQUE_DE_IA,
          content: {
            ...BLOQUE_DE_IA.content,
            text: 'Texto del técnico.',
            edited_by: 'tecnico@uji.es',
            edited_at: '2026-08-18T11:00:00Z',
          },
        }],
      },
    })
    pintar()

    expect(screen.getByTestId('editado-por-v_matricula').textContent).toContain('tecnico@uji.es')
  })

  it('should_decir_en_que_tabla_se_apoya_la_valoracion', () => {
    /** Es lo que SEG.1 dejó en el bloque: sin verlo, quien revisa no sabe qué debería decir. */
    mockearApi()
    pintar()

    expect(screen.getByTestId('fuente-v_matricula').textContent).toContain('t_matricula')
  })

  it('should_avisar_cuando_la_valoracion_no_esta_anclada', () => {
    /** Un apartado que leyó todo el informe es el caso que produce resúmenes que omiten. */
    mockearApi({
      workspace: {
        blocks: [{
          ...BLOQUE_DE_IA,
          content: { ...BLOQUE_DE_IA.content, context_scope: 'full', context_block_ids: [] },
        }],
      },
    })
    pintar()

    expect(screen.getByTestId('fuente-v_matricula').textContent).toMatch(/todo el informe/i)
  })

  it('should_estar_traducido_y_no_con_texto_incrustado', async () => {
    /** El panel tenía los rótulos escritos en castellano dentro del componente. */
    mockearApi()
    await i18n.changeLanguage('en')
    pintar()

    expect(screen.getByTestId('btn-editar-v_matricula').textContent).not.toMatch(/editar/i)
    await i18n.changeLanguage('es')
  })
})
