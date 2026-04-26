import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    lib: {
      entry: 'src/widget/main.tsx',
      name: 'GovGenAIWidget',
      fileName: 'widget',
      formats: ['iife'],
    },
    rollupOptions: {
      output: { inlineDynamicImports: true },
    },
    outDir: 'dist/widget',
  },
})
