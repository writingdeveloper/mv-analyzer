import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'
import path from 'node:path'
const fixture=JSON.parse(readFileSync(path.resolve('e2e/fixtures/analyze-report.json'),'utf8'))
const reasonPath=path.resolve(process.cwd(),'../examples/demo-reason.json')

test('a loading heading is never treated as a ready research page',async({page})=>{
  let release!:()=>void
  const gate=new Promise<void>(resolve=>{release=resolve})
  await page.route('**/data/*.json',async route=>{await gate;await route.continue()})
  try{
    await page.goto('/?lang=en#/discover',{waitUntil:'domcontentloaded'})
    await expect(page.getByRole('heading',{name:'Loading research snapshot'})).toBeVisible()
    await expect(page.locator('main > .page')).toHaveCount(0)
    release()
    await expect(page.locator('.discover-page')).toBeVisible()
    await expect(page.locator('.standardized-visual-head').first()).toBeVisible()
  }finally{release();await page.unrouteAll({behavior:'wait'})}
})

test('sample result is usable without installation and is labeled as an in-corpus demo',async({page})=>{
  const errors:string[]=[]
  page.on('pageerror',e=>errors.push(e.message))
  await page.goto('/?lang=en#/analyze')
  await page.getByRole('button',{name:'Explore a sample report',exact:true}).click()
  await expect(page.locator('.analyze-demo-notice')).toContainText('already part of the reference')
  await expect(page.getByRole('heading',{name:/What the measurements actually support/})).toBeVisible()
  await expect(page.getByText('Why this claim?').first()).toBeVisible()
  await expect(page.getByRole('img',{name:'Your MV in the reference PCA space'})).toBeVisible()
  await page.getByRole('button',{name:'3D',exact:true}).click()
  const canvas=page.locator('.analyze-pca3d canvas')
  await expect(canvas).toBeVisible()
  const renderer=await canvas.evaluate(node=>{
    const gl=(node as HTMLCanvasElement).getContext('webgl2')!
    const info=gl.getExtension('WEBGL_debug_renderer_info')!
    return gl.getParameter(info.UNMASKED_RENDERER_WEBGL) as string
  })
  expect(renderer).toContain('SwiftShader')
  await page.getByRole('button',{name:'2D',exact:true}).click()
  await expect(page.locator('.analyze-pca3d canvas')).toHaveCount(0)
  await expect(page.locator('.analyze-projection')).toBeVisible()
  expect(errors).toEqual([])
})

test('local import sends no report data and reload clears the report',async({page})=>{
  await page.goto('/?lang=en#/analyze')
  await expect(page.locator('.analyze-page')).toBeVisible()
  const requests:Array<{url:string;method:string;body:string|null}>=[]
  page.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()}))
  const copy=structuredClone(fixture)
  copy.video.title='LOCAL_ONLY_MARKER_9c205'
  await page.getByLabel('Choose MV analysis report JSON').setInputFiles({name:'local.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(copy))})
  await expect(page.getByRole('heading',{name:copy.video.title})).toBeVisible()
  await expect(page.locator('.analyze-projection')).toBeVisible()
  expect(requests.filter(r=>!['GET','HEAD'].includes(r.method))).toEqual([])
  expect(JSON.stringify(requests)).not.toContain(copy.video.title)
  const storage=await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))
  expect(storage).not.toContain(copy.video.title)
  await page.reload()
  await expect(page.getByRole('heading',{name:/Analyze your MV locally/})).toBeVisible()
  await expect(page.getByRole('heading',{name:copy.video.title})).toHaveCount(0)
})

test('impossible numeric evidence and legacy reports are rejected without partial output',async({page})=>{
  await page.goto('/?lang=en#/analyze')
  const copy=structuredClone(fixture)
  copy.features[0].percentile=150
  await page.getByLabel('Choose MV analysis report JSON').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(copy))})
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.locator('.analyze-results')).toHaveCount(0)
  copy.schema_version=1
  await page.getByLabel('Choose MV analysis report JSON').setInputFiles({name:'legacy.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(copy))})
  await expect(page.getByRole('alert')).toContainText('v1')
})

test('calendar-only collection dates do not shift in Los Angeles',async({browser})=>{
  const context=await browser.newContext({timezoneId:'America/Los_Angeles',locale:'en-US'})
  try{
    const page=await context.newPage()
    await page.goto('/?lang=en#/analyze')
    await page.getByRole('button',{name:'Explore a sample report',exact:true}).click()
    await expect(page.locator('.analyze-context-list').first()).toContainText('Jul 16, 2026 – Jul 21, 2026')
  }finally{await context.close()}
})

test('sample JSON, social metadata and security headers are served',async({request})=>{
  const response=await request.get('/')
  expect(response.status()).toBe(200)
  const headers=response.headers()
  expect(headers['content-security-policy']).toContain("script-src 'self'")
  expect(headers['content-security-policy']).not.toContain("'unsafe-eval'")
  expect(headers['x-content-type-options']).toBe('nosniff')
  for(const file of ['robots.txt','sitemap.xml','site.webmanifest','icon.svg','social-card.png','favicon.ico','data/demo-report.json']){
    expect((await request.get('/'+file)).status(),file).toBe(200)
  }
})


test('portable Reason JSON opens locally without report upload or invented chart detail',async({page})=>{
  await page.goto('/?lang=en#/analyze')
  const requests:Array<{method:string;url:string;body:string|null}>=[]
  page.on('request',r=>requests.push({method:r.method(),url:r.url(),body:r.postData()}))
  await page.getByLabel('Choose MV analysis report JSON').setInputFiles(reasonPath)
  await expect(page.locator('.reason-only-results')).toBeVisible()
  await expect(page.getByRole('heading',{name:/What the measurements actually support/})).toBeVisible()
  await expect(page.getByText('Why this claim?').first()).toBeVisible()
  await expect(page.locator('.analyze-two-col')).toHaveCount(0)
  expect(requests.filter(r=>!['GET','HEAD'].includes(r.method))).toEqual([])
})
