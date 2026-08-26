import { describe, test, expect, vi, beforeAll, afterEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import i18n from '@/shared/i18n'
import { ChatWidget } from '../components/ChatWidget'

// Helper: mock SSE Response with all events delivered at once
function makeSseResponse(events: Array<{ event: string; data: object }>): Response {
  const encoder = new TextEncoder()
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const { event, data } of events) {
        controller.enqueue(
          encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`),
        )
      }
      controller.close()
    },
  })
  return new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } })
}

// Helper: deferred SSE stream with externally controlled enqueue/close
function makeDeferredStream() {
  const encoder = new TextEncoder()
  let ctrl!: ReadableStreamDefaultController<Uint8Array>
  const stream = new ReadableStream<Uint8Array>({ start(c) { ctrl = c } })
  return {
    response: new Response(stream),
    send(event: string, data: object) {
      ctrl.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`))
    },
    close() { ctrl.close() },
  }
}

const DEFAULT_PROPS = {
  chatbotId: 'bot-1',
  apiUrl: 'http://localhost:8000/api/v1',
  lang: 'es',
}

const DONE_EVENT = {
  interaction_id: 'iact-1',
  sources: [],
  language_fallback: false,
  translation_warning: null,
}

const DONE_WITH_SOURCES = {
  interaction_id: 'iact-1',
  sources: [
    { document_id: 'doc-1', title: 'Reglament del Consell de Govern', url: 'https://www.uji.es/reglament.pdf', score: 0.92 },
    { document_id: 'doc-2', title: 'Estatuts UJI', url: 'https://dogv.gva.es/estatuts.pdf', score: 0.85 },
  ],
  language_fallback: false,
  translation_warning: null,
}

const fetchMock = vi.fn()

// El widget monta `EnlaceAlFuente` (AIS.6), que pide `/api/v1/instancia` al cargarse. Con un
// único mock compartido, esa petición se comía el `mockResolvedValueOnce` que cada test tenía
// preparado para la respuesta del chat, así que el chat recibía `undefined` y 18 tests caían
// con «Unable to find an element with the text».
//
// Se enruta por URL en vez de añadir un `Once` de más al principio de cada test: así el test
// declara sólo lo suyo, y montar mañana otro componente que pida algo al arrancar no vuelve a
// desplazar la cola. Lo destapó CI.
const fetchEnrutado = vi.fn((entrada: RequestInfo | URL, ...resto: unknown[]) => {
  const url = typeof entrada === 'string' ? entrada : String((entrada as Request).url ?? entrada)
  if (url.includes('/instancia')) {
    return Promise.resolve(new Response(JSON.stringify({ source_url: null })))
  }
  return fetchMock(entrada, ...resto)
})

beforeAll(async () => {
  await i18n.changeLanguage('es')
  vi.stubGlobal('fetch', fetchEnrutado)
})

afterEach(() => {
  vi.clearAllMocks()
})

// UX.1: el widget arranca CERRADO, que es la convención de un widget de chat. Los tests
// que ejercitan la conversación necesitan abrirlo antes, y lo hacen por el lanzador —no
// por un prop de conveniencia—, así que prueban también el camino que recorre el visitante.
function renderOpen(ui: React.ReactElement) {
  const resultado = render(ui)
  fireEvent.click(screen.getByTestId('widget-launcher'))
  return resultado
}

