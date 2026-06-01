import axe from 'axe-core'
import { expect } from 'vitest'

export async function expectNoAxeViolations(container: HTMLElement): Promise<void> {
  const results = await axe.run(container)
  const criticalOrSerious = results.violations.filter(
    v => v.impact === 'critical' || v.impact === 'serious',
  )
  expect(
    criticalOrSerious,
    criticalOrSerious.map(v => `${v.id}: ${v.description}`).join('\n'),
  ).toHaveLength(0)
}
