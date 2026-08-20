import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { noReintentarSiElServidorYaDecidio } from '@/shared/api/reintentos'
import { Suspense, lazy } from 'react'
import { AuthProvider, PrivateRoute } from '@/shared/auth'
import { AppLayout } from '@/admin/AppLayout'
import { HubLayout } from '@/admin/HubLayout'
import { CurationLayout } from '@/curation/CurationLayout'
import { ThemeProvider } from './themes/ThemeProvider'
import './index.css'
import './themes/base.css'
import '@/shared/i18n'

/**
 * Las páginas se cargan por ruta (CAL.5).
 *
 * Con imports estáticos, Rollup metía las 17 pantallas en un solo bundle de **1,18 MB**: quien
 * entraba a ver una lista de chatbots se descargaba también el constructor de informes, el
 * asistente de scripts y `recharts`. Cada `import()` de aquí es un punto de corte, así que el
 * arranque sólo trae el armazón y la pantalla que se pide.
 *
 * Los envoltorios —`AppLayout`, `HubLayout`, `PrivateRoute`— siguen siendo estáticos: están en
 * todas las rutas, así que separarlos sólo añadiría una espera más sin ahorrar nada.
 *
 * `.then(m => ({ default: ... }))` es necesario porque estos módulos exportan con nombre y
 * `React.lazy` espera un `default`.
 */
const LoginPage = lazy(() => import('@/admin/pages/LoginPage').then(m => ({ default: m.LoginPage })))
const AuthCallbackPage = lazy(() => import('@/admin/pages/AuthCallbackPage').then(m => ({ default: m.AuthCallbackPage })))
const AccessTokensPage = lazy(() => import('@/admin/pages/AccessTokensPage').then(m => ({ default: m.AccessTokensPage })))
const ChatbotsPage = lazy(() => import('@/admin/pages/ChatbotsPage').then(m => ({ default: m.ChatbotsPage })))
const OrganizacionesPage = lazy(() => import('@/admin/pages/OrganizacionesPage').then(m => ({ default: m.OrganizacionesPage })))
const DocumentsPage = lazy(() => import('@/admin/pages/DocumentsPage').then(m => ({ default: m.DocumentsPage })))
const VigenciaPage = lazy(() => import('@/admin/pages/VigenciaPage').then(m => ({ default: m.VigenciaPage })))
const ReportsPage = lazy(() => import('@/admin/pages/ReportsPage').then(m => ({ default: m.ReportsPage })))
const LLMConfigsPage = lazy(() => import('@/admin/pages/LLMConfigsPage').then(m => ({ default: m.LLMConfigsPage })))
const PromptsPage = lazy(() => import('@/admin/pages/PromptsPage').then(m => ({ default: m.PromptsPage })))
const AIBrainPage = lazy(() => import('@/admin/pages/AIBrainPage').then(m => ({ default: m.AIBrainPage })))
const ActivityPromptsPage = lazy(() => import('@/admin/pages/ActivityPromptsPage').then(m => ({ default: m.ActivityPromptsPage })))
const RedaccionLayout = lazy(() => import('@/redaccion/RedaccionLayout').then(m => ({ default: m.RedaccionLayout })))
const CurationSitesPage = lazy(() => import('@/curation/SitesPage').then(m => ({ default: m.SitesPage })))
const CurationAuditPage = lazy(() => import('@/curation/AuditPage').then(m => ({ default: m.AuditPage })))
const CurationFindingsPage = lazy(() => import('@/curation/FindingsPage').then(m => ({ default: m.FindingsPage })))
const CurationPublicationPage = lazy(() => import('@/curation/PublicationPage').then(m => ({ default: m.PublicationPage })))
const TestScenariosPage = lazy(() => import('@/admin/pages/TestScenariosPage').then(m => ({ default: m.TestScenariosPage })))
const ReportTemplateBuilderPage = lazy(() => import('@/redaccion/pages/ReportTemplateBuilderPage').then(m => ({ default: m.ReportTemplateBuilderPage })))
const GenericReportWizard = lazy(() => import('@/redaccion/pages/GenericReportWizard').then(m => ({ default: m.GenericReportWizard })))
const LLMDraftPreviewPage = lazy(() => import('@/redaccion/pages/LLMDraftPreviewPage').then(m => ({ default: m.LLMDraftPreviewPage })))
const ScriptProposalWizardPage = lazy(() => import('@/redaccion/pages/ScriptProposalWizardPage').then(m => ({ default: m.ScriptProposalWizardPage })))
const AdminScriptReviewQueuePage = lazy(() => import('@/redaccion/pages/AdminScriptReviewQueuePage').then(m => ({ default: m.AdminScriptReviewQueuePage })))
const WorkspacePreview = lazy(() => import('@/redaccion/preview/WorkspacePreview').then(m => ({ default: m.WorkspacePreview })))
const WorkspacePage = lazy(() => import('@/redaccion/pages/WorkspacePage').then(m => ({ default: m.WorkspacePage })))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // INF.3 — un 4xx no se reintenta: es una decisión del servidor, no una avería. Con
      // `retry: 2` a secas, un 409 de la vista previa se pedía tres veces antes de que la
      // pantalla pudiera explicar nada, y en ese hueco la consulta no está ni cargando ni en
      // error. Ver `shared/api/reintentos.ts`.
      retry: noReintentarSiElServidorYaDecidio,
      staleTime: 1000 * 60 * 5,
    },
  },
})

