import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PreviewRenderer } from '../PreviewRenderer'
import { samplePreviewPayload } from '@/test-utils/fixtures'

describe('PreviewRenderer', () => {
  it('should_render_cover_index_body_and_audit_annex_in_order', () => {
    const { container } = render(<PreviewRenderer payload={samplePreviewPayload()} />)
    const sections = container.querySelectorAll('[data-preview-section]')
    const kinds = Array.from(sections).map(s => s.getAttribute('data-preview-section'))
    expect(kinds).toEqual(['cover', 'toc', 'body', 'audit-annex'])
  })

  it('should_sanitize_block_html_before_rendering', () => {
    const payload = samplePreviewPayload({
      bodyBlockHtml: '<script>alert(1)</script><p>seguro</p>',
    })
    const { container } = render(<PreviewRenderer payload={payload} />)
    expect(container.querySelector('script')).toBeNull()
    expect(screen.getByText('seguro')).toBeInTheDocument()
  })

  it('should_link_citation_superscripts_to_audit_annex', () => {
    const payload = samplePreviewPayload({ withCitations: true })
    const { container } = render(<PreviewRenderer payload={payload} />)
    const sup = container.querySelector('sup a[href^="#audit-"]')
    expect(sup).not.toBeNull()
  })
})
