import type { FieldValues, UseFormSetError, FieldPath } from 'react-hook-form'

interface FastAPIValidationErrorItem {
  loc: (string | number)[]
  msg: string
  type: string
}

export function mapApiErrorsToFormErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>
): void {
  const detail = extractDetail(error)
  if (!detail) return
  for (const item of detail) {
    const field = item.loc.slice(1).join('.') as FieldPath<T>
    if (field) setError(field, { type: 'server', message: item.msg })
  }
}

function extractDetail(e: unknown): FastAPIValidationErrorItem[] | null {
  if (!e || typeof e !== 'object') return null
  // Direct FastAPI error: { detail: [...] }
  const direct = e as Record<string, unknown>
  if ('detail' in direct && Array.isArray(direct.detail)) {
    return direct.detail as FastAPIValidationErrorItem[]
  }
  // Axios-wrapped: { response: { data: { detail: [...] } } }
  const data = (e as { response?: { data?: unknown } })?.response?.data
  if (data && typeof data === 'object') {
    const wrapped = data as Record<string, unknown>
    if ('detail' in wrapped && Array.isArray(wrapped.detail)) {
      return wrapped.detail as FastAPIValidationErrorItem[]
    }
  }
  return null
}
