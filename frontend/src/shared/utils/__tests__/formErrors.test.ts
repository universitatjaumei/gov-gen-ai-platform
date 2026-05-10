import { describe, it, expect, vi } from 'vitest'
import type { UseFormSetError, FieldValues } from 'react-hook-form'
import { mapApiErrorsToFormErrors } from '../formErrors'

function makeSetError() {
  return vi.fn() as unknown as UseFormSetError<FieldValues>
}

describe('mapApiErrorsToFormErrors', () => {
  it('maps a direct FastAPI 422 detail to the correct form field', () => {
    const setError = makeSetError()
    mapApiErrorsToFormErrors(
      { detail: [{ loc: ['body', 'name'], msg: 'Name already in use', type: 'value_error' }] },
      setError
    )
    expect(setError).toHaveBeenCalledWith('name', { type: 'server', message: 'Name already in use' })
  })

  it('maps an axios-wrapped 422 response to the correct form field', () => {
    const setError = makeSetError()
    mapApiErrorsToFormErrors(
      {
        response: {
          data: {
            detail: [{ loc: ['body', 'name'], msg: 'Name already in use', type: 'value_error' }],
          },
        },
      },
      setError
    )
    expect(setError).toHaveBeenCalledWith('name', { type: 'server', message: 'Name already in use' })
  })

  it('does not call setError when the error has no validation detail', () => {
    const setError = makeSetError()
    mapApiErrorsToFormErrors(new Error('Network error'), setError)
    expect(setError).not.toHaveBeenCalled()
  })

  it('maps a nested loc path to dot-notation field name', () => {
    const setError = makeSetError()
    mapApiErrorsToFormErrors(
      { detail: [{ loc: ['body', 'config', 'model'], msg: 'Invalid model', type: 'value_error' }] },
      setError
    )
    expect(setError).toHaveBeenCalledWith('config.model', { type: 'server', message: 'Invalid model' })
  })

  it('maps multiple field errors in a single response', () => {
    const setError = makeSetError()
    mapApiErrorsToFormErrors(
      {
        detail: [
          { loc: ['body', 'name'], msg: 'Required', type: 'missing' },
          { loc: ['body', 'system_prompt'], msg: 'Too short', type: 'value_error' },
        ],
      },
      setError
    )
    expect(setError).toHaveBeenCalledTimes(2)
    expect(setError).toHaveBeenCalledWith('name', { type: 'server', message: 'Required' })
    expect(setError).toHaveBeenCalledWith('system_prompt', { type: 'server', message: 'Too short' })
  })
})
