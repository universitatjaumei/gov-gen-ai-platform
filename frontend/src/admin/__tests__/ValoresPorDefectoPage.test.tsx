import { describe, it, expect, beforeEach, beforeAll, vi } from 'vitest'
import { render, screen, within, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { ValoresPorDefectoPage } from '../pages/ValoresPorDefectoPage'
import {
  useListOrganizacionesApiV1HubOrganizacionesGet,
  useGetValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoGet as useValores,
  useUpdateValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoPatch as useGuardar,
} from '@/shared/api/generated/hub-organizaciones/hub-organizaciones'

/**
 * PLAT.3 — los valores por defecto de RAG, en su módulo.
 *
 * Vivían dentro de la pantalla de Organizaciones, y por eso esa pantalla acabó bajo Chatbots: la
 * mayoría de sus campos eran de Chatbots. Lo que esta pantalla tiene que hacer bien, además de
 * mostrarlos, es **distinguir un valor propio de uno heredado** y permitir volver a heredar —
 * que hasta PLAT.3 era imposible por API, porque el `PATCH` descartaba el `null` explícito.
 */
vi.mock('@/shared/api/generated/hub-organizaciones/hub-organizaciones', () => ({
  useListOrganizacionesApiV1HubOrganizacionesGet: vi.fn(),
  useGetValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoGet: vi.fn(),
  useUpdateValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoPatch: vi.fn(),
  getGetValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoGetQueryKey: () => [
    'valores',
  ],
}))

const ORGS = [
  { id: 'org-1', name: 'Universitat Jaume I' },
  { id: 'org-2', name: 'Diputación de Castellón' },
]

const VALORES = {
  default_public_graph_profile: 'PUBLIC_KB_RICH',
  default_retrieval_mode: 'RAG',
  default_reranker_enabled: false,
  // Con valor propio: se puede volver a heredar.
  default_chunk_size: 500,
  // Heredado ya: no se ofrece volver a heredar lo que ya hereda.
  default_chunk_overlap: null,
  default_context_token_budget: null,
}

const guardar = vi.fn()

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  guardar.mockClear()
  vi.mocked(useListOrganizacionesApiV1HubOrganizacionesGet).mockReturnValue({
    data: ORGS,
  } as never)
  vi.mocked(useValores).mockReturnValue({ data: VALORES, isLoading: false } as never)
  vi.mocked(useGuardar).mockReturnValue({ mutate: guardar, isPending: false } as never)
})

function renderPage() {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={cliente}>
      <ValoresPorDefectoPage />
    </QueryClientProvider>
  )
}

describe('PLAT.3 — la pantalla de valores por defecto', () => {
  it('should_let_you_pick_the_organisation', () => {
    // Es configuración del módulo aplicada a una organización, no identidad de una.
    renderPage()

    const selector = screen.getByLabelText(/organización/i)
    expect([...selector.querySelectorAll('option')].map((o) => o.textContent)).toEqual([
      'Universitat Jaume I',
      'Diputación de Castellón',
    ])
  })

  it('should_render_every_field_the_server_sends', () => {
    // Iterando la respuesta: si el contrato crece, la pantalla crece.
    renderPage()

    expect(screen.getByTestId('default_public_graph_profile')).toBeDefined()
    expect(screen.getByTestId('default_chunk_size')).toBeDefined()
  })

  it('should_say_inherited_instead_of_leaving_it_blank', () => {
    // `null` aquí es una decisión, no un dato que falte.
    renderPage()

    expect(screen.getByTestId('default_chunk_overlap').textContent).toMatch(/heredado/i)
  })

  it('should_offer_going_back_to_inheriting_only_where_it_applies', () => {
    renderPage()

    const conValorPropio = screen.getByTestId('default_chunk_size')
    expect(within(conValorPropio).getByRole('button', { name: /heredar/i })).toBeDefined()

    // Ya heredado: no hay nada que devolver.
    expect(within(screen.getByTestId('default_chunk_overlap')).queryByRole('button')).toBeNull()

    // No heredable: el reranker no tiene defecto de plataforma que heredar.
    expect(within(screen.getByTestId('default_reranker_enabled')).queryByRole('button')).toBeNull()
  })

  it('should_send_an_explicit_null_when_going_back_to_inheriting', () => {
    // **El test del prompt**: el `null` explícito es lo que `exclude_none` descartaba.
    renderPage()

    const fila = screen.getByTestId('default_chunk_size')
    fireEvent.click(within(fila).getByRole('button', { name: /heredar/i }))

    expect(guardar).toHaveBeenCalledWith(
      { organizacionId: 'org-1', data: { default_chunk_size: null } },
      expect.anything()
    )
  })

  it('should_show_a_translated_label_and_not_the_field_name', () => {
    // Ensenar `default_public_graph_profile` a una persona es ensenarle el contrato.
    renderPage()

    expect(screen.getByTestId('default_public_graph_profile').textContent).toMatch(
      /Perfil de grafo/i
    )
  })

  it('should_fall_back_to_the_field_name_for_a_field_with_no_label', () => {
    // Si el contrato crece, la fila aparece igual en vez de quedarse vacia.
    vi.mocked(useValores).mockReturnValue({
      data: { default_campo_futuro: 7 },
      isLoading: false,
    } as never)
    renderPage()

    expect(screen.getByTestId('default_campo_futuro').textContent).toMatch(
      /default_campo_futuro/
    )
  })

  it('should_say_this_is_not_tenant_identity', () => {
    renderPage()

    expect(document.body.textContent).toMatch(/no es identidad|Chatbots/i)
  })
})
