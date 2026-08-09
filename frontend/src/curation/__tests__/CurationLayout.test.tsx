import { describe, it, expect, beforeAll } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import i18n from '@/shared/i18n'
import { CurationLayout } from '../CurationLayout'

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

describe('CurationLayout', () => {
  it('should_render_curation_nav_without_chatbot_context: la navegación de curación no depende de ningún chatbot ni documento', () => {
    render(
      <MemoryRouter initialEntries={['/curation/sites']}>
        <Routes>
          <Route element={<CurationLayout />}>
            <Route path="/curation/sites" element={<div>Sitios</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    )

    // Las cuatro pestañas propias existen: Sitios, Auditoría, Hallazgos, Publicación.
    // Ninguna requiere una prop, un contexto ni un chatbot seleccionado — la curación es
    // previa al asistente (docs/DECISION_CURACION_SEPARADA.md).
    expect(screen.getByRole('link', { name: /sitios/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /auditoría/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /hallazgos/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /publicación/i })).toBeInTheDocument()
  })
})
