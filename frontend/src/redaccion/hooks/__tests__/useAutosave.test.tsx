import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAutosave } from '../useAutosave'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('useAutosave', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should_debounce_autosave_calls_to_at_most_one_per_1500ms', async () => {
    const patchMock = vi.fn().mockResolvedValue({ workspace_version: 2 })
    const wrapper = makeWrapper()
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock),
      { wrapper },
    )

    act(() => {
      result.current.markDirty()
    })
    act(() => {
      result.current.markDirty()
    })
    act(() => {
      result.current.markDirty()
    })

    // No invocation before 1500ms
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1499)
    })
    expect(patchMock).not.toHaveBeenCalled()

    // Exactly one call after debounce window elapses
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2)
    })
    expect(patchMock).toHaveBeenCalledTimes(1)
  })

  it('should_open_conflict_modal_on_409_response', async () => {
    const patchMock = vi.fn().mockRejectedValue({
      status: 409,
      body: { current_workspace_version: 5, conflicting_block_ids: ['b1'] },
    })
    const onConflict = vi.fn()
    const wrapper = makeWrapper()
    const { result } = renderHook(
      () =>
        useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock, {
          onConflict,
        }),
      { wrapper },
    )

    act(() => {
      result.current.markDirty()
    })
    await act(async () => {
      vi.advanceTimersByTime(1600)
      await vi.runAllTimersAsync()
    })

    expect(onConflict).toHaveBeenCalledWith({
      current_workspace_version: 5,
      conflicting_block_ids: ['b1'],
    })
    expect(result.current.status).toBe('conflict')
  })

  it('should_retry_save_with_backoff_on_network_error', async () => {
    const patchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error('network'))
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValue({ workspace_version: 2 })

    const wrapper = makeWrapper()
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock),
      { wrapper },
    )

    act(() => {
      result.current.markDirty()
    })
    await act(async () => {
      vi.advanceTimersByTime(1600)
      await vi.runAllTimersAsync()
    })

    expect(patchMock).toHaveBeenCalledTimes(3)
    expect(result.current.status).toBe('saved')
  })

  it('should_mark_workspace_offline_after_3_failed_retries', async () => {
    const patchMock = vi.fn().mockRejectedValue(new Error('network'))
    const wrapper = makeWrapper()
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock),
      { wrapper },
    )

    act(() => {
      result.current.markDirty()
    })
    await act(async () => {
      vi.advanceTimersByTime(1600)
      await vi.runAllTimersAsync()
    })

    expect(patchMock).toHaveBeenCalledTimes(3)
    expect(result.current.status).toBe('offline')
  })

  it('should_update_local_version_after_successful_save', async () => {
    const patchMock = vi.fn().mockResolvedValue({ workspace_version: 42 })
    const wrapper = makeWrapper()
    const { result } = renderHook(
      () => useAutosave('ws-1', () => ({ blockUpdates: [], version: 1 }), patchMock),
      { wrapper },
    )

    // Versión inicial leída de getState
    expect(result.current.workspaceVersion).toBe(1)

    act(() => {
      result.current.markDirty()
    })
    await act(async () => {
      vi.advanceTimersByTime(1600)
      await vi.runAllTimersAsync()
    })

    expect(result.current.workspaceVersion).toBe(42)
    expect(result.current.status).toBe('saved')
    expect(result.current.lastSavedAt).not.toBeNull()
  })
})
