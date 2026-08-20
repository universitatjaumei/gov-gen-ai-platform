import { describe, it, expect } from 'vitest'
import {
  aplicarArreglo,
  arregloMecanico,
  bloqueDelError,
  claveDelMensaje,
} from '../erroresDeLaPropuesta'

/**
 * INF.6 — una propuesta inválida se arregla sin empezar de cero.
 *
 * Con la propuesta rechazada, «Aprobar y crear» queda deshabilitado y la única salida era
 * volver a escribir el prompt entero. El usuario se quedó ahí, el 2026-08-20, con dos líneas
 * rojas que decían `blocks[b6].data_block_refs` y ningún sitio donde tocar.
 *
 * INF.5 hace que el error ocurra mucho menos. Esto hace que, cuando ocurra, se pueda arreglar.
 */

/** La propuesta que produjo el modelo en las pruebas, con el anclaje mal. */
function propuestaDelUsuario() {
  return {
    proposed_profile: 'GENERIC_REPORT',
    proposed_sections: [{ id: 's1', title: 'Tesoreria', order: 1, block_ids: ['b3', 'b4', 'b5', 'b6'] }],
    proposed_blocks: [
      { kind: 'DETERMINISTIC_DATA', id: 'b3', title: 'Saldos', order: 1, source_pipeline: 'csv' },
      { kind: 'TABLE', id: 'b4', title: 'Saldos por mes', order: 2, data_block_ref: 'b3' },
      { kind: 'CHART', id: 'b5', title: 'Evolucion', order: 3, data_block_ref: 'b3' },
      {
        kind: 'AI_SUMMARY',
        id: 'b6',
        title: 'Valoracion',
        order: 4,
        ai_prompt_template_id: 'generic_report_v1',
        review_policy_id: 'required',
        data_block_refs: ['b4', 'b5'],
      },
    ],
    proposed_inputs: { required_slots: [], optional_slots: [] },
    model_used: 'gemini',
    prompt_version: 'llm_spec_v2',
  }
}

describe('INF.6 — de qué bloque habla el error', () => {
  it('should_find_the_block_in_the_field_path', () => {
    expect(bloqueDelError('blocks[b6].data_block_refs')).toBe('b6')
    expect(bloqueDelError('blocks[t_matricula].config.source_block_ref')).toBe('t_matricula')
  })

  it('should_return_null_when_the_error_is_not_about_a_block', () => {
    expect(bloqueDelError('sections')).toBeNull()
    expect(bloqueDelError('proposed_inputs.required_slots')).toBeNull()
  })
})

describe('INF.6 — el arreglo mecánico', () => {
  const ERROR_DEL_USUARIO = {
    field: 'blocks[b6].data_block_refs',
    message: "AI_SUMMARY block 'b6' valora 'b4', que no produce datos ('TABLE')",
  }

  it('should_point_the_passage_at_the_data_the_table_draws', () => {
    // El arreglo no se adivina: `b4` es un TABLE cuyo `data_block_ref` es `b3`, así que la
    // valoración tiene que apuntar a `b3`. Está en la propia propuesta.
    const arreglo = arregloMecanico(propuestaDelUsuario(), ERROR_DEL_USUARIO)

    expect(arreglo).toEqual({
      blockId: 'b6',
      campo: 'data_block_refs',
      de: 'b4',
      a: 'b3',
    })
  })

  it('should_apply_the_fix_to_the_draft_without_touching_anything_else', () => {
    const propuesta = propuestaDelUsuario()
    const arregada = aplicarArreglo(propuesta, arregloMecanico(propuesta, ERROR_DEL_USUARIO)!)

    const valoracion = arregada.proposed_blocks.find((b) => b.id === 'b6')!
    expect(valoracion.data_block_refs).toEqual(['b3', 'b5'])
    // Los demás bloques, intactos.
    expect(arregada.proposed_blocks.find((b) => b.id === 'b4')!.data_block_ref).toBe('b3')
    expect(propuesta.proposed_blocks.find((b) => b.id === 'b6')!.data_block_refs).toEqual(['b4', 'b5'])
  })

  it('should_deduplicate_when_both_refs_lead_to_the_same_data', () => {
    // `b4` y `b5` dibujan los dos `b3`: arreglar los dos errores no puede dejar `['b3','b3']`.
    const propuesta = propuestaDelUsuario()
    let actual = propuesta
    for (const campo of ['b4', 'b5']) {
      const error = {
        field: 'blocks[b6].data_block_refs',
        message: `AI_SUMMARY block 'b6' valora '${campo}', que no produce datos`,
      }
      actual = aplicarArreglo(actual, arregloMecanico(actual, error)!)
    }
    expect(actual.proposed_blocks.find((b) => b.id === 'b6')!.data_block_refs).toEqual(['b3'])
  })

  it('should_offer_nothing_when_the_fix_is_not_mechanical', () => {
    // Una referencia a un bloque que no existe no se puede arreglar solo: hay que decidir.
    const arreglo = arregloMecanico(propuestaDelUsuario(), {
      field: 'blocks[b6].data_block_refs',
      message: "AI_SUMMARY block 'b6' valora un bloque inexistente 'b99'",
    })
    expect(arreglo).toBeNull()
  })
})

describe('INF.6 — el error en lenguaje de quien pide un informe', () => {
  it('should_translate_the_anchoring_error', () => {
    expect(
      claveDelMensaje({
        field: 'blocks[b6].data_block_refs',
        message: "AI_SUMMARY block 'b6' valora 'b4', que no produce datos ('TABLE')",
      }),
    ).toBe('draft_error.anchored_to_presentation')
  })

  it('should_fall_back_to_the_server_message_when_it_does_not_know_the_case', () => {
    expect(claveDelMensaje({ field: 'sections', message: 'algo raro' })).toBeNull()
  })
})
