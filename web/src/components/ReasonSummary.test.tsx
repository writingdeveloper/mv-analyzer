import {render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,expect,test} from 'vitest'
import fixture from '../../e2e/fixtures/analyze-report.json'
import type {AnalyzeReport} from '../data/analyzeReport'
import {deriveReasonDocument} from '../data/reasonDocument'
import {LocaleProvider} from '../i18n/LocaleProvider'
import {ReasonSummary} from './ReasonSummary'

beforeEach(()=>{localStorage.clear();window.history.replaceState({},'','/?lang=en')})
const renderReason=(lang='en')=>{window.history.replaceState({},'',`/?lang=${lang}`);return render(<LocaleProvider><MemoryRouter><ReasonSummary reason={deriveReasonDocument(fixture as unknown as AnalyzeReport)}/></MemoryRouter></LocaleProvider>)}

test('renders explanation first with auditable evidence disclosures',()=>{renderReason();expect(screen.getByRole('heading',{name:/What the measurements actually support/})).toBeInTheDocument();expect(screen.getAllByText('Why this claim?').length).toBeGreaterThan(0);expect(document.querySelectorAll('.reason-claim').length).toBeGreaterThanOrEqual(2);expect(screen.getByText(/No personal taste profile/)).toBeInTheDocument()})
test('renders Korean deterministic reason copy',()=>{renderReason('ko');expect(screen.getByRole('heading',{name:/측정값이 실제로 지지하는 이유/})).toBeInTheDocument();expect(screen.getAllByText('왜 이렇게 판단했나요?').length).toBeGreaterThan(0)})
