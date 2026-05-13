/**
 * Tests 9R.7.1 (RED → GREEN)
 * ReportUIContractRenderer + DynamicUploadSlots + DynamicFieldRenderer
 */
import { describe, it, expect, vi, beforeAll } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import i18n from '@/shared/i18n'

import { ReportUIContractRenderer } from '../components/ReportUIContractRenderer'
import type { ReportUIContract } from '@/shared/api/generated/model'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

const SAMPLE_CONTRACT: ReportUIContract = {
  wizard_steps: [
    { id: 'step1', title: 'Datos', order: 0, block_ids: ['b1'] },
  ],
  dropzones: [
    {
      slot_id: 'excel_input',
      label: { es: 'Archivo Excel', en: 'Excel File' },
      accept: ['.xlsx', '.xls'],
      multiple: false,
      max_size_mb: 10,
    },
  ],
  manual_fields: [
    {
      slot_id: 'titulo',
      label: { es: 'Título del informe', en: 'Report title' },
      field_type: 'text',
      placeholder: { es: 'Introduce el título', en: 'Enter title' },
      required: true,
    },
    {
      slot_id: 'notas',
      label: { es: 'Notas adicionales', en: 'Additional notes' },
      field_type: 'text',
      placeholder: { es: 'Opcional', en: 'Optional' },
      required: false,
    },
  ],
  block_editor_enabled: false,
  ai_review_panel_enabled: false,
  preview_layout: 'markdown',
}

describe('DynamicUploadSlots', () => {
  it('should_render_upload_slots_from_ui_contract', () => {
    render(
      <ReportUIContractRenderer
        contract={SAMPLE_CONTRACT}
        onSubmit={vi.fn()}
      />
    )
    // The dropzone label should be rendered
    expect(screen.getByText('Archivo Excel')).toBeDefined()
    // File input with correct accept attribute
    const fileInput = screen.getByLabelText('Archivo Excel') as HTMLInputElement
    expect(fileInput.accept).toBe('.xlsx,.xls')
  })
})

describe('DynamicFieldRenderer', () => {
  it('should_render_dynamic_fields_from_ui_contract', () => {
    render(
      <ReportUIContractRenderer
        contract={SAMPLE_CONTRACT}
        onSubmit={vi.fn()}
      />
    )
    expect(screen.getByLabelText('Título del informe')).toBeDefined()
    expect(screen.getByLabelText('Notas adicionales')).toBeDefined()
  })

  it('should_block_continue_when_required_input_missing', async () => {
    const onSubmit = vi.fn()
    render(
      <ReportUIContractRenderer
        contract={SAMPLE_CONTRACT}
        onSubmit={onSubmit}
      />
    )

    // Click submit without filling required field
    fireEvent.click(screen.getByRole('button', { name: /continuar/i }))

    // onSubmit must not be called
    await waitFor(() => {
      expect(onSubmit).not.toHaveBeenCalled()
    })
  })

  it('should_show_validation_error_on_invalid_field', async () => {
    render(
      <ReportUIContractRenderer
        contract={SAMPLE_CONTRACT}
        onSubmit={vi.fn()}
      />
    )

    const titleInput = screen.getByLabelText('Título del informe')
    // Touch the field and leave empty
    fireEvent.blur(titleInput)
    fireEvent.click(screen.getByRole('button', { name: /continuar/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined()
    })
  })

  it('should_render_localized_labels_from_dict', () => {
    render(
      <ReportUIContractRenderer
        contract={SAMPLE_CONTRACT}
        onSubmit={vi.fn()}
      />
    )
    // i18n is set to 'es' — Spanish labels must be visible
    expect(screen.getByText('Título del informe')).toBeDefined()
    expect(screen.getByText('Notas adicionales')).toBeDefined()
    expect(screen.getByText('Archivo Excel')).toBeDefined()
    // English labels must NOT be visible
    expect(screen.queryByText('Report title')).toBeNull()
    expect(screen.queryByText('Excel File')).toBeNull()
  })
})
