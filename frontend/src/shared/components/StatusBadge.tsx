import type { StatusTone } from '@/redaccion/utils/statusLabels'

const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: 'bg-gray-100 text-gray-600',
  info: 'bg-blue-100 text-blue-700',
  warning: 'bg-yellow-100 text-yellow-700',
  success: 'bg-green-100 text-green-700',
  error: 'bg-destructive/10 text-destructive',
}

interface StatusBadgeProps {
  label: string
  tone: StatusTone
  'data-testid'?: string
}

export function StatusBadge({ label, tone, 'data-testid': testId }: StatusBadgeProps) {
  return (
    <span
      data-testid={testId}
      className={`text-xs px-2 py-0.5 rounded-full ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  )
}
