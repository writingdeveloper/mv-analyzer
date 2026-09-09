import { defineConfig, devices } from '@playwright/test'

const localPort = process.env.MVA_QA_PORT || '4173'
const localBaseURL = `http://127.0.0.1:${localPort}`
const remoteBaseURL = process.env.PLAYWRIGHT_BASE_URL?.replace(/\/+$/, '')
const baseURL = remoteBaseURL || localBaseURL

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 7_000 },
  fullyParallel: false,
  workers: 2,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL,
    launchOptions: { args: ['--disable-gpu','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'] },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: remoteBaseURL ? undefined : {
    command: `npm run build && npm run preview -- --port ${localPort} --strictPort`,
    url: localBaseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    { name: 'chromium-desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } } },
    { name: 'chromium-mobile', use: { ...devices['Pixel 5'] } },
  ],
})
