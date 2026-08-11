import { useState } from 'react'
import { useQueryClient, type QueryKey } from '@tanstack/react-query'
import {
  useDeleteDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdDelete,
  useGetDocumentCopiesApiV1HubIngestionChatbotIdDocumentsDocumentIdCopiasGet,
} from '@/shared/api/generated/hub-ingestion/hub-ingestion'
import type { HubDocumentOut } from '@/shared/api/generated/model'

/**
 * Borrado de un documento del corpus, con el aviso de copias hermanas (DER.2).
 *
 * Vive fuera de `DocumentsPage` porque la página es un orquestador (CAL.3) y esto son tres
 * cosas acopladas entre sí —el documento elegido, dónde más vive y si se borra en cascada—
 * que no le interesan a nadie más de la pantalla.
 *
 * Las copias se consultan **al abrir el diálogo**, no al borrar: un aviso que llega después
 * de la decisión no es un aviso.
 */
export function useBorradoDeDocumento(chatbotId: string, documentsQueryKey: QueryKey) {
  const qc = useQueryClient()
  const [objetivo, setObjetivo] = useState<HubDocumentOut | null>(null)
  const [borrarEnTodos, setBorrarEnTodos] = useState(false)

  const { data: copias } =
    useGetDocumentCopiesApiV1HubIngestionChatbotIdDocumentsDocumentIdCopiasGet(
      chatbotId,
      objetivo?.id ?? '',
      { query: { enabled: !!objetivo && !!chatbotId } },
    )

  const mutacion = useDeleteDocumentApiV1HubIngestionChatbotIdDocumentsDocumentIdDelete({
    mutation: {
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: documentsQueryKey })
        setObjetivo(null)
        setBorrarEnTodos(false)
      },
    },
  })

  return {
    objetivo,
    elegir: setObjetivo,
    cancelar: () => setObjetivo(null),
    copiasEnOtrosChatbots: copias?.copias_en_otros_chatbots ?? 0,
    borrarEnTodos,
    setBorrarEnTodos,
    isPending: mutacion.isPending,
    confirmar: () => {
      if (!objetivo) return
      mutacion.mutate({
        chatbotId,
        documentId: objetivo.id,
        params: { en_todos_los_chatbots: borrarEnTodos },
      })
    },
  }
}
