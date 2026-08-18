import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { useFocusStore } from '../../useFocusStore'
import { CopilotPanel } from '../CopilotPanel'
import { translateCopilotApiV1RedaccionCopilotTranslatePost } from '@/shared/api/generated/redaccion-copilot/redaccion-copilot'

// Desde CAL.2 el panel llama al cliente generado por Orval, que va sobre axios: un
// stub global de `fetch` ya no intercepta la petición.
vi.mock('@/shared/api/generated/redaccion-copilot/redaccion-copilot', () => ({
  askCopilotApiV1RedaccionCopilotAskPost: vi.fn(),
  translateCopilotApiV1RedaccionCopilotTranslatePost: vi.fn(),
}))

describe('CopilotPanel', () => {
  beforeEach(() => {
    act(() => useFocusStore.getState().reset())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('should_render_pills_contextual_to_active_module', () => {
    act(() => useFocusStore.getState().setContext({ type: 'informe', entityId: 'ws-1' }))
    const { rerender } = render(<CopilotPanel />)

    const informePills = screen.getAllByTestId('copilot-pill')
    expect(informePills.length).toBeGreaterThanOrEqual(3)
    // pills propias de 'informe' (rechazo de bloque, agrupar/sumar, gráfico de barras…)
    expect(screen.getByText(/rechazo/i)).toBeInTheDocument()
    expect(screen.getByText(/agrupa por mes/i)).toBeInTheDocument()
    // pills exclusivas de 'flujo' no aparecen
    expect(screen.queryByText(/trigger/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/slack/i)).not.toBeInTheDocument()

    // Cambiamos al contexto 'flujo'
    act(() => useFocusStore.getState().setContext({ type: 'flujo', entityId: 'flow-1' }))
    rerender(<CopilotPanel />)

    const flujoPills = screen.getAllByTestId('copilot-pill')
    expect(flujoPills.length).toBeGreaterThanOrEqual(3)
    expect(screen.getByText(/trigger/i)).toBeInTheDocument()
    expect(screen.getByText(/slack/i)).toBeInTheDocument()
    expect(screen.queryByText(/agrupa por mes/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/rechazo/i)).not.toBeInTheDocument()
  })

  /**
   * GUI.5 — este test exigia que 'Aplicar' escribiera la propuesta en 'pendingAction' del
   * store, y lo hacia. Lo que nadie comprobo es que **nadie lo lee**: 'useCopilotAction', el
   * unico consumidor, no lo usa ninguna pantalla. Un boton verde que no hace nada es peor que
   * no tener boton, porque quien lo pulsa cree que ya esta hecho.
   *
   * La propuesta ahora se copia, que es algo que de verdad ocurre.
   */
  it('should_copiar_la_propuesta_en_vez_de_prometer_aplicarla', async () => {
    vi.mocked(translateCopilotApiV1RedaccionCopilotTranslatePost).mockResolvedValue({
      kind: 'chart_config',
      payload: { chart_type: 'bar', x_column: 'mes', y_column: 'importe' },
    } as any)
    const escribir = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText: escribir } })

    act(() => useFocusStore.getState().setContext({ type: 'informe', entityId: 'ws-1' }))
    render(<CopilotPanel />)

    fireEvent.click(screen.getByTestId('copilot-mode-chart'))
    fireEvent.change(screen.getByTestId('copilot-input'), {
      target: { value: 'Grafico de barras por mes' },
    })
    fireEvent.click(screen.getByTestId('copilot-send'))

    expect(screen.queryByTestId('copilot-apply')).not.toBeInTheDocument()
    const copiar = await screen.findByTestId('copilot-copy')
    await act(async () => {
      fireEvent.click(copiar)
    })

    expect(escribir).toHaveBeenCalledWith(expect.stringContaining('chart_type'))
  })
})
