import { expect, test } from '@playwright/test'

for (const viewport of [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 768, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`Discover contains wide research visuals on ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.goto('/?lang=ko#/discover')
    await expect(page.getByRole('heading', { name: /Feature를 움직이면/ })).toBeVisible()

    const layout = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      writingModes: [...document.querySelectorAll('.heatmap-table thead th')].slice(1).map((node) => getComputedStyle(node).writingMode),
    }))

    expect(layout.overflow).toBeLessThanOrEqual(2)
    expect(layout.writingModes.every((mode) => mode === 'horizontal-tb')).toBe(true)
  })
}
