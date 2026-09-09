import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test } from 'vitest'
import { LocaleProvider } from '../i18n/LocaleProvider'
import { AnalyzePage } from './AnalyzePage'

import { testReport as validReport } from '../test/analyzeFixture'

function renderPage(lang:'en'|'ko'='en'){
  localStorage.clear()
  window.history.replaceState({},'',`/?lang=${lang}`)
  return render(<LocaleProvider><MemoryRouter><AnalyzePage/></MemoryRouter></LocaleProvider>)
}

async function importReport(report:unknown=validReport()){
  const input=screen.getByLabelText(/analysis report|분석 리포트/i) as HTMLInputElement
  const file=new File([JSON.stringify(report)],'my-mv.json',{type:'application/json'})
  Object.defineProperty(file,'text',{value:async()=>JSON.stringify(report)})
  fireEvent.change(input,{target:{files:[file]}})
  await screen.findByRole('heading',{name:/^Example MV$/})
}

beforeEach(()=>{localStorage.clear();window.history.replaceState({},'','/?lang=en')})

test('shows local-only instructions before import',()=>{
  renderPage('en')
  expect(screen.getByRole('heading',{name:/Analyze your MV locally/i})).toBeInTheDocument()
  expect(screen.getByText(/mva analyze .*--web-report my-mv\.json/i)).toBeInTheDocument()
  expect(screen.getByText(/not uploaded/i)).toBeInTheDocument()
})

test('imports a valid report and renders neutral benchmark evidence',async()=>{
  renderPage('en')
  await importReport()

  expect(screen.getByText('Extreme Reference Corpus v2026.07')).toBeInTheDocument()
  expect(screen.getByText(/Descriptive benchmark · not a prediction of success/i)).toBeInTheDocument()
  expect(screen.getByText('Cuts per minute')).toBeInTheDocument()
  expect(screen.getAllByText(/Reference percentile/).length).toBeGreaterThan(0)
  expect(screen.getAllByText('z').length).toBeGreaterThan(0)
  expect(screen.getAllByText('Raw value').length).toBeGreaterThan(0)
  expect(screen.getByText('Neighbor MV')).toBeInTheDocument()
  expect(screen.getByText(/Closer to the top-group centroid/i)).toBeInTheDocument()
  expect(screen.getByText(`PC1 ${validReport().pca.score![0].toFixed(3)}`)).toBeInTheDocument()
  expect(screen.queryByText(/^Good$/i)).not.toBeInTheDocument()
  expect(screen.queryByText(/^Bad$/i)).not.toBeInTheDocument()
  expect(screen.queryByText(/^Success probability$/i)).not.toBeInTheDocument()
})

test('invalid report shows an error without partial result',async()=>{
  renderPage('en')
  const input=screen.getByLabelText(/analysis report/i)
  const file=new File(['{"kind":"wrong"}'],'bad.json',{type:'application/json'})
  Object.defineProperty(file,'text',{value:async()=>'{"kind":"wrong"}'})
  fireEvent.change(input,{target:{files:[file]}})

  expect(await screen.findByRole('alert')).toHaveTextContent(/schema|report/i)
  expect(screen.queryByText('Example MV')).not.toBeInTheDocument()
})

test('clear report returns to the landing state',async()=>{
  renderPage('en')
  await importReport()
  fireEvent.click(screen.getByRole('button',{name:/clear report/i}))
  expect(screen.getByRole('heading',{name:/Analyze your MV locally/i})).toBeInTheDocument()
  expect(screen.queryByText('Example MV')).not.toBeInTheDocument()
})

test('renders Korean copy and feature label',async()=>{
  renderPage('ko')
  expect(screen.getByRole('heading',{name:/내 MV를 로컬에서 분석/i})).toBeInTheDocument()
  const input=screen.getByLabelText(/분석 리포트/i) as HTMLInputElement
  const report=validReport()
  const file=new File([JSON.stringify(report)],'my-mv.json',{type:'application/json'})
  Object.defineProperty(file,'text',{value:async()=>JSON.stringify(report)})
  fireEvent.change(input,{target:{files:[file]}})
  await waitFor(()=>expect(screen.getByText('분당 컷 수')).toBeInTheDocument())
  expect(screen.getByText(/성공 예측이 아닙니다/)).toBeInTheDocument()
})


test('cancel invalidates an in-flight local file read',async()=>{
  renderPage('en')
  let finish!:(text:string)=>void
  const promise=new Promise<string>(resolve=>{finish=resolve})
  const file=new File(['pending'],'pending.json',{type:'application/json'})
  Object.defineProperty(file,'text',{value:()=>promise})
  fireEvent.change(screen.getByLabelText(/analysis report/i),{target:{files:[file]}})
  fireEvent.click(screen.getByRole('button',{name:'Cancel import'}))
  await act(async()=>{finish(JSON.stringify(validReport()));await promise})
  expect(screen.queryByRole('heading',{name:/^Example MV$/})).not.toBeInTheDocument()
  expect(screen.getByRole('heading',{name:/Analyze your MV locally/})).toBeInTheDocument()
})


test('imports a portable reason document directly and shows explanation-only results',async()=>{
  renderPage('en')
  const {deriveReasonDocument}=await import('../data/reasonDocument')
  const reason=deriveReasonDocument(validReport() as never)
  const input=screen.getByLabelText(/analysis report/i) as HTMLInputElement
  const file=new File([JSON.stringify(reason)],'my-reason.json',{type:'application/json'})
  Object.defineProperty(file,'text',{value:async()=>JSON.stringify(reason)})
  fireEvent.change(input,{target:{files:[file]}})
  await screen.findByText('Example MV')
  expect(screen.getByRole('heading',{name:/What the measurements actually support/})).toBeInTheDocument()
  expect(screen.queryByText(/PCA POSITION/)).not.toBeInTheDocument()
})
