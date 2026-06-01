import { useState } from 'react'
import { useTranslation } from 'react-i18next'

interface ColumnConfig {
  name: string
  fakerProvider: string
}

interface TestDataAnonymizerFormProps {
  columns: string[]
  onChange: (config: ColumnConfig[]) => void
}

const FAKER_PROVIDERS = [
  'name', 'email', 'phone_number', 'address', 'company',
  'ssn', 'date_of_birth', 'credit_card_number', 'none',
]

export function TestDataAnonymizerForm({ columns, onChange }: TestDataAnonymizerFormProps) {
  const { t } = useTranslation('scripts')
  const [config, setConfig] = useState<Record<string, string>>(
    Object.fromEntries(columns.map(c => [c, 'none'])),
  )

  function handleChange(col: string, provider: string) {
    const updated = { ...config, [col]: provider }
    setConfig(updated)
    onChange(columns.map(name => ({ name, fakerProvider: updated[name] ?? 'none' })))
  }

  if (columns.length === 0) {
    return <p className="text-sm text-muted-foreground">{t('anonymize.no_columns')}</p>
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">{t('anonymize.title')}</h3>
      <table className="w-full text-sm border rounded">
        <thead>
          <tr className="bg-muted text-left">
            <th className="px-3 py-2">{t('anonymize.column')}</th>
            <th className="px-3 py-2">{t('anonymize.faker_provider')}</th>
          </tr>
        </thead>
        <tbody>
          {columns.map(col => (
            <tr key={col} className="border-t">
              <td className="px-3 py-2 font-mono text-xs">{col}</td>
              <td className="px-3 py-2">
                <select
                  value={config[col] ?? 'none'}
                  onChange={e => handleChange(col, e.target.value)}
                  className="text-xs border rounded px-2 py-1 w-full"
                >
                  {FAKER_PROVIDERS.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
