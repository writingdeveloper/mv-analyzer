import validateSchema from './reportValidator.mjs'

export const MAX_ANALYZE_REPORT_BYTES = 2_000_000

export type AnalyzeDomain = 'all' | 'vocaloid' | 'kpop'
export type AnalyzeGroup = 'top' | 'bottom'

export interface AnalyzeFeature {
  id: string
  labels: { ko: string; en: string }
  category: string
  value: number
  z: number
  percentile: number
  reference_median: number
  reference_mean: number
  reference_std: number
  reference_n: number
}

export interface AnalyzeNeighbor {
  video_id: string
  title: string
  channel: string
  domain: Exclude<AnalyzeDomain, 'all'>
  group: AnalyzeGroup
  distance: number
}

export interface AnalyzeReport {
  schema_version: 2
  kind: 'mv-analyzer-report'
  generated_at: string
  pipeline: { version: string; git_commit: string; feature_schema: string; source_features_sha256: string;
    measurement_git_commit: string | null; measurement_status: 'recorded' | 'unverified' }
  video: { video_id: string; title: string; channel: string; upload_date: string | null; duration_s: number | null }
  benchmark: {
    corpus_id: string
    label: string
    sampling: string
    domain: AnalyzeDomain
    n: number
    collected_at: string
    collection_start: string
    collection_end: string
    corpus_sha256: string
    target_in_reference: boolean
    warning: 'descriptive-reference-only'
  }
  features: AnalyzeFeature[]
  pca: {
    status: 'available' | 'insufficient_coverage'; features: string[];
    score: [number,number,number] | null; display: [number,number,number] | null;
    explained_variance_pct: [number,number,number]; observed_count: number; coverage: number;
    imputed_features: string[]; experimental_features: string[]; basis_id: string;
    reference_points: Array<{ video_id:string; title:string; domain:'vocaloid'|'kpop'; group:AnalyzeGroup; score:[number,number,number]; display:[number,number,number] }>
  }
  neighbors: AnalyzeNeighbor[]
  centroids: { top_distance: number | null; bottom_distance: number | null; closer_group: AnalyzeGroup | null; coverage: number }
}


export class ReportValidationError extends Error {
  constructor(public readonly code: 'legacy' | 'schema' | 'unsafe' | 'inconsistent' | 'corpus', detail: string) {
    super(detail)
    this.name = 'ReportValidationError'
  }
}

const unsafeKeys = new Set(['lyrics','raw_lyrics','lyrics_lines','lyrics_ocr','thumb_text_content','formats',
  'requested_formats','local_path','cookies','cookie','headers','request_headers','vlm_prompt','vlm_response',
  'media_url','video_url','__proto__','constructor','prototype'])

function privateIp(text: string): boolean {
  return (text.match(/(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)/g) ?? []).some(token => {
    const [a,b,c] = token.split('.').map(Number)
    if (token.split('.').some(v => Number(v)>255)) return false
    return a===0 || a===10 || a===127 || a>=224 || (a===100&&b>=64&&b<=127) ||
      (a===169&&b===254) || (a===172&&b>=16&&b<=31) ||
      (a===192&&(b===168 || b===0 || (b===88&&c===99))) ||
      (a===198&&(b===18||b===19||(b===51&&c===100))) || (a===203&&b===0&&c===113)
  })
}

