// Regression: ISSUE-009 — 0 frontend tests
// Found by /qa on 2026-06-02
// Report: .gstack/qa-reports/qa-report-localhost-3000-2026-06-02.md

import { describe, it, expect, vi } from 'vitest'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from '@/App.vue'

// Mock router since App uses composables that depend on route
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ name: 'chat', path: '/' }),
  createRouter: vi.fn(),
  createMemoryHistory: vi.fn(),
}))

describe('App', () => {
  it('mounts without errors', () => {
    const app = createApp(App)
    app.use(createPinia())
    expect(() => app.mount(document.createElement('div'))).not.toThrow()
  })
})
