import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import deployment from '../vercel.json' with { type: 'json' }

export default defineConfig({
  plugins: [react()],
  base: '/',
  preview: {headers:Object.fromEntries(deployment.headers[0].headers.map(h=>[h.key,h.value]))},
  test: {
    globals: true,
    maxWorkers: 2,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
  },
})
