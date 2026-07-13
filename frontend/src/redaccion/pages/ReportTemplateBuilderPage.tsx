import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useListTemplates,
  useCreateTemplate,
} from '@/shared/api/generated/hub-redaccion/hub-redaccion'
import type { TemplateOut } from '@/shared/api/generated/model'
import { useAuth } from '@/shared/auth'

export function ReportTemplateBuilderPage() {
  const { t } = useTranslation('common')
  const { user } = useAuth()
  const [name, setName] = useState('')

  const { data: templatesRaw, isLoading } = useListTemplates()
  const templates = (templatesRaw as unknown as TemplateOut[] | undefined) ?? []
  const { mutate: createTemplate, isPending } = useCreateTemplate()

  if (!user || !['superadmin', 'admin'].includes(user.role)) {
    return <div data-testid="access-denied">Sin permisos</div>
  }

  if (isLoading) return <div>{t('loading')}</div>

  function handleSave() {
    createTemplate({
      data: { name, report_profile: 'GENERIC_REPORT', owner_kind: 'platform', spec_json: {} },
    })
  }

  return (
    <div className="space-y-4 p-4">
      <ul className="space-y-1">
        {templates.map(tmpl => (
          <li
            key={tmpl.id}
            data-testid={`template-item-${tmpl.id}`}
            className="text-sm px-3 py-2 border rounded"
          >
            {tmpl.name}
          </li>
        ))}
      </ul>

      <div className="space-y-2">
        <label htmlFor="template-name" className="text-sm font-medium">
          Nombre de plantilla
        </label>
        <input
          id="template-name"
          data-testid="input-template-name"
          value={name}
          onChange={e => setName(e.target.value)}
          className="w-full border rounded px-3 py-1.5 text-sm"
        />
        <button
          type="button"
          data-testid="btn-save-template"
          disabled={isPending || !name}
          onClick={handleSave}
          className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded disabled:opacity-50"
        >
          Guardar plantilla
        </button>
      </div>
    </div>
  )
}
