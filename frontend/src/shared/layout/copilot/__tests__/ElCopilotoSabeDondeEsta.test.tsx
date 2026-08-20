import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import i18n from '@/shared/i18n'
import { CopilotPanel } from '../CopilotPanel'
import { useFocusStore } from '../../useFocusStore'
import { askCopilotApiV1RedaccionCopilotAskPost } from '@/shared/api/generated/redaccion-copilot/redaccion-copilot'

/**
 * INF.10 — el copiloto manda el informe abierto.
 *
 * Sabía en qué **tipo** de contexto estaba («informe» o «flujo») y no **cuál**, así que
 * respondía solo con la documentación del proyecto. En las pruebas del 2026-08-20 el usuario le
 * preguntó «no sé dónde aprobar los bloques» y no obtuvo respuesta.
 */
vi.mock('@/shared/api/generated/redaccion-copilot/redaccion-copilot', () => ({
  askCopilotApiV1RedaccionCopilotAskPost: vi.fn(),
  translateCopilotApiV1RedaccionCopilotTranslatePost: vi.fn(),
}))

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(askCopilotApiV1RedaccionCopilotAskPost).mockResolvedValue({
    answer: 'Apruébalo en el panel de revisión.',
    source_refs: [],
  } as never)
})

async function preguntar(pregunta: string) {
  render(<CopilotPanel />)
  const entrada = screen.getByRole('textbox')
  fireEvent.change(entrada, { target: { value: pregunta } })
  const botones = screen.getAllByRole('button')
  const enviar = botones.find((b) => /enviar|preguntar|send/i.test(b.textContent ?? '')) ?? botones[botones.length - 1]
  fireEvent.click(enviar)
}

describe('INF.10 — el copiloto sabe en qué informe está', () => {
  it('should_send_the_open_report_with_the_question', async () => {
    useFocusStore.setState({ context: { type: 'informe', entityId: 'ws-42' } })

    await preguntar('¿Dónde apruebo los bloques?')

    await waitFor(() =>
      expect(askCopilotApiV1RedaccionCopilotAskPost).toHaveBeenCalledWith(
        expect.objectContaining({ workspace_id: 'ws-42' }),
      ),
    )
  })

  it('should_send_nothing_when_there_is_no_report_open', async () => {
    useFocusStore.setState({ context: { type: 'flujo', entityId: 'flow-1' } })

    await preguntar('¿Qué es un flujo?')

    await waitFor(() =>
      expect(askCopilotApiV1RedaccionCopilotAskPost).toHaveBeenCalledWith(
        expect.objectContaining({ workspace_id: null }),
      ),
    )
  })
})
