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
import './index.css'
import '@/shared/i18n'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
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
                  </Route>
                  <Route path="/redaccion/builder" element={<ReportTemplateBuilderPage />} />
                  <Route path="/redaccion/wizard" element={<GenericReportWizard />} />
                  <Route path="/automation" element={<PlaceholderPage section="Automatización" />} />
                  <Route path="/platform" element={<PlaceholderPage section="Plataforma" />} />
                </Route>
              </Route>
              <Route path="*" element={<Navigate to="/hub" replace />} />
            </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
