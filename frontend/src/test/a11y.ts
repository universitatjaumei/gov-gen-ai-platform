import axe from 'axe-core'
import { expect } from 'vitest'

const WCAG_RULES: axe.RuleObject = {
  'color-contrast': { enabled: true },
  'aria-required-attr': { enabled: true },
  'aria-required-children': { enabled: true },
  'aria-required-parent': { enabled: true },
  'aria-valid-attr': { enabled: true },
  'aria-valid-attr-value': { enabled: true },
  'button-name': { enabled: true },
  'document-title': { enabled: true },
  'duplicate-id': { enabled: true },
  'form-field-multiple-labels': { enabled: true },
  'frame-title': { enabled: true },
  'html-has-lang': { enabled: true },
  'html-lang-valid': { enabled: true },
  'image-alt': { enabled: true },
  'input-button-name': { enabled: true },
  'input-image-alt': { enabled: true },
  'label': { enabled: true },
  'link-name': { enabled: true },
  'list': { enabled: true },
  'listitem': { enabled: true },
  'meta-viewport': { enabled: true },
  'select-name': { enabled: true },
  'svg-img-alt': { enabled: true },
  'tabindex': { enabled: true },
  'focus-order-semantics': { enabled: true },
  'landmark-one-main': { enabled: true },
  'region': { enabled: true },
}

export async function expectNoA11yViolations(container: HTMLElement): Promise<void> {
  const results = await axe.run(container, { rules: WCAG_RULES })
  const significant = results.violations.filter(
    v => v.impact === 'critical' || v.impact === 'serious',
  )
  expect(
    significant,
    significant.map(v => `[${v.impact}] ${v.id}: ${v.description}`).join('\n'),
  ).toHaveLength(0)
}
