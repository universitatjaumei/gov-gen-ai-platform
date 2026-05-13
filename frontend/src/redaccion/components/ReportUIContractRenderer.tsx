import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslation } from 'react-i18next'
import type { ReportUIContract, UIFieldDescriptor } from '@/shared/api/generated/model'
import { DynamicUploadSlots } from './DynamicUploadSlots'
import { DynamicFieldRenderer } from './DynamicFieldRenderer'

export function getLocalizedLabel(
  dict: Record<string, string>,
  locale: string,
): string {
  return dict[locale] ?? dict['es'] ?? dict['en'] ?? Object.values(dict)[0] ?? ''
}

function buildZodSchema(fields: UIFieldDescriptor[]) {
  const shape: Record<string, z.ZodTypeAny> = {}
  for (const f of fields) {
    shape[f.slot_id] = f.required
      ? z.string().min(1, { message: 'required' })
      : z.string().optional()
  }
  return z.object(shape)
}

export type ContractFormData = {
  fields: Record<string, string>
  files: Record<string, File[]>
}

interface Props {
  contract: ReportUIContract
  onSubmit: (data: ContractFormData) => void
}

export function ReportUIContractRenderer({ contract, onSubmit }: Props) {
  const { i18n, t } = useTranslation('common')
  const [files, setFiles] = useState<Record<string, File[]>>({})

  const schema = buildZodSchema(contract.manual_fields)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema) })

  function handleFileChange(slotId: string, newFiles: File[]) {
    setFiles(prev => ({ ...prev, [slotId]: newFiles }))
  }

  function onValid(values: Record<string, unknown>) {
    onSubmit({ fields: values as Record<string, string>, files })
  }

  return (
    <form onSubmit={handleSubmit(onValid)} noValidate>
      <DynamicUploadSlots
        dropzones={contract.dropzones}
        locale={i18n.language}
        onFileChange={handleFileChange}
      />
      <DynamicFieldRenderer
        fields={contract.manual_fields}
        locale={i18n.language}
        register={register}
        errors={errors}
      />
      <button type="submit">{t('continue')}</button>
    </form>
  )
}
