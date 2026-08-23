/**
 * REV.13 — la pantalla enseña **todos** los prompts, no sólo los de plataforma.
 *
 * Quien la revisó preguntó por qué hay prompts del sistema en Chatbots y prompts de actividad
 * en Plataforma, y en Plataforma sólo se ven los del módulo de Informes. La respuesta es que
 * son dos modelos distintos —una plantilla cuelga de un chatbot y va por idioma; una actividad
 * es única global—, así que unificar las tablas sería meter dos cosas en una. Lo que sí faltaba
 * era **verlas juntas**.
 *
 * El test que importa es el último: que desde aquí se pueda **editar** una plantilla de
 * chatbot. Sin él, la pantalla unificada sería un listado bonito que no deja tocar la mitad de
 * lo que enseña, y quien la abriera seguiría teniendo que ir a la otra.
 */
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'

import { ActivityPromptsPage } from '../ActivityPromptsPage'

vi.mock('@/shared/api/generated/hub-activity-prompts/hub-activity-prompts', () => ({
  useListActivityPrompts: vi.fn(),
  useUpdateActivityPrompt: vi.fn(),
  useResetActivityPrompt: vi.fn(),
  getListActivityPromptsQueryKey: () => ['activity-prompts'],
}))
vi.mock('@/shared/api/generated/hub-prompts-catalog/hub-prompts-catalog', () => ({
  useListPromptsCatalog: vi.fn(),
  getListPromptsCatalogQueryKey: () => ['prompts-catalog'],
}))
vi.mock('@/shared/api/generated/hub-prompt-templates/hub-prompt-templates', () => ({
  useUpdatePromptTemplateApiV1HubPromptTemplatesTemplateIdPatch: vi.fn(),
}))
vi.mock('@/shared/api/generated/hub-chatbots/hub-chatbots', () => ({
  useUpdateChatbotApiV1HubChatbotsChatbotIdPatch: vi.fn(),
}))

import {
  useListActivityPrompts,
  useUpdateActivityPrompt,
  useResetActivityPrompt,
} from '@/shared/api/generated/hub-activity-prompts/hub-activity-prompts'
import { useListPromptsCatalog } from '@/shared/api/generated/hub-prompts-catalog/hub-prompts-catalog'
import { useUpdatePromptTemplateApiV1HubPromptTemplatesTemplateIdPatch } from '@/shared/api/generated/hub-prompt-templates/hub-prompt-templates'
import { useUpdateChatbotApiV1HubChatbotsChatbotIdPatch } from '@/shared/api/generated/hub-chatbots/hub-chatbots'

const mockGuardarPlantilla = vi.fn()
const mockGuardarBase = vi.fn()

const PROPUESTA = {
  activity: 'propuesta_de_script',
  purpose: 'escribe el script de extracción',
  default_tier: 2,
  default_template: 'Eres un asistente experto…',
  variables: ['schema'],
  override_tier: null,
  template_text: null,
  effective_tier: 2,
  tier_source: 'codigo',
  text_source: 'codigo',
  modulo: 'informes',
}

const DEL_CATALOGO = [
  {
    ambito: 'chatbot_base',
    clave: 'prompt_base',
    chatbot_id: 'bot-1',
    chatbot_nombre: 'Asistente Normativa',
    template_text: 'Eres el asistente de normativa.',
  },
  {
    ambito: 'plataforma',
    clave: 'propuesta_de_script',
    descripcion: 'escribe el script de extracción',
    modulo: 'informes',
  },
  {
    ambito: 'chatbot',
    clave: 'system_base',
    chatbot_id: 'bot-1',
    chatbot_nombre: 'Asistente Normativa',
    language: 'es',
    template_id: 'tpl-1',
    template_text: 'Eres un asistente institucional.',
    version: 3,
  },
]

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
    data: [PROPUESTA],
    isPending: false,
  } as unknown as ReturnType<typeof useListActivityPrompts>)
  vi.mocked(useUpdateActivityPrompt).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useUpdateActivityPrompt>)
  vi.mocked(useResetActivityPrompt).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useResetActivityPrompt>)
  vi.mocked(useListPromptsCatalog).mockReturnValue({
    data: DEL_CATALOGO,
    isPending: false,
  } as unknown as ReturnType<typeof useListPromptsCatalog>)
  vi.mocked(
    useUpdatePromptTemplateApiV1HubPromptTemplatesTemplateIdPatch,
  ).mockReturnValue({
    mutate: mockGuardarPlantilla,
    isPending: false,
    isError: false,
  } as unknown as ReturnType<
    typeof useUpdatePromptTemplateApiV1HubPromptTemplatesTemplateIdPatch
  >)
  vi.mocked(useUpdateChatbotApiV1HubChatbotsChatbotIdPatch).mockReturnValue({
    mutate: mockGuardarBase,
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useUpdateChatbotApiV1HubChatbotsChatbotIdPatch>)
})