describe('ChatWidget — comportamiento de widget (UX.1)', () => {
  test('should_start_closed_showing_only_the_launcher', () => {
    render(<ChatWidget {...DEFAULT_PROPS} />)

    expect(screen.getByTestId('widget-launcher')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  test('should_open_when_the_launcher_is_clicked', () => {
    render(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.click(screen.getByTestId('widget-launcher'))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.queryByTestId('widget-launcher')).not.toBeInTheDocument()
  })

  test('should_bring_its_own_box_instead_of_inheriting_the_host_page', () => {
    // El defecto que lo motiva: el panel se renderizaba con `height: 100%` dentro del
    // contenedor y heredaba lo que le diera la página, así que en un `<div>` pelado se
    // estiraba a ancho completo al final del documento.
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    const caja = screen.getByRole('dialog')

    expect(caja).toHaveStyle({ position: 'fixed' })
    expect(caja.style.width).not.toBe('')
    expect(caja.style.borderTop).toContain('#0b5394')
  })

  test('should_use_a_growing_textarea_not_a_single_line_input', () => {
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    const campo = screen.getByRole('textbox')

    expect(campo.tagName).toBe('TEXTAREA')
    expect(campo).toHaveStyle({ resize: 'none' })
    expect(campo.style.overflowY).not.toBe('scroll')
  })

  test('should_grow_the_textarea_as_the_question_gets_longer', () => {
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)
    const campo = screen.getByRole('textbox') as HTMLTextAreaElement
    // jsdom no calcula `scrollHeight`, así que se simula: lo que se comprueba es que el
    // componente REACCIONA al contenido, no la altura exacta que pintaría un navegador.
    Object.defineProperty(campo, 'scrollHeight', { value: 92, configurable: true })

    fireEvent.change(campo, { target: { value: 'Una pregunta prou llarga '.repeat(6) } })

    expect(campo.style.height).toBe('92px')
  })

  test('should_scroll_to_the_answer_without_the_user_doing_it', async () => {
    const scrollIntoView = vi.fn()
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      value: scrollIntoView,
      writable: true,
      configurable: true,
    })
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Resposta llarga.' } },
        { event: 'done', data: DONE_EVENT },
      ]),
    )
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => expect(scrollIntoView).toHaveBeenCalled())
  })
})

describe('ChatWidget — señal inmediata y aviso de IA (UX.7)', () => {
  test('should_acknowledge_the_question_before_the_server_says_anything', async () => {
    // El primer `status` del servidor tarda unos segundos: hasta que llegaba, quien
    // preguntaba no tenía ninguna señal de que su pregunta se hubiera enviado.
    const deferred = makeDeferredStream()
    fetchMock.mockResolvedValueOnce(deferred.response)
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    // Sin ningún evento del servidor todavía.
    await waitFor(() => expect(screen.getByTestId('widget-pensando')).toBeInTheDocument())
  })

  test('should_replace_the_placeholder_with_the_real_progress', async () => {
    const deferred = makeDeferredStream()
    fetchMock.mockResolvedValueOnce(deferred.response)
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))
    await screen.findByTestId('widget-pensando')

    await act(async () => {
      deferred.send('status', { node: 'retrieve', msg: 'Buscando…' })
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.queryByTestId('widget-pensando')).not.toBeInTheDocument()
      expect(screen.getByText(/Buscando en la base documental/)).toBeInTheDocument()
    })
  })

  test('should_warn_that_the_answers_come_from_ai_and_may_be_wrong', () => {
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    const aviso = screen.getByTestId('widget-aviso-ia')

    expect(aviso.textContent).toMatch(/inteligencia artificial/i)
    expect(aviso.textContent).toMatch(/errores/i)
  })

  test('should_name_the_model_when_the_page_declares_it', () => {
    renderOpen(<ChatWidget {...DEFAULT_PROPS} model="Gemini 2.5 Flash" />)

    expect(screen.getByTestId('widget-aviso-ia').textContent).toContain('(Gemini 2.5 Flash)')
  })

  test('should_not_show_empty_parentheses_without_a_model', () => {
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    expect(screen.getByTestId('widget-aviso-ia').textContent).not.toContain('()')
  })
})

describe('ChatWidget — la cita dice qué artículo (UX.6)', () => {
  test('should_show_the_anchor_next_to_the_document_title', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Sis anys.' } },
        {
          event: 'done',
          data: {
            ...DONE_EVENT,
            sources: [{
              document_id: 'doc-1',
              title: 'Reglament de la Sindicatura de Greuges',
              url: 'https://www.uji.es/reglament.pdf#art-9',
              score: 0.9,
            }],
          },
        },
      ]),
    )
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    // El ancla viajaba en el enlace pero no se veía: la píldora solo pintaba el título.
    await waitFor(() => expect(screen.getByText(/art-9/)).toBeInTheDocument())
  })

  test('should_not_invent_an_anchor_when_the_source_has_none', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Resposta.' } },
        { event: 'done', data: DONE_WITH_SOURCES },
      ]),
    )
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await screen.findByText('Estatuts UJI')
    expect(screen.queryByText(/·/)).not.toBeInTheDocument()
  })
})

