import type { UIDropzoneDescriptor } from '@/shared/api/generated/model'
import { getLocalizedLabel } from './ReportUIContractRenderer'

interface Props {
  dropzones: UIDropzoneDescriptor[]
  locale: string
  onFileChange: (slotId: string, files: File[]) => void
  /** INF.1 — slots obligatorios que estaban vacíos al intentar enviar. */
  missingSlots?: string[]
  /** Texto del aviso, ya traducido: este componente no llama a i18n. */
  missingMessage?: string
  /** INF.1 — slots cuyo fichero ya está en el informe de una ejecución anterior. */
  satisfiedSlots?: string[]
  /** Texto que lo dice, ya traducido. */
  satisfiedMessage?: string
}

export function DynamicUploadSlots({
  dropzones,
  locale,
  onFileChange,
  missingSlots = [],
  missingMessage = '',
  satisfiedSlots = [],
  satisfiedMessage = '',
}: Props) {
  return (
    <div>
      {dropzones.map(dz => {
        const label = getLocalizedLabel(dz.label, locale)
        const inputId = `dropzone_${dz.slot_id}`
        const errorId = `${inputId}_error`
        const falta = missingSlots.includes(dz.slot_id)
        return (
          <div key={dz.slot_id}>
            <label htmlFor={inputId}>{label}</label>
            <input
              id={inputId}
              type="file"
              accept={(dz.accept ?? []).join(',')}
              multiple={dz.multiple ?? false}
              aria-required={dz.required ?? false}
              aria-invalid={falta}
              aria-describedby={falta ? errorId : undefined}
              onChange={e => onFileChange(dz.slot_id, Array.from(e.target.files ?? []))}
            />
            {/* El aviso nombra el fichero que falta y vive junto a su campo. «Falta algo» no
                sirve: el informe puede pedir varios ficheros. */}
            {falta && (
              <p id={errorId} role="alert">
                {label}: {missingMessage}
              </p>
            )}
            {/* Ya subido en una ejecución anterior: se dice, para que reejecutar no parezca
                que exige el fichero otra vez. */}
            {!falta && satisfiedSlots.includes(dz.slot_id) && (
              <p data-testid={`slot-satisfecho-${dz.slot_id}`}>{satisfiedMessage}</p>
            )}
          </div>
        )
      })}
    </div>
  )
}