describe('La pantalla de prompts enseña los dos ámbitos', () => {
  it('should_mostrar_tambien_las_plantillas_de_chatbot', () => {
    wrap()

    expect(screen.getByTestId('plantilla-tpl-1')).toBeInTheDocument()
    expect(screen.getByTestId('grupo-chatbot-bot-1')).toHaveTextContent(
      'Asistente Normativa',
    )
  })

  it('should_decir_de_que_asistente_y_en_que_idioma_es_cada_plantilla', () => {
    wrap()

    const tarjeta = screen.getByTestId('plantilla-tpl-1')
    expect(tarjeta).toHaveTextContent('system_base')
    expect(tarjeta).toHaveTextContent('es')
  })

  it('should_dejar_ver_solo_un_ambito_cuando_se_filtra', () => {
    wrap()

    fireEvent.change(screen.getByLabelText('Ámbito'), { target: { value: 'plataforma' } })

    expect(screen.queryByTestId('plantilla-tpl-1')).not.toBeInTheDocument()
    expect(screen.getByTestId('activity-propuesta_de_script')).toBeInTheDocument()
  })

  it('should_mostrar_el_prompt_base_del_asistente', () => {
    // Es el que de verdad se ve hoy en Chatbots: las plantillas por actividad están vacías en
    // la mayoría de despliegues, así que dejarlo fuera sería enseñar lo que casi nadie tiene.
    wrap()

    expect(screen.getByTestId('plantilla-base-bot-1')).toHaveTextContent(
      'Prompt base del asistente',
    )
  })

  it('should_guardar_el_prompt_base_por_su_propio_camino', () => {
    // El prompt base es una columna de `hub_chatbots`, no una plantilla: mandarlo al router de
    // plantillas daría un 404 con un identificador que no existe.
    wrap()

    fireEvent.change(screen.getByTestId('texto-base-bot-1'), {
      target: { value: 'Eres el asistente de normativa de la UJI.' },
    })
    fireEvent.click(screen.getByTestId('guardar-base-bot-1'))

    expect(mockGuardarBase).toHaveBeenCalledWith(
      {
        chatbotId: 'bot-1',
        data: { system_prompt: 'Eres el asistente de normativa de la UJI.' },
      },
      expect.anything(),
    )
    expect(mockGuardarPlantilla).not.toHaveBeenCalled()
  })

  it('should_editar_una_plantilla_de_chatbot_desde_aqui', () => {
    // **El test que importa.** El catálogo es de sólo lectura a propósito, así que la edición
    // tiene que salir de aquí hacia el router de las plantillas, con su `template_id`.
    wrap()

    fireEvent.change(screen.getByTestId('texto-tpl-1'), {
      target: { value: 'Eres un asistente de la Universitat.' },
    })
    fireEvent.click(screen.getByTestId('guardar-tpl-1'))

    expect(mockGuardarPlantilla).toHaveBeenCalledWith(
      {
        templateId: 'tpl-1',
        data: { template_text: 'Eres un asistente de la Universitat.' },
      },
      expect.anything(),
    )
  })
})
