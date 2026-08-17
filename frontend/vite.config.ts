import { defineConfig } from 'vitest/config'
// `loadEnv` no lo reexporta `vitest/config`: sale de `vite`.
import { loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

/** Destino del proxy de desarrollo.
 *
 * Configurable por `VITE_API_TARGET` (`.env.local`) porque el puerto del backend no siempre
 * puede ser el de siempre: en esta máquina el 8000 quedó retenido por un proceso huérfano
 * que no responde a `taskkill`. El defecto no cambia, así que nadie tiene que hacer nada.
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
