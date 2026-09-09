import { describe, expect, test } from 'vitest'
import fixture from '../../e2e/fixtures/analyze-report.json'
import { parseAnalyzeReport } from './analyzeReport'

describe('scientific report boundary regression', () => {
  test.each([
    ['percentile above 100', ['features',0,'percentile'],150],
    ['negative sample count', ['features',0,'reference_n'],-1],
    ['negative standard deviation', ['features',0,'reference_std'],-2],
    ['inconsistent z-score', ['features',0,'z'],987654],
    ['invalid coverage', ['centroids','coverage'],9],
    ['negative distance', ['neighbors',0,'distance'],-1],
    ['unknown corpus', ['benchmark','corpus_id'],'unknown-corpus'],
    ['impossible variance', ['pca','explained_variance_pct'],[200,-100,50]],
  ])('rejects %s', (_name,path,value) => {
    const r: any = structuredClone(fixture)
    const keys = path as (string | number)[]
    let node = r
    for (const key of keys.slice(0,-1)) node = node[key]
    node[keys.at(-1)!] = value
    expect(() => parseAnalyzeReport(r)).toThrow()
  })
  test.each(['empty','duplicate'])('rejects %s features', mode => {
    const r = structuredClone(fixture)
    r.features = mode === 'empty' ? [] : [...r.features, {...r.features[0]}]
    expect(() => parseAnalyzeReport(r)).toThrow()
  })
})
