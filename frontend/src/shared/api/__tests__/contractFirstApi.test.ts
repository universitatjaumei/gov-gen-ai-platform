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
 * Exento: el streaming SSE del chat del widget (`widget/hooks/useChat.ts`). Orval
 * no genera clientes para SSE y `customInstance` va sobre axios, que no expone el
 * cuerpo incremental. Ese fetch se queda, y lo que se le exige es que sea el ÚNICO.
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
]

/**
 * Único punto donde se permite construir `Authorization` a mano: el consumidor de
 * SSE. Todo lo demás pasa por el interceptor de `shared/api/client.ts`.
 */
const SSE_EXEMPT = 'widget/hooks/useChat.ts'

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

    const construyenAuth = sourceFiles()
      .filter((f) => /Authorization/.test(readFileSync(f, 'utf-8')))
      .map(rel)
      .filter((f) => !f.endsWith('__tests__/contractFirstApi.test.ts'))
      .sort()

    expect(
      construyenAuth,
      'La cabecera Authorization solo puede construirse en client.ts (interceptor) y en ' +
        'el consumidor de SSE, que Orval no cubre.',
    ).toEqual(['shared/api/client.ts', SSE_EXEMPT].sort())
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
