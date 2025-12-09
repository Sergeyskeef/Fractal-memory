import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './tests/setup.ts',
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/e2e/**', // E2E тесты для Playwright
      '**/*.config.*',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'tests/',
        '**/e2e/**',
        '*.config.*',
        'dist/',
      ],
    },
  },
})

