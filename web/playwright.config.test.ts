import { afterEach, expect, test, vi } from 'vitest'

const originalBaseUrl = process.env.PLAYWRIGHT_BASE_URL

afterEach(() => {
  if (originalBaseUrl === undefined) delete process.env.PLAYWRIGHT_BASE_URL
  else process.env.PLAYWRIGHT_BASE_URL = originalBaseUrl
  vi.resetModules()
})

test('uses a remote base URL without starting the local preview server', async () => {
  process.env.PLAYWRIGHT_BASE_URL = 'https://mv-analyzer.writingdeveloper.blog'
  vi.resetModules()

  const { default: config } = await import('./playwright.config')

  expect(config.use?.baseURL).toBe('https://mv-analyzer.writingdeveloper.blog')
  expect(config.webServer).toBeUndefined()
})

test('keeps the local preview server as the default target', async () => {
  delete process.env.PLAYWRIGHT_BASE_URL
  vi.resetModules()

  const { default: config } = await import('./playwright.config')

  expect(config.use?.baseURL).toBe('http://127.0.0.1:4173')
  expect(config.webServer).toBeDefined()
})
