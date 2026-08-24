/**
 * CAL.2 — Guardarraíl de la capa API: el frontend habla por el contrato.
 *
 * Cierra el literal `// TODO CF.4` que llevaban los módulos de `shared/api/*.ts`
 * escritos a mano. Cada uno de ellos repetía tres cosas que no le tocan decidir a
 * una pantalla: la URL base del servidor, cómo se construye la cabecera de
 * autenticación, y la forma del dato que devuelve la API.
 *
 * Los tres se comprueban aquí de forma estática, leyendo el árbol, porque es la
 * única manera de que un módulo nuevo escrito a mano dentro de seis meses no pase
 * desapercibido: un test de render solo ve la pantalla que renderiza.
 *
 * Exento: el widget público (`widget/`), que deliberadamente no importa el cliente
 * generado — el bundle es un IIFE independiente (`vite.config.widget.ts`) y arrastrar
 * react-query + axios ahí infla un script pensado para pesar poco. Dos ficheros hacen
 * `fetch` a mano por eso: `hooks/useChat.ts` (streaming SSE; Orval no genera clientes
 * para eso y `customInstance` va sobre axios, que no expone el cuerpo incremental) y
 * `main.tsx` (tema del chatbot para pintar el widget). Lo que se exige es que la lista
 * de excepciones no crezca sin que alguien la mire.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs'
import { join, resolve, relative } from 'node:path'

const SRC = resolve(__dirname, '../../..')

/** Los cinco módulos que CAL.2 retira, más el del copiloto (misma deuda). */
const MANUAL_API_MODULES = [
  'shared/api/ingestion.ts',
  'shared/api/organizaciones.ts',
  'shared/api/feedback.ts',
  'shared/api/llmConfigs.ts',
  'shared/api/promptTemplates.ts',
  'shared/layout/copilot/copilotApi.ts',
  // AIS.4 — el séptimo, que esta lista no vigilaba porque nadie lo añadió. Llamaba a tres
  // endpoints autenticados con `fetch` crudo y sin credencial, así que devolvían 401 y el panel
  // de anonimización no funcionaba desde el navegador. Ver el test de más abajo: una lista de
  // nombres sólo protege de lo que alguien recordó apuntar, y por eso ahora hay una regla que
  // los **descubre**.
  'redaccion/hooks/useAnonymizationApi.ts',
]

/**
 * Directorios cuyo código llama a la API por el cliente generado, sin excepciones.
 *
 * El widget queda fuera **con razón escrita** (ver el test): es un bundle IIFE aparte que usa
 * SSE, que axios no cubre. `admin/pages/LoginPage.tsx` también, porque ocurre antes de haber
 * credencial que interceptar.
 */
const SIN_FETCH_A_MANO = ['redaccion', 'curation', 'admin']

const EXENTOS_DE_FETCH = ['admin/pages/LoginPage.tsx']

function sourceFiles(): string[] {
  const out: string[] = []
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry)
      if (statSync(full).isDirectory()) {
        if (entry === 'node_modules' || entry === 'generated') continue
        walk(full)
        continue
      }
      if (/\.(ts|tsx)$/.test(entry)) out.push(full)
    }
  }
  walk(SRC)
  return out
}

const rel = (f: string) => relative(SRC, f).replace(/\\/g, '/')