describe('ChatWidget — el progreso habla el idioma de la página (UX.3)', () => {
  test('should_translate_the_node_status_instead_of_showing_the_server_text', async () => {
    await i18n.changeLanguage('ca')
    const deferred = makeDeferredStream()
    fetchMock.mockResolvedValueOnce(deferred.response)
    renderOpen(<ChatWidget {...DEFAULT_PROPS} lang="ca" />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await act(async () => {
      // El servidor manda el texto en castellano; el widget no lo debe pintar.
      deferred.send('status', { node: 'retrieve', msg: 'Buscando en la base de conocimiento...' })
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.getByText(/Cercant en la base documental/)).toBeInTheDocument()
      expect(screen.queryByText(/Buscando en la base de conocimiento/)).not.toBeInTheDocument()
    })
    await i18n.changeLanguage('es')
  })

  test('should_fall_back_to_the_server_text_for_an_untranslated_node', async () => {
    const deferred = makeDeferredStream()
    fetchMock.mockResolvedValueOnce(deferred.response)
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await act(async () => {
      deferred.send('status', { node: 'un_nodo_futuro', msg: 'Haciendo algo nuevo...' })
      await Promise.resolve()
    })

    // Un nodo sin traducción enseña lo que diga el servidor: mejor eso que un hueco.
    await waitFor(() =>
      expect(screen.getByText('Haciendo algo nuevo...')).toBeInTheDocument(),
    )
  })
})

describe('ChatWidget — pregunta y respuesta se distinguen (UX.2)', () => {
  test('should_frame_the_user_question_in_light_blue', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Resposta.' } },
        { event: 'done', data: DONE_EVENT },
      ]),
    )
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    const turno = await screen.findByTestId('turn-user')
    // jsdom normaliza el hexadecimal a rgb(): #e8f0f8 -> rgb(232, 240, 248).
    expect(turno).toHaveStyle({ background: 'rgb(232, 240, 248)' })
  })

  test('should_separate_a_question_from_the_previous_answer', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Resposta.' } },
        { event: 'done', data: DONE_EVENT },
      ]),
    )
    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    const turno = await screen.findByTestId('turn-user')
    expect(turno.style.marginTop).not.toBe('')
    const respuesta = await screen.findByTestId('turn-assistant')
    expect(respuesta.style.marginTop).not.toBe('')
  })
})

