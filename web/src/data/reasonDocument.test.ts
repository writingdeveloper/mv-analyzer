import {describe,expect,test} from 'vitest'
import fixture from '../../e2e/fixtures/analyze-report.json'
import {deriveReasonDocument,parseReasonDocument,REASON_POLICY_ID,renderReasonClaim} from './reasonDocument'
import type {AnalyzeReport} from './analyzeReport'
const report=fixture as unknown as AnalyzeReport

describe('Reason Engine browser mirror',()=>{
 test('uses the same policy and source fingerprints',()=>{const r=deriveReasonDocument(report);expect(r.policy_id).toBe(REASON_POLICY_ID);expect(r.source_report.source_features_sha256).toBe(report.pipeline.source_features_sha256);expect(r.source_report.corpus_sha256).toBe(report.benchmark.corpus_sha256)})
 test('produces composed feel claims and does not promote near-median cut rate',()=>{const r=deriveReasonDocument(report);expect(r.summary.feel).toContain('feel:closeup-focus');expect(r.summary.feel).toContain('feel:event-dense-audio');expect(r.summary.distinctive.some(id=>id.includes('scene_cuts_per_minute'))).toBe(false);expect(JSON.stringify(r)).not.toContain('motion_scene_')})
 test('renders deterministic bilingual evidence text',()=>{const r=deriveReasonDocument(report);const c=r.claims.find(x=>x.question==='distinctive')!;expect(renderReasonClaim(c,'en')).toMatch(/reference corpus/i);expect(renderReasonClaim(c,'ko')).toMatch(/기준 코퍼스/);expect(renderReasonClaim(c,'en')).not.toMatch(/success probability/i)})
 test('report-only browser derivation has no personal taste claims',()=>{expect(deriveReasonDocument(report).summary.taste).toEqual([])})
 test('accepts its own portable reason document and rejects tampering',()=>{const reason=deriveReasonDocument(report);expect(parseReasonDocument(reason).kind).toBe('mv-analyzer-reason');expect(()=>parseReasonDocument({...reason,policy_id:'unknown'})).toThrow(/policy|schema/i);expect(()=>parseReasonDocument({...reason,local_path:'C:\\secret'})).toThrow(/unsafe|unexpected/i)})
})
