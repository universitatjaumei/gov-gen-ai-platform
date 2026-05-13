import type { UIDropzoneDescriptor } from '@/shared/api/generated/model'
import { getLocalizedLabel } from './ReportUIContractRenderer'

interface Props {
  dropzones: UIDropzoneDescriptor[]
  locale: string
  onFileChange: (slotId: string, files: File[]) => void
}

export function DynamicUploadSlots({ dropzones, locale, onFileChange }: Props) {
  return (
    <div>
      {dropzones.map(dz => {
        const label = getLocalizedLabel(dz.label, locale)
        const inputId = `dropzone_${dz.slot_id}`
        return (
          <div key={dz.slot_id}>
            <label htmlFor={inputId}>{label}</label>
            <input
              id={inputId}
              type="file"
              accept={(dz.accept ?? []).join(',')}
              multiple={dz.multiple ?? false}
              onChange={e => onFileChange(dz.slot_id, Array.from(e.target.files ?? []))}
            />
          </div>
        )
      })}
    </div>
  )
}
