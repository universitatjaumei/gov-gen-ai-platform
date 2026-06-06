import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense } from 'react'
import { AuthProvider, PrivateRoute } from '@/shared/auth'
import { AppLayout } from '@/admin/AppLayout'
import { HubLayout } from '@/admin/HubLayout'
import { LoginPage } from '@/admin/pages/LoginPage'
import { ChatbotsPage } from '@/admin/pages/ChatbotsPage'
import { ClientsPage } from '@/admin/pages/ClientsPage'
import { DocumentsPage } from '@/admin/pages/DocumentsPage'
import { ReportsPage } from '@/admin/pages/ReportsPage'
import { LLMConfigsPage } from '@/admin/pages/LLMConfigsPage'
import { PromptsPage } from '@/admin/pages/PromptsPage'
import { PlaceholderPage } from '@/admin/pages/PlaceholderPage'
import { ReportTemplateBuilderPage } from '@/redaccion/pages/ReportTemplateBuilderPage'
import { GenericReportWizard } from '@/redaccion/pages/GenericReportWizard'
import { LLMDraftPreviewPage } from '@/redaccion/pages/LLMDraftPreviewPage'
import { ScriptProposalWizardPage } from '@/redaccion/pages/ScriptProposalWizardPage'
import { AdminScriptReviewQueuePage } from '@/redaccion/pages/AdminScriptReviewQueuePage'
import { WorkspacePreview } from '@/redaccion/preview/WorkspacePreview'
import { AIBrainPage } from '@/admin/pages/AIBrainPage'
import { SitesPage } from '@/admin/pages/SitesPage'
import { ContentQualityPage } from '@/admin/pages/ContentQualityPage'
import { ThemeProvider } from './themes/ThemeProvider'
import './index.css'
import './themes/base.css'
import '@/shared/i18n'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 1000 * 60 * 5,
    },
  },
})

const getThemeUrl = (): string | undefined => {
  const params = new URLSearchParams(window.location.search)
  return params.get('theme') ?? undefined
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider themeUrl={getThemeUrl()}>
      <BrowserRouter>
        <AuthProvider>
          <Suspense fallback={null}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<PrivateRoute />}>
                <Route element={<AppLayout />}>
                  <Route index element={<Navigate to="/hub" replace />} />
                  <Route path="/hub" element={<HubLayout />}>
                    <Route index element={<Navigate to="/hub/chatbots" replace />} />
                    <Route path="chatbots" element={<ChatbotsPage />} />
                    <Route path="clients" element={<ClientsPage />} />
                    <Route path="documents" element={<DocumentsPage />} />
                    <Route path="reports" element={<ReportsPage />} />
                    <Route path="llm-configs" element={<LLMConfigsPage />} />
                    <Route path="prompts" element={<PromptsPage />} />
                    <Route path="brain" element={<AIBrainPage />} />
                    <Route path="sites" element={<SitesPage />} />
                    <Route path="content-quality" element={<ContentQualityPage />} />
                  </Route>
                  <Route path="/redaccion/builder" element={<ReportTemplateBuilderPage />} />
                  <Route path="/redaccion/wizard" element={<GenericReportWizard />} />
                  <Route path="/redaccion/draft" element={<LLMDraftPreviewPage />} />
                  <Route path="/redaccion/scripts/wizard" element={<ScriptProposalWizardPage />} />
                  <Route path="/redaccion/scripts/review" element={<AdminScriptReviewQueuePage />} />
                  <Route path="/redaccion/workspaces/:id/preview" element={<WorkspacePreview />} />
                  <Route path="/automation" element={<PlaceholderPage section="Automatización" />} />
                  <Route path="/platform" element={<PlaceholderPage section="Plataforma" />} />
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