describe('CAL.2 — capa API generada desde el contrato', () => {
  it('should_not_import_from_shared_api_manual_modules', () => {
    // Primero: los ficheros ya no existen.
    const supervivientes = MANUAL_API_MODULES.filter((m) => existsSync(join(SRC, m)))
    expect(
      supervivientes,
      `Módulos API escritos a mano que siguen en el árbol: ${supervivientes.join(', ')}`,
    ).toEqual([])

    // Segundo: nadie los importa. Comprobar solo lo primero dejaría pasar un
    // import a un fichero borrado, que es un fallo de build, no de test.
    const specifiers = MANUAL_API_MODULES.map((m) => m.replace(/\.ts$/, ''))
    const culpables: string[] = []
    for (const file of sourceFiles()) {
      const code = readFileSync(file, 'utf-8')
      for (const spec of specifiers) {
        const bare = spec.split('/').pop()!
        const patrones = [`@/${spec}`, `./${bare}'`, `./${bare}"`]
        if (patrones.some((p) => code.includes(p))) {
          culpables.push(`${rel(file)} → ${spec}`)
        }
      }
    }
    expect(culpables, `Imports a módulos API retirados:\n${culpables.join('\n')}`).toEqual([])
  })

  it('should_use_generated_hook_not_manual_fetch_in_documents_page', () => {
    const page = readFileSync(join(SRC, 'admin/pages/DocumentsPage.tsx'), 'utf-8')

    expect(page).toContain('@/shared/api/generated/hub-ingestion/hub-ingestion')
    expect(page).toMatch(/useListDocumentsApiV1HubIngestionChatbotIdDocumentsGet/)
    expect(page).toMatch(/useGetIngestionJobsApiV1HubIngestionChatbotIdJobsGet/)

    // Ni un fetch crudo ni una URL de API construida a mano en la página.
    expect(page).not.toMatch(/\bfetch\(/)
    expect(page).not.toContain('/api/v1/')
  })

  it('should_send_auth_via_custom_instance', () => {
    // La cabecera se construye en un solo sitio: el interceptor de client.ts.
    const client = readFileSync(join(SRC, 'shared/api/client.ts'), 'utf-8')
    expect(client).toMatch(/interceptors\.request\.use/)
    expect(client).toMatch(/Authorization/)

    // Los ficheros de test solo *comprueban* la cabecera (fixtures, aserciones): no
    // son el código de producción que este guardarraíl vigila.
    const esFicheroDeTest = (f: string) => f.split('/').includes('__tests__')

    const construyenAuth = sourceFiles()
      .filter((f) => /Authorization/.test(readFileSync(f, 'utf-8')))
      .map(rel)
      .filter((f) => !esFicheroDeTest(f))
      .sort()

    // SEC.8.5: el widget deja de ser una excepción. Embebía un JWT o un PAT completo en
    // el HTML de la página —visible para cualquiera y con el rol de su dueño detrás— y
    // ahora manda `X-Widget-Key`, una credencial de sitio que solo abre su propio chatbot
    // si es público. Así que ya no queda más sitio que el interceptor.
    expect(
      construyenAuth,
      'La cabecera Authorization solo puede construirse en client.ts (interceptor).',
    ).toEqual(['shared/api/client.ts'])
  })

  it('should_discover_hand_written_api_calls_instead_of_listing_them', () => {
    /**
     * AIS.4 — la regla que faltaba, y el fallo de método que la justifica.
     *
     * Este fichero comprobaba dos cosas y ninguna cazaba `useAnonymizationApi.ts`: la lista de
     * módulos manuales no lo incluía —porque se escribió antes y nadie lo añadió—, y la
     * comprobación de la credencial busca ficheros que **mencionen** la cabecera, así que aquel
     * pasaba **precisamente por no construirla**. Un guardarraíl que sólo mira lo que alguien
     * recordó apuntar no protege de lo que nadie recordó.
     *
     * Esto lo invierte: se recorre el árbol y se exige que ningún módulo de pantalla llame a la
     * API por su cuenta. Lo que sea excepción, se declara arriba con su motivo.
     */
    const culpables = sourceFiles()
      .map(rel)
      .filter((f) => SIN_FETCH_A_MANO.some((d) => f.startsWith(`${d}/`)))
      .filter((f) => !f.split('/').includes('__tests__'))
      .filter((f) => !EXENTOS_DE_FETCH.includes(f))
      .filter((f) => /\bfetch\s*\(/.test(readFileSync(join(SRC, f), 'utf-8')))
      .sort()

    expect(
      culpables,
      'estos ficheros de pantalla llaman a la API con `fetch` a mano: la credencial la pone el ' +
        'interceptor de client.ts, así que un fetch propio se la salta y el endpoint responde ' +
        '401 sin que nada lo delate hasta que alguien abre la pantalla',
    ).toEqual([])
  })

  it('should_type_ingestion_job_from_generated_model', () => {
    // El tipo existe en el contrato generado…
    for (const modelo of ['ingestionJob.ts', 'hubDocumentOut.ts', 'hubDocumentDetailOut.ts']) {
      expect(
        existsSync(join(SRC, 'shared/api/generated/model', modelo)),
        `Falta ${modelo} en generated/model: el backend no declara response_model para ese endpoint.`,
      ).toBe(true)
    }

    // …y es el que usa la página, en lugar de una interfaz redeclarada.
    const page = readFileSync(join(SRC, 'admin/pages/DocumentsPage.tsx'), 'utf-8')
    expect(page).toMatch(/from '@\/shared\/api\/generated\/model'/)
    expect(page).toMatch(/\bHubDocumentOut\b/)
    expect(page).not.toMatch(/^\s*(export\s+)?interface\s+(IngestionJob|HubDocument)/m)
  })

  it('should_not_hardcode_api_host_outside_dev_config', () => {
    const conHost = sourceFiles()
      .filter((f) => readFileSync(f, 'utf-8').includes('localhost:8000'))
      .map(rel)
      // Los tests del widget fijan una URL de ejemplo como dato de entrada; eso es
      // configuración de la prueba, no una URL de servidor incrustada en el código.
      .filter((f) => !f.includes('__tests__/'))
      .sort()

    expect(
      conHost,
      `El host de la API se resuelve por configuración, no en el código: ${conHost.join(', ')}`,
    ).toEqual([])
  })
})
