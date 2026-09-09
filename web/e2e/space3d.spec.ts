import { expect, test } from '@playwright/test'

test('Data Constellation renders, controls toggle, and focus details stay readable', async ({ page }) => {
  const consoleErrors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  page.on('pageerror', (error) => consoleErrors.push(error.message))

  await page.goto('/?lang=ko#/space')
  await expect(page.getByRole('heading', { name: /100편의 MV를/ })).toBeVisible()
  await page.getByRole('button', { name: '3D' }).click()

  await expect(page.getByText('Data Constellation')).toBeVisible()
  const canvas = page.getByRole('img', { name: 'PCA 3D Data Constellation canvas' })
  await expect(canvas).toBeVisible()
  const box = await canvas.boundingBox()
  expect(box?.width ?? 0).toBeGreaterThan(300)
  expect(box?.height ?? 0).toBeGreaterThan(350)

  const renderedFrame = await canvas.evaluate((node) => (node as HTMLCanvasElement).toDataURL('image/png').length)
  expect(renderedFrame).toBeGreaterThan(2_000)

  await expect(page.getByRole('button', { name: '자동 회전 끄기' })).toBeVisible()
  await page.getByRole('button', { name: '자동 회전 끄기' }).click()
  await expect(page.getByRole('button', { name: '자동 회전 켜기' })).toBeVisible()

  await page.getByRole('button', { name: '이웃 연결 끄기' }).click()
  await expect(page.getByRole('button', { name: '이웃 연결 켜기' })).toBeVisible()
  await page.getByRole('button', { name: '뷰 초기화' }).click()

  await expect(page.getByText(/표시 좌표는 PC별 max-abs 정규화/)).toBeVisible()
  await expect(page.getByText(/Z-SCORED FEATURES/)).toBeVisible()
  await expect(page.locator('.constellation-toolbar').getByText(/raw PCA score/)).toBeVisible()
  expect(consoleErrors).toEqual([])
})

test('mobile 3D view stays inside the viewport without horizontal page overflow', async ({ page }) => {
  await page.goto('/?lang=ko#/space')
  await page.getByRole('button', { name: '3D' }).click()
  const canvas = page.getByRole('img', { name: 'PCA 3D Data Constellation canvas' })
  await expect(canvas).toBeVisible()

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(2)
})
