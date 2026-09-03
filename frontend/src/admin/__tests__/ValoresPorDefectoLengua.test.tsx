import { describe, it, expect, beforeEach, beforeAll, vi } from 'vitest'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from '@/shared/i18n'
import { ValoresPorDefectoPage } from '../pages/ValoresPorDefectoPage'
import {
  useListOrganizacionesApiV1HubOrganizacionesGet,
  useGetValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoGet as useValores,
  useUpdateValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoPatch as useGuardar,
} from '@/shared/api/generated/hub-organizaciones/hub-organizaciones'
import { useOpcionesDeLengua } from '@/shared/api/generated/hub-opciones/hub-opciones'

/**
 * LANG.2 — el defecto de modo de idioma de una organización, ofrecido desde el contrato.
 *
 * **La lista escrita a mano decía `['prefer', 'strict', 'neutral']`, y dos de los tres eran
 * falsos**: `strict` es una política que la factoría del grafo nunca compuso, y `neutral` no es
 * ningún valor —es el nombre de la clase; el modo se llama `none`—. Desde LANG.1 los dos dan 422
 * al guardar, así que la pantalla ofrecía dos opciones que rompen.
 *
 * Se sigue usando `<datalist>` y no `<select>`, que es la decisión de PLAT.3 y su motivo sigue en
 * pie: el contrato declara el campo como cadena libre —tiene que serlo, `fixed:<código>` es
 * paramétrico—, así que un desplegable perdería en silencio cualquier valor que la lista no
 * conociera. Lo que cambia es de dónde sale la lista.
 */
vi.mock('@/shared/api/generated/hub-organizaciones/hub-organizaciones', () => ({
  useListOrganizacionesApiV1HubOrganizacionesGet: vi.fn(),
  useGetValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoGet: vi.fn(),
  useUpdateValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoPatch: vi.fn(),
  getGetValoresPorDefectoApiV1HubOrganizacionesOrganizacionIdValoresPorDefectoGetQueryKey: () => [
    'valores',
  ],
}))

vi.mock('@/shared/api/generated/hub-opciones/hub-opciones', () => ({
  useOpcionesDeLengua: vi.fn(),
}))

const CATALOGO = {
  modos: [
    { valor: 'prefer', requiere_lengua: false, es_por_defecto: true },
    { valor: 'none', requiere_lengua: false, es_por_defecto: false },
    { valor: 'fixed', requiere_lengua: true, es_por_defecto: false },
  ],
  lenguas: [
    { codigo: 'val', etiqueta: 'Valencià' },
    { codigo: 'es', etiqueta: 'Castellano' },
    { codigo: 'en', etiqueta: 'English' },
  ],
}

beforeAll(async () => {
  await i18n.changeLanguage('es')
})

beforeEach(() => {
  localStorage.clear()
  vi.mocked(useListOrganizacionesApiV1HubOrganizacionesGet).mockReturnValue({
    data: [{ id: 'org-1', name: 'Universitat Jaume I' }],
  } as never)
  vi.mocked(useValores).mockReturnValue({
    data: { default_language_mode: 'prefer' },
    isLoading: false,
  } as never)
  vi.mocked(useGuardar).mockReturnValue({ mutate: vi.fn(), isPending: false } as never)
  vi.mocked(useOpcionesDeLengua).mockReturnValue({ data: CATALOGO, isLoading: false } as never)
})

function renderPage() {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={cliente}>
      <ValoresPorDefectoPage />
    </QueryClientProvider>
  )
}

/** Los valores que la pantalla ofrece para `default_language_mode`, de su `<datalist>`.
 *
 * Se busca por el `id` que la pantalla compone (`vpd_<campo>_opciones`) y no navegando el DOM
 * desde la fila: el `<datalist>` es un elemento hermano del input, no un hijo.
 */
function opciones(): string[] {
  const lista = document.getElementById('vpd_default_language_mode_opciones')
  return Array.from(lista?.querySelectorAll('option') ?? []).map(
    (o) => o.getAttribute('value') ?? ''
  )
}

describe('LANG.2 — el defecto de idioma de la organización', () => {
  it('should_offer_the_modes_the_server_sent', () => {
    renderPage()

    expect(opciones()).toEqual(['prefer', 'none', 'fixed:val', 'fixed:es', 'fixed:en'])
  })

  it('should_not_offer_the_two_values_that_break', () => {
    /** `strict` no lo compone la factoría y `neutral` no existe: los dos dan 422 al guardar. */
    renderPage()

    expect(opciones()).not.toContain('strict')
    expect(opciones()).not.toContain('neutral')
  })

  it('should_offer_the_corpus_code_and_not_the_langdetect_one', () => {
    renderPage()

    expect(opciones()).toContain('fixed:val')
    expect(opciones()).not.toContain('fixed:ca')
  })

  it('should_offer_nothing_of_its_own_while_the_catalogue_is_missing', () => {
    vi.mocked(useOpcionesDeLengua).mockReturnValue({ data: undefined, isLoading: true } as never)

    renderPage()

    expect(opciones()).toEqual([])
  })
})
