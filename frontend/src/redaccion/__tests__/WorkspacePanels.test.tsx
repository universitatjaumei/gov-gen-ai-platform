/**
 * Tests 9R.7.2 (RED → GREEN)
 * BlockEditor + AIBlockReviewPanel + DataQualityPanel + WorkspaceStatusBar
 */
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'

import { AIBlockReviewPanel } from '../components/AIBlockReviewPanel'
import { DataQualityPanel } from '../components/DataQualityPanel'
import { WorkspaceStatusBar } from '../components/WorkspaceStatusBar'

// --------------------------------------------------------------------------
// Mock Orval hooks
// --------------------------------------------------------------------------

const mockPatchMutate = vi.fn()

vi.mock('@/shared/api/generated/hub-redaccion/hub-redaccion', () => ({
  useGetWorkspaceById: vi.fn(),
  usePatchWorkspaceBlock: vi.fn(),
  useGetWorkspaceWarnings: vi.fn(),
}))

import {
  useGetWorkspaceById,
  usePatchWorkspaceBlock,
  useGetWorkspaceWarnings,
} from '@/shared/api/generated/hub-redaccion/hub-redaccion'

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

function makeBlock(id: string, status: string, kind = 'AI_ASSISTED_TEXT') {
  return {
    block_id: id,
    kind,
    status,
    content: status === 'needs_review' ? { text: `Draft for ${id}` } : null,
    failure_kind: null,
    last_error_message: null,
    retry_attempts: 0,
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  vi.mocked(usePatchWorkspaceBlock).mockReturnValue({
    mutate: mockPatchMutate,
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof usePatchWorkspaceBlock>)
})

// --------------------------------------------------------------------------
// AIBlockReviewPanel
// --------------------------------------------------------------------------

describe('AIBlockReviewPanel', () => {
  it('should_show_ai_blocks_as_pending_review', () => {
    vi.mocked(useGetWorkspaceById).mockReturnValue({
      data: {
        id: 'ws-1',
        template_version_id: 'tv-1',
        status: 'in_review',
        blocks: [
          makeBlock('b_ai', 'needs_review'),
          makeBlock('b_data', 'extracted', 'DETERMINISTIC_DATA'),
        ],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useGetWorkspaceById>)

    wrap(<AIBlockReviewPanel workspaceId="ws-1" />)

    expect(screen.getByTestId('review-block-b_ai')).toBeDefined()
    // Only needs_review blocks shown
    expect(screen.queryByTestId('review-block-b_data')).toBeNull()
  })

  it('should_require_explicit_approval_before_final_assembly', () => {
    vi.mocked(useGetWorkspaceById).mockReturnValue({
      data: {
        id: 'ws-1',
        template_version_id: 'tv-1',
        status: 'in_review',
        blocks: [makeBlock('b_ai', 'needs_review')],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useGetWorkspaceById>)

    wrap(<AIBlockReviewPanel workspaceId="ws-1" />)

    // When blocks are pending review, "ready for assembly" must NOT be shown
    expect(screen.queryByTestId('ready-for-assembly')).toBeNull()
    // Pending indicator must be visible
    expect(screen.getByTestId('pending-review-count')).toBeDefined()
  })

  it('should_allow_regenerate_ai_block', () => {
    vi.mocked(useGetWorkspaceById).mockReturnValue({
      data: {
        id: 'ws-1',
        template_version_id: 'tv-1',
        status: 'in_review',
        blocks: [makeBlock('b_ai', 'needs_review')],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useGetWorkspaceById>)

    wrap(<AIBlockReviewPanel workspaceId="ws-1" />)

    fireEvent.click(screen.getByTestId('btn-regenerate-b_ai'))

    // SEG.4 — el segundo argumento son las opciones de la mutacion: desde ahora la accion
    // invalida la consulta del informe. Antes no lo hacia, asi que aprobar un apartado dejaba
    // el panel ensenandolo como pendiente hasta que alguien recargaba.
    expect(mockPatchMutate).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ action: 'regenerate' }) }),
      expect.anything(),
    )
  })
})

// --------------------------------------------------------------------------
// DataQualityPanel
// --------------------------------------------------------------------------

describe('DataQualityPanel', () => {
  it('should_show_extraction_warnings_with_severity', () => {
    vi.mocked(useGetWorkspaceWarnings).mockReturnValue({
      data: [
        { block_id: 'b1', message: 'Confianza baja', kind: 'low_confidence', severity: 'warning' },
        { block_id: 'b2', message: 'Tipo incorrecto', kind: 'type_mismatch', severity: 'error' },
      ],
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useGetWorkspaceWarnings>)

    wrap(<DataQualityPanel workspaceId="ws-1" />)

    expect(screen.getByText('Confianza baja')).toBeDefined()
    expect(screen.getByText('Tipo incorrecto')).toBeDefined()
    expect(screen.getByTestId('severity-warning')).toBeDefined()
    expect(screen.getByTestId('severity-error')).toBeDefined()
  })
})

// --------------------------------------------------------------------------
// WorkspaceStatusBar
// --------------------------------------------------------------------------

describe('WorkspaceStatusBar', () => {
  it('should_show_workspace_status_progress', () => {
    vi.mocked(useGetWorkspaceById).mockReturnValue({
      data: {
        id: 'ws-1',
        template_version_id: 'tv-1',
        status: 'drafting',
        blocks: [],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useGetWorkspaceById>)

    wrap(<WorkspaceStatusBar workspaceId="ws-1" />)

    expect(screen.getByTestId('workspace-status-badge')).toBeDefined()
    // After refactor, badge shows friendly label not raw status string
    expect(screen.getByTestId('workspace-status-badge').textContent).not.toEqual('drafting')
  })
})
