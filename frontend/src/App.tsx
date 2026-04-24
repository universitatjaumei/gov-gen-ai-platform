import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense } from 'react'
import { AuthProvider, PrivateRoute } from '@/shared/auth'
import { AppLayout } from '@/admin/AppLayout'
import { LoginPage } from '@/admin/pages/LoginPage'
import { ChatbotsPage } from '@/admin/pages/ChatbotsPage'
import { PlaceholderPage } from '@/admin/pages/PlaceholderPage'
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
                  <Route path="/hub" element={<ChatbotsPage />} />
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