function scanSafety(value: unknown, depth=0): void {
  if(depth>16) throw new ReportValidationError('unsafe','unsafe report nesting depth')
  if(Array.isArray(value)) {
    if(value.length>1000) throw new ReportValidationError('unsafe','unsafe report array size')
    value.forEach(item=>scanSafety(item,depth+1)); return
  }
  if(typeof value==='object'&&value!==null) {
    for(const [key,item] of Object.entries(value)) {
      if(unsafeKeys.has(key)) throw new ReportValidationError('unsafe','unsafe report key')
      scanSafety(item,depth+1)
    }
  } else if(typeof value==='number'&&!Number.isFinite(value)) {
    throw new ReportValidationError('schema','report numbers must be finite')
  } else if(typeof value==='string') {
    if(/\b[A-Za-z]:[\\/]|\\\\|(?:^|\s)\/(?:home|Users|tmp|var|mnt|etc|root|private|opt)\//i.test(value)||value.toLowerCase().includes('file://'))
      throw new ReportValidationError('unsafe','local path in report')
    if(/https?:\/\/|localhost|googlevideo\.com/i.test(value)||privateIp(value)||/(?:^|[\s\[])(?:(?:fc|fd)[0-9a-f]{2}:|fe[89ab][0-9a-f]:|::1(?:\]|$))/i.test(value))
      throw new ReportValidationError('unsafe','private or signed/media URL in report')
  }
}

const close=(a:number,b:number)=>Math.abs(a-b)<=Math.max(1e-5,Math.max(Math.abs(a),Math.abs(b))*1e-6)
function ensure(condition:boolean,detail:string):asserts condition {
  if(!condition) throw new ReportValidationError('inconsistent',detail)
}

export function parseAnalyzeReport(value: unknown): AnalyzeReport {
  scanSafety(value)
  if(typeof value==='object'&&value!==null&&'schema_version' in value&&value.schema_version===1)
    throw new ReportValidationError('legacy','Legacy schema v1: regenerate using mva report-export.')
  if(!validateSchema(value)) {
    const issue=validateSchema.errors?.[0]
    if(issue?.instancePath.startsWith('/benchmark')&&['const','enum'].includes(issue.keyword))
      throw new ReportValidationError('corpus','unsupported corpus identity or fingerprint')
    const detail=issue?.keyword==='additionalProperties' ? 'unexpected report key' :
      `invalid report ${issue?.instancePath||''} ${issue?.params.missingProperty||''}: ${issue?.message||'schema'}`
    throw new ReportValidationError('schema',detail)
  }
  const r=value as AnalyzeReport
  ensure(new Set(r.features.map(f=>f.id)).size===r.features.length,'duplicate feature id')
  for(const f of r.features) {
    ensure(f.reference_n<=r.benchmark.n,'feature reference_n exceeds corpus n')
    ensure(close(f.z,(f.value-f.reference_mean)/f.reference_std),'inconsistent feature z-score')
  }
  const p=r.pca
  ensure(p.explained_variance_pct.reduce((a,b)=>a+b,0)<=100.02,'invalid PCA variance sum')
  ensure([...p.imputed_features,...p.experimental_features].every(f=>p.features.includes(f)),'invalid PCA feature policy')
  ensure(p.observed_count===p.features.length-p.imputed_features.length,'invalid PCA observed_count')
  ensure(close(p.coverage,p.observed_count/p.features.length),'invalid PCA coverage')
  const ids=p.reference_points.map(point=>point.video_id)
  ensure(ids.length===r.benchmark.n&&new Set(ids).size===ids.length,'invalid PCA reference population')
  ensure(r.benchmark.target_in_reference===ids.includes(r.video.video_id),'inconsistent target reference membership')
  const neighbors=r.neighbors.map(item=>item.video_id)
  ensure(new Set(neighbors).size===neighbors.length&&!neighbors.includes(r.video.video_id),'invalid duplicate/self neighbors')
  ensure(neighbors.every(id=>ids.includes(id)),'neighbor is outside the declared corpus')
  ensure(r.benchmark.domain==='all'||[...p.reference_points,...r.neighbors].every(item=>item.domain===r.benchmark.domain),'mixed report domain')
  const c=r.centroids
  ensure(c.coverage>=0.6||(!r.neighbors.length&&c.top_distance===null&&c.bottom_distance===null&&c.closer_group===null),'insufficient distance coverage')
  if(c.closer_group) {
    ensure(c.top_distance!==null&&c.bottom_distance!==null,'missing centroid distance')
    ensure(c.closer_group==='top'?c.top_distance<=c.bottom_distance:c.bottom_distance<=c.top_distance,'inconsistent centroid group')
  }
  ensure((r.pipeline.measurement_status==='recorded')===(r.pipeline.measurement_git_commit!==null),'inconsistent measurement provenance')
  ensure(Number.isFinite(Date.parse(r.generated_at)),'invalid generated_at date')
  const day=r.video.upload_date?.replace(/-/g,'')
  if(day) {
    const iso=`${day.slice(0,4)}-${day.slice(4,6)}-${day.slice(6,8)}`
    const date=new Date(`${iso}T00:00:00Z`)
    ensure(Number.isFinite(date.getTime())&&date.toISOString().slice(0,10)===iso,'invalid upload calendar date')
  }
  return r
}
