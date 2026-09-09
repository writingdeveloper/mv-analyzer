import { describe, expect, test } from 'vitest'
import { MAX_ANALYZE_REPORT_BYTES, parseAnalyzeReport } from './analyzeReport'

import { testReport as validReport } from '../test/analyzeFixture'

describe('parseAnalyzeReport',()=>{
  test('accepts the current safe report schema',()=>{
    const report=parseAnalyzeReport(validReport())
    expect(report.kind).toBe('mv-analyzer-report')
    expect(report.video.title).toBe('Example MV')
    expect(report.features[0].percentile).toBe(validReport().features[0].percentile)
  })

  test('rejects wrong kind and future schema',()=>{
    expect(()=>parseAnalyzeReport({...validReport(),kind:'other'})).toThrow(/kind/i)
    expect(()=>parseAnalyzeReport({...validReport(),schema_version:999})).toThrow(/schema/i)
  })

  test('rejects missing identity and malformed numeric rows',()=>{
    const missing=validReport(); delete (missing.video as Partial<typeof missing.video>).video_id
    expect(()=>parseAnalyzeReport(missing)).toThrow(/video_id/i)
    const malformed=validReport(); malformed.features[0].z=Number.NaN
    expect(()=>parseAnalyzeReport(malformed)).toThrow(/finite/i)
  })

  test.each([
    ['raw lyric key',{raw_lyrics:'text'}],
    ['thumbnail OCR key',{thumb_text_content:'text'}],
    ['windows path',{note:'C:\\Users\\name\\secret.json'}],
    ['file URL',{note:'file:///tmp/video.mp4'}],
    ['localhost',{note:'http://localhost:11434'}],
    ['private IP',{note:'http://192.168.1.5/internal'}],
    ['signed media',{note:'https://r1---sn.googlevideo.com/videoplayback?expire=1&sig=abc'}],
  ])('rejects unsafe content: %s',(_name,extra)=>{
    expect(()=>parseAnalyzeReport({...validReport(),...extra})).toThrow(/unsafe|unexpected|local|private|signed/i)
  })

  test('rejects unrelated extra keys even when their values look safe',()=>{
    expect(()=>parseAnalyzeReport({...validReport(),debug:'safe-looking'})).toThrow(/unexpected/i)
  })

  test('uses a bounded local file size',()=>{
    expect(MAX_ANALYZE_REPORT_BYTES).toBe(2_000_000)
  })
})
