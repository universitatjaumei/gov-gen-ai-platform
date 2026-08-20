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
 * INF.2 — el panel pinta lo que el servidor permite, no lo que él deduce del estado.
 *
 * Filtraba por `status === 'needs_review'`, así que un bloque de IA en `failed` **no se pintaba**
 * y el panel anunciaba «Todos los apartados aprobados». Al mismo tiempo la vista previa y la
 * exportación devolvían 409 por esos mismos bloques. El usuario se quedó sin nada que pulsar:
 * es el bloqueo B de las pruebas humanas del 2026-08-20.
 *
 * Y los cuatro botones estaban escritos a mano, así que se pintaba «Regenerar» sobre bloques
 * `needs_review` —transición que la máquina de estados no permite—.
 */
vi.mock('@/shared/api/generated/hub-redaccion/hub-redaccion', () => ({
  useGetWorkspaceById: vi.fn(),
  usePatchWorkspaceBlock: vi.fn(),
  getGetWorkspaceByIdQueryKey: vi.fn(() => ['workspace']),
}))

vi.mock('@/shared/api/generated/redaccion-workspaces/redaccion-workspaces', () => ({
  useEditBlock: vi.fn(),
}))

const WS = '11111111-1111-1111-1111-111111111111'

/** Lo que el servidor devuelve hoy para el caso del usuario: la IA falló y se puede regenerar. */
const BLOQUE_FALLIDO = {
  block_id: 'v_matricula',
  kind: 'AI_ASSISTED_TEXT',
  status: 'failed',
  failure_kind: 'ai_failed',
  content: {},
  retry_attempts: 1,
  updated_at: '2026-08-20T10:00:00Z',
  acciones_permitidas: ['edit', 'reject', 'regenerate'],
}

const BLOQUE_EN_REVISION = {
  block_id: 'v_tesis',
  kind: 'AI_ASSISTED_TEXT',
  status: 'needs_review',
  content: { text: 'Las tesis leídas suben un 17 %.' },
  retry_attempts: 0,
  updated_at: '2026-08-20T10:00:00Z',
  acciones_permitidas: ['approve', 'edit', 'reject'],
}

const patch = vi.fn()

function pintar(bloques: object[]) {
  vi.mocked(useGetWorkspaceById).mockReturnValue({
    data: { id: WS, status: 'in_review', blocks: bloques },
    isLoading: false,
  } as never)
  vi.mocked(usePatchWorkspaceBlock).mockReturnValue({ mutate: patch, isPending: false } as never)
  vi.mocked(useEditBlock).mockReturnValue({ mutate: vi.fn(), isPending: false } as never)

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

describe('INF.2 — el panel itera las acciones del servidor', () => {
  it('should_show_a_failed_block_instead_of_claiming_everything_is_approved', async () => {
    pintar([BLOQUE_FALLIDO])

    expect(await screen.findByTestId('review-block-v_matricula')).toBeDefined()
    expect(screen.queryByTestId('ready-for-assembly')).toBeNull()
  })

  it('should_offer_regenerate_on_a_failed_block', async () => {
    pintar([BLOQUE_FALLIDO])

    fireEvent.click(await screen.findByTestId('btn-regenerate-v_matricula'))

    await waitFor(() =>
      expect(patch).toHaveBeenCalledWith(
        expect.objectContaining({ blockId: 'v_matricula', data: { action: 'regenerate' } }),
        expect.anything(),
      ),
    )
  })

  it('should_not_offer_approve_on_a_failed_block', async () => {
    pintar([BLOQUE_FALLIDO])

    await screen.findByTestId('review-block-v_matricula')
    expect(screen.queryByTestId('btn-approve-v_matricula')).toBeNull()
  })

  it('should_not_offer_regenerate_on_a_block_awaiting_review', async () => {
    pintar([BLOQUE_EN_REVISION])

    await screen.findByTestId('review-block-v_tesis')
    // La transicion `needs_review → ai_generated` no existe: ofrecerla es pintar un boton roto.
    expect(screen.queryByTestId('btn-regenerate-v_tesis')).toBeNull()
    expect(screen.queryByTestId('btn-approve-v_tesis')).toBeDefined()
  })

  it('should_say_everything_is_approved_only_when_no_block_has_actions', async () => {
    pintar([
      {
        ...BLOQUE_EN_REVISION,
        status: 'approved',
        acciones_permitidas: [],
      },
    ])

    expect(await screen.findByTestId('ready-for-assembly')).toBeDefined()
  })

  it('should_not_decide_from_the_status_string', async () => {
    // Guardarraíl: un estado que el frontend no conoce, con acciones. Si el componente
    // volviera a comparar `status` con literales, este bloque desaparecería de la pantalla.
    pintar([
      {
        ...BLOQUE_FALLIDO,
        status: 'un_estado_que_el_frontend_no_conoce',
        acciones_permitidas: ['edit'],
      },
    ])

    expect(await screen.findByTestId('review-block-v_matricula')).toBeDefined()
    expect(screen.queryByTestId('btn-editar-v_matricula')).toBeDefined()
  })
})
