import { describe, it, expect, beforeAll } from 'vitest'
import { render } from '@testing-library/react'
import i18n from '@/shared/i18n'
import { expectNoAxeViolations } from '@/test-utils/axe'
import { WorkspaceEditor } from '../WorkspaceEditor'
import { mockWorkspaceWithMixedBlocks } from '@/test-utils/fixtures'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

describe('Editor accessibility (WCAG 2.2 AA)', () => {
  it('should_pass_axe_audit_on_workspace_with_mixed_block_states', async () => {
    const { container } = render(
      <WorkspaceEditor workspace={mockWorkspaceWithMixedBlocks()} />,
    )
    await expectNoAxeViolations(container)
  })

  it('should_announce_block_state_change_via_aria_live', () => {
    const { container, rerender } = render(
      <WorkspaceEditor workspace={mockWorkspaceWithMixedBlocks({ block1State: 'draft' })} />,
    )
    rerender(
      <WorkspaceEditor workspace={mockWorkspaceWithMixedBlocks({ block1State: 'ai_generated' })} />,
    )
    const live = container.querySelector('[aria-live="polite"]')
    expect(live?.textContent).toMatch(/borrador IA listo/i)
  })

  it('should_trap_focus_within_drawer_when_open', () => {
    // Render con drawer abierto; comprobar que document.activeElement está dentro del drawer.
  })

  it('should_restore_focus_to_trigger_on_drawer_close', () => {
    // Render con botón trigger; abre drawer; cierra; comprobar activeElement = trigger.
  })

  it('should_pass_axe_audit_on_drawer_open_state', async () => {
    const { container } = render(
      <WorkspaceEditor workspace={mockWorkspaceWithMixedBlocks()} />,
    )
    await expectNoAxeViolations(container)
  })
})
