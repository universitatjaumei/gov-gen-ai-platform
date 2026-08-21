import { defineConfig } from 'vitest/config'
// `loadEnv` no lo reexporta `vitest/config`: sale de `vite`.
import { loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

/** Destino del proxy de desarrollo.
 *
 * Configurable por `VITE_API_TARGET` (`.env.local`) para quien necesite otro puerto, pero el
 * defecto es el bueno: es el puerto en el que `arranque.bat` levanta el backend.
 *
 * Si el 8000 da `WinError 10048`, no es que haga falta otro puerto: lo retiene el árbol de
 * procesos de un uvicorn `--reload` anterior cuyo arranque falló, con el socket en estado
 * `Bound` (invisible para `netstat | findstr LISTENING`). Se mata el árbol entero y se sigue
 * en el 8000. Detalle en la nota del 2026-08-20 de `planificacion/PROJECT_STATE.md`.
 */
const DESTINO_API_POR_DEFECTO = 'http://localhost:8000'

export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    proxy: {
      '/api': {
        target: loadEnv(mode, process.cwd(), '').VITE_API_TARGET || DESTINO_API_POR_DEFECTO,
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      input: {
        admin: 'index.html',
        widget: 'widget.html',
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/.{idea,git,cache,output,temp}/**',
      'src/__tests__/a11y/**',
    ],
  },
}))
