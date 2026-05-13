import type { FieldErrors, FieldValues, UseFormRegister } from 'react-hook-form'
import type { UIFieldDescriptor } from '@/shared/api/generated/model'
import { getLocalizedLabel } from './ReportUIContractRenderer'

interface Props {
  fields: UIFieldDescriptor[]
  locale: string
  register: UseFormRegister<FieldValues>
  errors: FieldErrors
}

export function DynamicFieldRenderer({ fields, locale, register, errors }: Props) {
  return (
    <div>
      {fields.map(f => {
        const label = getLocalizedLabel(f.label, locale)
        const placeholder = getLocalizedLabel(f.placeholder ?? {}, locale)
        const error = errors[f.slot_id]
        const inputId = `field_${f.slot_id}`
        return (
          <div key={f.slot_id}>
            <label htmlFor={inputId}>{label}</label>
            <input
              id={inputId}
              type={f.field_type === 'number' ? 'number' : 'text'}
              placeholder={placeholder}
              aria-required={f.required ?? false}
              {...register(f.slot_id)}
            />
            {error && (
              <span role="alert" className="text-destructive text-xs">
                {String(error.message)}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}
