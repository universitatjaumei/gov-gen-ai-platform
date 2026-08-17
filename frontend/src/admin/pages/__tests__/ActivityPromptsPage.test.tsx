/**
 * PRO.2.1 — la pantalla de la biblioteca de prompts de actividad.
 *
 * Lo que se defiende aquí es la parte que se puede hacer mal sin que se note: que el texto
 * por defecto **no se copie** a la caja (copiarlo congela el prompt) y que el selector de
 * nivel **diga cuál es el defecto** en vez de dejar un hueco que nadie sabe interpretar.
 */
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'

import { ActivityPromptsPage } from '../ActivityPromptsPage'

const mockUpdate = vi.fn()
const mockReset = vi.fn()

vi.mock('@/shared/api/generated/hub-activity-prompts/hub-activity-prompts', () => ({
  useListActivityPrompts: vi.fn(),
  useUpdateActivityPrompt: vi.fn(),
  useResetActivityPrompt: vi.fn(),
  getListActivityPromptsQueryKey: () => ['activity-prompts'],
}))

import {
  useListActivityPrompts,
  useUpdateActivityPrompt,
  useResetActivityPrompt,
} from '@/shared/api/generated/hub-activity-prompts/hub-activity-prompts'

const PROPUESTA = {
  activity: 'propuesta_de_script',
  purpose: 'escribe el script de extracción',
  default_tier: 2,
  default_template: 'Eres un asistente experto… Sólo puedes importar de {lista_blanca}.',
  variables: ['lista_blanca', 'schema'],
  override_tier: null,
  template_text: null,
  effective_tier: 2,
  tier_source: 'codigo',
  text_source: 'codigo',
}

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <ActivityPromptsPage />
    </QueryClientProvider>,
  )
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useListActivityPrompts).mockReturnValue({
    data: [PROPUESTA] as unknown as ReturnType<typeof useListActivityPrompts>['data'],
    isPending: false,
  } as unknown as ReturnType<typeof useListActivityPrompts>)
  vi.mocked(useUpdateActivityPrompt).mockReturnValue({
    mutate: mockUpdate,
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useUpdateActivityPrompt>)
  vi.mocked(useResetActivityPrompt).mockReturnValue({
    mutate: mockReset,
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useResetActivityPrompt>)
})

describe('ActivityPromptsPage', () => {
  it('should_mostrar_el_nivel_efectivo_y_de_donde_sale', () => {
    wrap()

    const chip = screen.getByTestId('effective-tier-propuesta_de_script')
    expect(chip.textContent).toContain('2')
    expect(chip.textContent?.toLowerCase()).toContain('código')
  })

  it('should_decir_cual_es_el_nivel_por_defecto_en_la_primera_opcion', () => {
    wrap()

    const selector = screen.getByTestId('tier-select-propuesta_de_script') as HTMLSelectElement
    // Sin override el selector está en la opción «por defecto», y esa opción dice el número.
    expect(selector.value).toBe('')
    expect(selector.options[0].textContent).toContain('2')
  })

  it('should_no_copiar_el_texto_por_defecto_en_la_caja', () => {
    wrap()

    const caja = screen.getByTestId('text-propuesta_de_script') as HTMLTextAreaElement
    expect(caja.value).toBe('')
    expect(caja.placeholder).toContain('asistente experto')
  })

  it('should_guardar_el_nivel_sin_mandar_texto', () => {
    wrap()

    fireEvent.change(screen.getByTestId('tier-select-propuesta_de_script'), {
      target: { value: '3' },
    })
    fireEvent.click(screen.getByTestId('save-propuesta_de_script'))

    expect(mockUpdate).toHaveBeenCalledTimes(1)
    const enviado = mockUpdate.mock.calls[0][0]
    expect(enviado.activity).toBe('propuesta_de_script')
    expect(enviado.data.override_tier).toBe(3)
    expect(enviado.data.template_text).toBeNull()
  })

  it('should_mandar_null_al_volver_al_nivel_por_defecto', () => {
    vi.mocked(useListActivityPrompts).mockReturnValue({
      data: [
        { ...PROPUESTA, override_tier: 3, effective_tier: 3, tier_source: 'override' },
      ] as unknown as ReturnType<typeof useListActivityPrompts>['data'],
      isPending: false,
    } as unknown as ReturnType<typeof useListActivityPrompts>)

    wrap()
    fireEvent.change(screen.getByTestId('tier-select-propuesta_de_script'), {
      target: { value: '' },
    })
    fireEvent.click(screen.getByTestId('save-propuesta_de_script'))

    expect(mockUpdate.mock.calls[0][0].data.override_tier).toBeNull()
  })

  it('should_enseñar_las_variables_detectadas_en_lo_que_se_va_a_usar', () => {
    wrap()

    // Sin texto propio, las variables son las del texto por defecto.
    expect(screen.getByTestId('detected-vars').textContent).toContain('{lista_blanca}')

    fireEvent.change(screen.getByTestId('text-propuesta_de_script'), {
      target: { value: 'Nada de variables aquí.' },
    })
    expect(screen.getByTestId('detected-vars').textContent).not.toContain('{lista_blanca}')
  })

  it('should_restablecer_y_vaciar_el_formulario', () => {
    mockReset.mockImplementation((_vars, opciones) => opciones?.onSuccess?.())
    wrap()

    fireEvent.change(screen.getByTestId('text-propuesta_de_script'), {
      target: { value: 'mi texto' },
    })
    fireEvent.click(screen.getByTestId('reset-propuesta_de_script'))

    const caja = screen.getByTestId('text-propuesta_de_script') as HTMLTextAreaElement
    expect(caja.value).toBe('')
  })
})
