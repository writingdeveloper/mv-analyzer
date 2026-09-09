import { expect, test } from '@playwright/test'

const routes = ['#/', '#/discover', '#/space', '#/compare', '#/analyze', '#/samples', '#/methodology'] as const

function collectErrors(page: import('@playwright/test').Page) {
  const errors: string[] = []
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
  page.on('pageerror', (error) => errors.push(error.message))
  return errors
}

test('browser language defaults to English outside Korean locales and Korean for ko-KR', async ({ browser }) => {
  const enContext = await browser.newContext({ locale: 'en-US' })
  const enPage = await enContext.newPage()
  await enPage.goto('/#/')
  await expect(enPage.locator('html')).toHaveAttribute('lang', 'en')
  await expect(enPage.getByRole('heading', { name: /How do high- and low-performing MVs/ })).toBeVisible()
  await enContext.close()

  const koContext = await browser.newContext({ locale: 'ko-KR' })
  const koPage = await koContext.newPage()
  await koPage.goto('/#/')
  await expect(koPage.locator('html')).toHaveAttribute('lang', 'ko')
  await expect(koPage.getByRole('heading', { name: /인기 극단의 MV는/ })).toBeVisible()
  await koContext.close()
})

test('query locale overrides browser preference in both directions', async ({ browser }) => {
  const enBrowser = await browser.newContext({ locale: 'en-US' })
  const enPage = await enBrowser.newPage()
  await enPage.goto('/?lang=ko#/discover')
  await expect(enPage.locator('html')).toHaveAttribute('lang', 'ko')
  await expect(enPage.getByRole('heading', { name: /Feature를 움직이면/ })).toBeVisible()
  await enBrowser.close()

  const koBrowser = await browser.newContext({ locale: 'ko-KR' })
  const koPage = await koBrowser.newPage()
  await koPage.goto('/?lang=en#/discover')
  await expect(koPage.locator('html')).toHaveAttribute('lang', 'en')
  await expect(koPage.getByRole('heading', { name: /Move a feature and/ })).toBeVisible()
  await koBrowser.close()
})

test('language switch preserves the hash route and saved choice survives a query-free navigation', async ({ page }) => {
  await page.goto('/?lang=ko#/space')
  await expect(page.locator('html')).toHaveAttribute('lang', 'ko')
  await page.getByRole('button', { name: '영어' }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await expect(page).toHaveURL(/\?lang=en#\/space$/)
  await expect(page.getByRole('heading', { name: /Place 100 music videos/ })).toBeVisible()
  expect(await page.evaluate(() => localStorage.getItem('mv-analyzer-locale'))).toBe('en')

  await page.goto('/#/space')
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await expect(page.getByRole('heading', { name: /Place 100 music videos/ })).toBeVisible()
})

test('all primary routes render in Korean and English without data errors', async ({ page }) => {
  const errors = collectErrors(page)
  for (const locale of ['ko', 'en'] as const) {
    for (const hash of routes) {
      await page.goto(`/?lang=${locale}${hash}`)
      await expect(page.locator('main > .page')).toBeVisible()
      await expect(page.locator('main > .page h1')).toBeVisible()
      await expect(page.locator('html')).toHaveAttribute('lang', locale)
      await expect(page.locator('main')).not.toContainText('DATA ERROR')
    }
  }
  expect(errors).toEqual([])
})

for (const viewport of [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 768, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
  { name: 'small-mobile', width: 320, height: 760 },
]) {
  test(`English portfolio layout has no page overflow at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    for (const hash of routes) {
      await page.goto(`/?lang=en${hash}`)
      await expect(page.locator('main > .page')).toBeVisible()
      await expect(page.locator('main > .page h1')).toBeVisible()
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
      expect(overflow, `${hash} overflow at ${viewport.width}px`).toBeLessThanOrEqual(2)
    }
  })
}

test('English Discover uses bilingual research labels and horizontal heatmap headers', async ({ page }) => {
  await page.goto('/?lang=en#/discover')
  await expect(page.getByRole('heading', { name: /Move a feature and/ })).toBeVisible()
  await page.getByLabel('X feature').selectOption('scene_cuts_per_minute')
  await expect(page.locator('.standardized-visual-head b').filter({ hasText: 'Cuts per minute' }).first()).toBeVisible()
  await expect(page.getByText(/Full 100-video reference/)).toBeVisible()
  await expect(page.getByText(/opposite direction/)).toBeVisible()
  const headerModes = await page.locator('.heatmap-table thead th').evaluateAll((nodes) => nodes.slice(1).map((node) => getComputedStyle(node).writingMode))
  expect(headerModes.every((mode) => mode === 'horizontal-tb')).toBe(true)
})

test('English Three.js Data Constellation renders with localized controls and zero console errors', async ({ page }) => {
  const errors = collectErrors(page)
  await page.goto('/?lang=en#/space')
  await page.getByRole('button', { name: '3D' }).click()
  await expect(page.getByRole('button', { name: 'Hide neighbor links' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Disable auto-rotate' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Reset view' })).toBeVisible()
  await expect(page.getByText(/Cuts per minute/).first()).toBeVisible()
  const canvas = page.getByRole('img', { name: 'PCA 3D Data Constellation canvas' })
  await expect(canvas).toBeVisible()
  const frame = await canvas.evaluate((node) => (node as HTMLCanvasElement).toDataURL('image/png').length)
  expect(frame).toBeGreaterThan(2_000)
  expect(errors).toEqual([])
})