const getThemeUrl = (): string | undefined => {
  const params = new URLSearchParams(window.location.search)
  return params.get('theme') ?? undefined
}

/**
 * Espera mientras llega el trozo de la ruta.
 *
 * Antes el `fallback` era `null` porque no había nada que esperar: todo venía en el bundle
 * inicial. Con la carga por ruta, `null` dejaría la pantalla en blanco durante la descarga y
 * parecería que la aplicación se ha colgado.
 */
function CargandoRuta() {
  return (
    <div className="flex items-center justify-center p-12" role="status" aria-live="polite">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted border-t-primary" />
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider themeUrl={getThemeUrl()}>
      <BrowserRouter>
        <AuthProvider>
          <Suspense fallback={<CargandoRuta />}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/auth/callback" element={<AuthCallbackPage />} />
              <Route element={<PrivateRoute />}>
                <Route element={<AppLayout />}>
                  <Route index element={<Navigate to="/hub" replace />} />
                  <Route path="/hub" element={<HubLayout />}>
                    <Route index element={<Navigate to="/hub/chatbots" replace />} />
                    <Route path="chatbots" element={<ChatbotsPage />} />
                    <Route path="organizaciones" element={<OrganizacionesPage />} />
                    <Route path="documents" element={<DocumentsPage />} />
                    <Route path="vigencia" element={<VigenciaPage />} />
                    <Route path="reports" element={<ReportsPage />} />
                    <Route path="llm-configs" element={<LLMConfigsPage />} />
                    <Route path="prompts" element={<PromptsPage />} />
                    <Route path="activity-prompts" element={<ActivityPromptsPage />} />
                    <Route path="brain" element={<AIBrainPage />} />
                    <Route path="test-scenarios" element={<TestScenariosPage />} />
                    <Route path="access-tokens" element={<AccessTokensPage />} />
                  </Route>
                  <Route path="/curation" element={<CurationLayout />}>
                    <Route index element={<Navigate to="/curation/sites" replace />} />
                    <Route path="sites" element={<CurationSitesPage />} />
                    <Route path="audit" element={<CurationAuditPage />} />
                    <Route path="findings" element={<CurationFindingsPage />} />
                    <Route path="publish" element={<CurationPublicationPage />} />
                  </Route>
                  {/* Informes: las pantallas existían pero sus rutas estaban sueltas y
                      fuera de todo menú, así que sólo se llegaba escribiendo la URL. */}
                  <Route path="/redaccion" element={<RedaccionLayout />}>
                    <Route index element={<Navigate to="/redaccion/builder" replace />} />
                    <Route path="builder" element={<ReportTemplateBuilderPage />} />
                    <Route path="wizard" element={<GenericReportWizard />} />
                    <Route path="draft" element={<LLMDraftPreviewPage />} />
                    <Route path="scripts/wizard" element={<ScriptProposalWizardPage />} />
                    <Route path="scripts/review" element={<AdminScriptReviewQueuePage />} />
                  </Route>
                  {/* Fuera del layout: es una vista de impresión, sin navegación. */}
                  <Route path="/redaccion/workspaces/:id/preview" element={<WorkspacePreview />} />
                  {/* La pantalla donde se trabaja un informe. Existían todos sus componentes
                      desde 9R y ninguna ruta los montaba (VER.4). */}
                  <Route path="/redaccion/workspaces/:id" element={<WorkspacePage />} />
                </Route>
              </Route>
              <Route path="*" element={<Navigate to="/hub" replace />} />
            </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
