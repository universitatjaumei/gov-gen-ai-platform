import { describe, it, beforeAll } from 'vitest'
import { render } from '@testing-library/react'
import i18n from '@/shared/i18n'
import { WorkspaceEditor } from '@/redaccion/components/WorkspaceEditor'
import { mockWorkspaceWithMixedBlocks } from '@/test-utils/fixtures'
import { expectNoA11yViolations } from '@/test/a11y'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

describe('WorkspaceEditor — WCAG 2.2 AA baseline', () => {
  it('should_have_no_critical_a11y_violations', async () => {
    const { container } = render(
      <WorkspaceEditor workspace={mockWorkspaceWithMixedBlocks()} />,
    )
    await expectNoA11yViolations(container)
  })

  it('should_have_no_critical_a11y_violations_with_drawer_open', async () => {
    const { container } = render(
      <WorkspaceEditor workspace={mockWorkspaceWithMixedBlocks({ block1State: 'ai_generated' })} />,
    )
    await expectNoA11yViolations(container)
  })
})
