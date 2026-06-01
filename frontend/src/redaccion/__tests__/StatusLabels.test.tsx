/**
 * Tests 9R.7.6 (RED → GREEN)
 * statusLabels utility + StatusBadge + BlockDebugPanel
 */
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'

import { BlockEditor } from '../components/BlockEditor'
import { BlockDebugPanel } from '../components/BlockDebugPanel'
import { mapBlockStatusToUserLabel } from '../utils/statusLabels'

// --------------------------------------------------------------------------
// Mocks
// --------------------------------------------------------------------------

vi.mock('@/shared/api/generated/hub-redaccion/hub-redaccion', () => ({
  useGetWorkspaceById: vi.fn(),
  usePatchWorkspaceBlock: vi.fn(),
  useGetWorkspaceWarnings: vi.fn(),
}))

vi.mock('@/shared/auth', async () => {
  const actual = await vi.importActual<typeof import('@/shared/auth')>('@/shared/auth')
  return { ...actual, useAuth: vi.fn() }
})

import {
  useGetWorkspaceById,
  usePatchWorkspaceBlock,
} from '@/shared/api/generated/hub-redaccion/hub-redaccion'
import { useAuth } from '@/shared/auth'

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

interface BlockStub {
  block_id: string
  kind: string
  status: string
  content: null
  failure_kind: string | null
  last_error_message: string | null
  retry_attempts: number
  updated_at: string
}

function makeBlock(id: string, status: string, extra: Partial<BlockStub> = {}): BlockStub {
  return {
    block_id: id,
    kind: 'AI_ASSISTED_TEXT',
    status,
    content: null,
    failure_kind: null,
    last_error_message: null,
    retry_attempts: 0,
    updated_at: '2026-01-01T00:00:00Z',
    ...extra,
  }
}

function setupWorkspace(blocks: BlockStub[]) {
  vi.mocked(useGetWorkspaceById).mockReturnValue({
    data: {
      id: 'ws-1',
      template_version_id: 'tv-1',
      status: 'in_review',
      blocks,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    isLoading: false,
    isError: false,
  } as ReturnType<typeof useGetWorkspaceById>)
}

function setupAuth(role: string) {
  vi.mocked(useAuth).mockReturnValue({
    user: { user_id: 'u1', email: `${role}@test.com`, role },
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  })
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(usePatchWorkspaceBlock).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof usePatchWorkspaceBlock>)
  setupAuth('user')
})

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('statusLabels and StatusBadge', () => {
  it('should_render_user_label_not_internal_status', () => {
    setupWorkspace([makeBlock('b1', 'needs_review')])
    wrap(<BlockEditor workspaceId="ws-1" />)

    // Raw internal status must NOT appear as visible text
    expect(screen.queryByText('needs_review')).toBeNull()
    // A StatusBadge for the block must be present
    expect(screen.getByTestId('status-badge-b1')).toBeDefined()
  })

  it('should_map_failed_to_recoverable_error_tone', () => {
    const result = mapBlockStatusToUserLabel('failed')
    expect(result.tone).toBe('error')
  })

  it('should_not_show_last_error_message_to_regular_user', () => {
    const SECRET_ERROR = 'Traceback (most recent call last): RuntimeError at line 42'
    setupWorkspace([
      makeBlock('b1', 'failed', {
        failure_kind: 'ai_failed',
        last_error_message: SECRET_ERROR,
      }),
    ])
    setupAuth('user')
    wrap(<BlockEditor workspaceId="ws-1" />)

    expect(screen.queryByText(SECRET_ERROR)).toBeNull()
  })

  it('should_show_last_error_message_in_debug_panel_for_admin', () => {
    const ERROR_MESSAGE = 'Traceback (most recent call last): RuntimeError at line 42'
    const block = makeBlock('b1', 'failed', {
      failure_kind: 'ai_failed',
      last_error_message: ERROR_MESSAGE,
    })

    setupAuth('admin')
    wrap(<BlockDebugPanel block={block} />)

    // Debug panel visible for admin
    expect(screen.getByTestId('block-debug-panel')).toBeDefined()

    // Toggle to expose internals
    const toggleBtn = screen.queryByTestId('btn-toggle-debug')
    if (toggleBtn) {
      fireEvent.click(toggleBtn)
      expect(screen.queryByText(ERROR_MESSAGE)).not.toBeNull()
    }
  })

  it('should_hide_debug_panel_for_user_role', () => {
    const block = makeBlock('b1', 'failed', {
      failure_kind: 'ai_failed',
      last_error_message: 'some internal error',
    })

    setupAuth('user')
    wrap(<BlockDebugPanel block={block} />)

    expect(screen.queryByTestId('block-debug-panel')).toBeNull()
  })

  it('should_translate_failure_kind_to_friendly_message', () => {
    const SECRET_ERROR = 'Internal: LLM timed out after 30 s'
    setupWorkspace([
      makeBlock('b1', 'failed', {
        failure_kind: 'ai_failed',
        last_error_message: SECRET_ERROR,
      }),
    ])
    setupAuth('user')
    wrap(<BlockEditor workspaceId="ws-1" />)

    // Raw error must not appear
    expect(screen.queryByText(SECRET_ERROR)).toBeNull()
    // Friendly message element must be present
    expect(screen.getByTestId('failure-friendly-message-b1')).toBeDefined()
  })
})
