import { expect, test, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'
import path from 'node:path'

const fixturePath = path.resolve(process.cwd(), 'e2e/fixtures/analyze-report.json')
const fixture = JSON.parse(readFileSync(fixturePath, 'utf-8')) as {
  video:{title:string}
  benchmark:{label:string}
  features:Array<{labels:{en:string}}>
  neighbors:Array<{title:string}>
}

function collectErrors(page: Page) {
  const errors: string[] = []
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
  page.on('pageerror', error => errors.push(error.message))
  return errors
}

async function importFixture(page: Page) {
  await page.getByLabel('Choose MV analysis report JSON').setInputFiles(fixturePath)
  await expect(page.getByRole('heading', { name: fixture.video.title })).toBeVisible()
}

test('Analyze imports a real safe Python report and renders neutral benchmark evidence', async ({ page }) => {
  const errors = collectErrors(page)
  await page.goto('/?lang=en#/analyze')
  await expect(page.getByRole('heading', { name: /Analyze your MV locally/ })).toBeVisible()
  await expect(page.getByText(/file is not uploaded/i)).toBeVisible()

  await importFixture(page)
  const reasonHeading=page.getByRole('heading',{name:/What the measurements actually support/})
  await expect(reasonHeading).toBeVisible()
  await expect(page.getByText('Why this claim?').first()).toBeVisible()
  const ordering=await page.evaluate(()=>{const reason=document.querySelector('.reason-summary'),details=document.querySelector('.analyze-two-col');return Boolean(reason&&details&&reason.compareDocumentPosition(details)&Node.DOCUMENT_POSITION_FOLLOWING)})
  expect(ordering).toBe(true)

  await expect(page.getByText(fixture.benchmark.label)).toBeVisible()
  await expect(page.getByText(/Descriptive benchmark · not a prediction of success/i)).toBeVisible()
  await expect(page.getByText(fixture.features[0].labels.en)).toBeVisible()
  await expect(page.getByText(/Reference percentile/i).first()).toBeVisible()
  await expect(page.locator('.analyze-neighbors a').filter({hasText:fixture.neighbors[0].title})).toBeVisible()
  await expect(page.getByText(/centroid in this reference sample/i)).toBeVisible()
  await expect(page.locator('.analyze-pca-coords b').first()).toBeVisible()
  expect(errors).toEqual([])
})

test('Analyze rejects malformed input without leaking partial result', async ({ page }) => {
  await page.goto('/?lang=en#/analyze')
  await page.getByLabel('Choose MV analysis report JSON').setInputFiles({
    name: 'bad.json',
    mimeType: 'application/json',
    buffer: Buffer.from('{"schema_version":1,"kind":"wrong","video":{"title":"SHOULD NOT RENDER"}}'),
  })
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByText('SHOULD NOT RENDER')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: /Analyze your MV locally/ })).toBeVisible()
})

test('Analyze language switch works before and after a local import and clear resets memory state', async ({ page }) => {
  await page.goto('/?lang=ko#/analyze')
  await expect(page.getByRole('heading', { name: /내 MV를 로컬에서 분석/ })).toBeVisible()
  await page.getByRole('button', { name: '영어' }).click()
  await expect(page.getByRole('heading', { name: /Analyze your MV locally/ })).toBeVisible()
  await importFixture(page)
  await page.getByRole('button', { name: 'Korean' }).click()
  await expect(page.getByText(/설명적 벤치마크 · 성공 예측이 아닙니다/)).toBeVisible()
  await page.getByRole('button', { name: /리포트 지우기/ }).click()
  await expect(page.getByRole('heading', { name: /내 MV를 로컬에서 분석/ })).toBeVisible()
  await expect(page.getByRole('heading', { name: fixture.video.title })).toHaveCount(0)
})

for (const viewport of [
  { name: 'desktop', width: 1440, height: 1000 },
  { name: 'tablet', width: 768, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
  { name: 'small-mobile', width: 320, height: 760 },
]) {
  test(`Analyze has no page overflow after report import at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.goto('/?lang=en#/analyze')
    await importFixture(page)
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow, `Analyze overflow at ${viewport.width}px`).toBeLessThanOrEqual(2)
  })
}