describe('ChatWidget', () => {
  test('should_display_user_and_assistant_messages', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Hola, soy el asistente.' } },
        { event: 'done', data: DONE_EVENT },
      ]),
    )

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hola' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByText('Hola')).toBeInTheDocument()
      expect(screen.getByText('Hola, soy el asistente.')).toBeInTheDocument()
    })
  })

  test('should_stream_chunks_in_real_time', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Chunk1' } },
        { event: 'token', data: { delta: 'Chunk2' } },
        { event: 'done', data: DONE_EVENT },
      ]),
    )

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hola' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByText('Chunk1Chunk2')).toBeInTheDocument()
    })
  })

  test('should_show_node_status_during_stream', async () => {
    const deferred = makeDeferredStream()
    fetchMock.mockResolvedValueOnce(deferred.response)

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hola' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await act(async () => {
      deferred.send('status', { node: 'retriever', msg: 'Buscando en la base de conocimiento...' })
    })

    await waitFor(() => {
      expect(screen.getByText('Buscando en la base de conocimiento...')).toBeInTheDocument()
    })

    await act(async () => {
      deferred.send('done', DONE_EVENT)
      deferred.close()
    })
  })

  test('should_hide_status_when_streaming_ends', async () => {
    const deferred = makeDeferredStream()
    fetchMock.mockResolvedValueOnce(deferred.response)

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hola' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await act(async () => {
      deferred.send('status', { node: 'retriever', msg: 'Buscando...' })
    })

    await waitFor(() => {
      expect(screen.getByText('Buscando...')).toBeInTheDocument()
    })

    await act(async () => {
      deferred.send('token', { delta: 'Respuesta' })
      deferred.send('done', DONE_EVENT)
      deferred.close()
    })

    await waitFor(() => {
      expect(screen.queryByText('Buscando...')).not.toBeInTheDocument()
    })
  })

  test('should_show_translation_warning_on_language_fallback', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Resposta' } },
        {
          event: 'done',
          data: {
            interaction_id: 'iact-1',
            sources: [],
            language_fallback: true,
            translation_warning: 'Resposta en idioma alternatiu',
          },
        },
      ]),
    )

    renderOpen(<ChatWidget {...DEFAULT_PROPS} lang="ca" />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hola' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText('Resposta en idioma alternatiu')).toBeInTheDocument()
    })
  })

  test('should_show_star_rating_after_response', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Aquí está la respuesta.' } },
        { event: 'done', data: DONE_EVENT },
      ]),
    )

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByRole('group')).toBeInTheDocument()
    })
  })

  test('should_submit_feedback_on_star_click', async () => {
    fetchMock
      .mockResolvedValueOnce(
        makeSseResponse([
          { event: 'token', data: { delta: 'Respuesta.' } },
          { event: 'done', data: { ...DONE_EVENT, interaction_id: 'iact-99' } },
        ]),
      )
      .mockResolvedValueOnce(new Response('{}', { status: 200 }))

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByRole('group')).toBeInTheDocument()
    })

    const starButtons = screen.getAllByRole('button', { name: /estrellas/i })
    await act(async () => {
      fireEvent.click(starButtons[2]) // 3 estrellas
    })

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/hub/feedback/iact-99',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ score: 3 }),
      }),
    )
  })

  test('should_render_source_pills_after_last_assistant_message', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Aquí tienes la respuesta.' } },
        { event: 'done', data: DONE_WITH_SOURCES },
      ]),
    )

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /Reglament del Consell de Govern/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /Estatuts UJI/i })).toBeInTheDocument()
    })
  })

  test('should_open_source_pill_in_new_tab', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Respuesta.' } },
        { event: 'done', data: DONE_WITH_SOURCES },
      ]),
    )

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      const link = screen.getByRole('link', { name: /Reglament del Consell de Govern/i })
      expect(link).toHaveAttribute('href', 'https://www.uji.es/reglament.pdf')
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'))
    })
  })

  test('should_render_no_pills_when_sources_empty', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Respuesta sin fuentes.' } },
        { event: 'done', data: DONE_EVENT },
      ]),
    )

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByText('Respuesta sin fuentes.')).toBeInTheDocument()
    })

    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  test('should_have_sources_section_label_for_screen_readers', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Respuesta.' } },
        { event: 'done', data: DONE_WITH_SOURCES },
      ]),
    )

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByRole('navigation', { name: /fuentes/i })).toBeInTheDocument()
    })
  })

  test('should_render_assistant_message_as_markdown', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: '**Texto en negrita**' } },
        { event: 'done', data: DONE_EVENT },
      ]),
    )

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Pregunta' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByRole('strong')).toBeInTheDocument()
    })
  })

  test('should_show_loading_indicator_during_stream', async () => {
    let resolveFetch!: (r: Response) => void
    fetchMock.mockReturnValueOnce(new Promise<Response>(r => { resolveFetch = r }))

    renderOpen(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hola' } })

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /enviar/i }))
    })

    // isStreaming=true before fetch resolves → loading indicator visible
    expect(screen.getByRole('status')).toBeInTheDocument()

    await act(async () => {
      resolveFetch(
        makeSseResponse([
          { event: 'token', data: { delta: 'Resp' } },
          { event: 'done', data: DONE_EVENT },
        ]),
      )
    })

    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })
  })
})
