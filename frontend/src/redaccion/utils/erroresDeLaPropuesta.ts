/**
 * Los errores del validador, puestos donde se pueden arreglar (INF.6).
 *
 * Con la propuesta rechazada, «Aprobar y crear» queda deshabilitado y la única salida era
 * volver a escribir el prompt entero. En las pruebas del 2026-08-20 el usuario se quedó ahí:
 * dos líneas rojas que decían `blocks[b6].data_block_refs` y ningún sitio donde tocar.
 *
 * Aquí vive la parte que se puede razonar sin pintar nada: de qué bloque habla cada error, si
 * el arreglo se puede deducir de la propia propuesta, y cómo se cuenta en lenguaje de quien
 * pide un informe. Es lógica pura a propósito: así se prueba sin montar la pantalla.
 */
import type { DraftValidationError } from '@/shared/api/generated/model'

/** Un bloque de la propuesta. La forma la fija el contrato; aquí solo hace falta esto. */
interface BloquePropuesto {
  id: string
  kind: string
  data_block_ref?: string | null
  data_block_refs?: string[] | null
  [clave: string]: unknown
}

interface PropuestaConBloques {
  proposed_blocks: BloquePropuesto[]
  [clave: string]: unknown
}

export interface ArregloMecanico {
  blockId: string
  campo: 'data_block_refs'
  de: string
  a: string
}

/** Los bloques que solo **dibujan** datos: su `data_block_ref` dice de dónde salen. */
const PRESENTACIONES = new Set(['TABLE', 'CHART'])

/** `blocks[b6].data_block_refs` → `b6`. */
export function bloqueDelError(field: string): string | null {
  const coincidencia = /^blocks\[([^\]]+)\]/.exec(field)
  return coincidencia ? coincidencia[1] : null
}

/**
 * El arreglo, cuando se puede deducir de la propuesta y no hay nada que decidir.
 *
 * El caso que se repite: una valoración anclada al `TABLE` en vez de al bloque de datos que el
 * `TABLE` dibuja. El destino correcto **no se adivina**, está en el `data_block_ref` de ese
 * mismo `TABLE`. Si la referencia apunta a un bloque que no existe, no hay arreglo mecánico:
 * eso hay que decidirlo.
 */
export function arregloMecanico(
  propuesta: PropuestaConBloques,
  error: DraftValidationError,
): ArregloMecanico | null {
  const blockId = bloqueDelError(error.field)
  if (!blockId || !error.field.endsWith('data_block_refs')) return null

  const culpable = _referenciaCitada(error.message)
  if (!culpable) return null

  const apuntado = propuesta.proposed_blocks.find((b) => b.id === culpable)
  if (!apuntado || !PRESENTACIONES.has(apuntado.kind)) return null

  const datos = apuntado.data_block_ref
  if (!datos) return null

  return { blockId, campo: 'data_block_refs', de: culpable, a: datos }
}

/** Aplica el arreglo sobre una copia: la propuesta original no se toca. */
export function aplicarArreglo<T extends PropuestaConBloques>(
  propuesta: T,
  arreglo: ArregloMecanico,
): T {
  return {
    ...propuesta,
    proposed_blocks: propuesta.proposed_blocks.map((bloque) => {
      if (bloque.id !== arreglo.blockId) return bloque
      const referencias = (bloque.data_block_refs ?? []).map((r) =>
        r === arreglo.de ? arreglo.a : r,
      )
      // Sin deduplicar, arreglar dos referencias que dibujan la misma tabla dejaría el mismo
      // bloque de datos repetido, y la valoración recibiría el contexto dos veces.
      return { ...bloque, data_block_refs: [...new Set(referencias)] }
    }),
  }
}

/**
 * La clave de traducción para los errores que sabemos contar bien.
 *
 * `null` cuando no se reconoce el caso: entonces se enseña el mensaje del servidor tal cual,
 * que es peor que una frase escrita para una persona pero mucho mejor que esconderlo.
 */
export function claveDelMensaje(error: DraftValidationError): string | null {
  if (error.field.endsWith('data_block_refs') && /no produce datos/.test(error.message)) {
    return 'draft_error.anchored_to_presentation'
  }
  if (error.field.endsWith('data_block_refs') && /inexistente/.test(error.message)) {
    return 'draft_error.unknown_reference'
  }
  if (error.field.endsWith('data_block_ref') && /must reference a block that produces data/.test(error.message)) {
    return 'draft_error.presentation_without_data'
  }
  return null
}

/** El id que el mensaje del validador cita entre comillas simples, si cita alguno útil. */
function _referenciaCitada(mensaje: string): string | null {
  // «... valora 'b4', que no produce datos ('TABLE')» → b4. El primer entrecomillado es el id
  // del bloque que se queja; el segundo, el que está mal referenciado.
  const citas = [...mensaje.matchAll(/'([^']+)'/g)].map((m) => m[1])
  return citas.length >= 2 ? citas[1] : null
}
