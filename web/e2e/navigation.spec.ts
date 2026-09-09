import { expect, test } from '@playwright/test'

const routes = [
  ['#/', 'Overview'],
  ['#/discover', 'Discover'],
  ['#/space', 'MV Space'],
  ['#/compare', 'Compare'],
  ['#/analyze', 'Analyze'],
  ['#/samples', 'Samples'],
  ['#/methodology', 'Methodology'],
] as const

test('all primary research pages render from the deployed hash-router contract', async ({ page }) => {
  const errors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  page.on('pageerror', (error) => errors.push(error.message))

  for (const [hash, label] of routes) {
    await page.goto(`/?lang=ko${hash}`)
    await expect(page.getByRole('link', { name: label })).toBeVisible()
    await expect(page.locator('main > .page')).toBeVisible()
      await expect(page.locator('main > .page h1')).toBeVisible()
    await expect(page.locator('main')).not.toContainText('데이터를 불러오지 못했습니다')
  }

  expect(errors).toEqual([])
})
