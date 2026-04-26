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

const fetchMock = vi.fn()

beforeAll(async () => {
  await i18n.changeLanguage('es')
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('ChatWidget', () => {
  test('should_display_user_and_assistant_messages', async () => {
    fetchMock.mockResolvedValueOnce(
      makeSseResponse([
        { event: 'token', data: { delta: 'Hola, soy el asistente.' } },
        { event: 'done', data: DONE_EVENT },
      ]),
    )

    render(<ChatWidget {...DEFAULT_PROPS} />)

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

    render(<ChatWidget {...DEFAULT_PROPS} />)

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hola' } })
    fireEvent.click(screen.getByRole('button', { name: /enviar/i }))

    await waitFor(() => {
      expect(screen.getByText('Chunk1Chunk2')).toBeInTheDocument()
    })
  })

  test('should_show_node_status_during_stream', async () => {
    const deferred = makeDeferredStream()
    fetchMock.mockResolvedValueOnce(deferred.response)

    render(<ChatWidget {...DEFAULT_PROPS} />)

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

    render(<ChatWidget {...DEFAULT_PROPS} />)

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

    render(<ChatWidget {...DEFAULT_PROPS} lang="ca" />)

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

    render(<ChatWidget {...DEFAULT_PROPS} />)

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

    render(<ChatWidget {...DEFAULT_PROPS} />)

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

  test('should_show_loading_indicator_during_stream', async () => {
    let resolveFetch!: (r: Response) => void
    fetchMock.mockReturnValueOnce(new Promise<Response>(r => { resolveFetch = r }))

    render(<ChatWidget {...DEFAULT_PROPS} />)

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
