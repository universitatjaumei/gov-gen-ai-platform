import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/shared/i18n'

const root = document.getElementById('widget-root')
if (root) {
  createRoot(root).render(
    <StrictMode>
      <div>Widget — pendiente Prompt 9.9</div>
    </StrictMode>
  )
}
