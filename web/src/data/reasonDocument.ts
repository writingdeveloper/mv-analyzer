import type { AnalyzeFeature, AnalyzeReport } from './analyzeReport'

export const REASON_POLICY_ID='reason-v1-z075-tail20-compose-v1'
const Z=0.75, HIGH=80, LOW=20

export type ReasonQuestion='distinctive'|'feel'|'taste'
export type ReasonSupport='supported'|'contradicted'|'insufficient'
export type ReasonConfidence='high'|'medium'|'low'
export interface ReasonEvidence { kind:string; feature_id?:string; label?:{ko:string;en:string}; value?:number; z?:number; reference_percentile?:number; reference_median?:number; [key:string]:unknown }
export interface ReasonClaim { id:string; question:ReasonQuestion; claim_type:string; subject:string; direction:'high'|'low'|'mixed'|'match'|'none'; support:ReasonSupport; confidence:ReasonConfidence; scope:'reference_corpus'|'taste_profile'|'timeline'|'measurement_quality'; text_key:string; evidence:ReasonEvidence[] }
export interface ReasonDocument { schema_version:1; kind:'mv-analyzer-reason'; policy_id:string; generated_at:string; video:{video_id:string;title:string;channel:string}; source_report:{schema_version:2;source_features_sha256:string;corpus_sha256:string;benchmark_domain:'all'|'vocaloid'|'kpop'}; summary:{distinctive:string[];feel:string[];taste:string[]}; claims:ReasonClaim[]; limits:string[] }

const allowed=(f:AnalyzeFeature)=>!f.id.startsWith('motion_scene_')
const featureEvidence=(f:AnalyzeFeature):ReasonEvidence=>({kind:'feature',feature_id:f.id,label:f.labels,value:f.value,z:f.z,reference_percentile:f.percentile,reference_median:f.reference_median})
const distinctive=(f:AnalyzeFeature)=>Math.abs(f.z)>=Z||f.percentile>=HIGH||f.percentile<=LOW
const strength=(f:AnalyzeFeature)=>Math.max(Math.abs(f.z),Math.abs(f.percentile-50)/25)
const confidence=(f:AnalyzeFeature):ReasonConfidence=>Math.abs(f.z)>=1||f.percentile>=90||f.percentile<=10?'high':'medium'

function distinctiveClaims(report:AnalyzeReport):ReasonClaim[]{
  return report.features.filter(f=>allowed(f)&&distinctive(f)).sort((a,b)=>strength(b)-strength(a)||a.id.localeCompare(b.id)).map(f=>{
    const direction:'high'|'low'=f.z>0||f.percentile>50?'high':'low'
    return {id:`distinctive:${f.id}:${direction}`,question:'distinctive',claim_type:'descriptive_difference',subject:f.category,direction,support:'supported',confidence:confidence(f),scope:'reference_corpus',text_key:`reason.feature.${direction}`,evidence:[featureEvidence(f)]}
  })
}

const composition=(id:string,subject:string,text_key:string,rows:AnalyzeFeature[],level:ReasonConfidence='medium'):ReasonClaim=>({id,question:'feel',claim_type:'measured_composition',subject,direction:'mixed',support:'supported',confidence:level,scope:'reference_corpus',text_key,evidence:rows.map(featureEvidence)})
function feelClaims(report:AnalyzeReport):ReasonClaim[]{
  const f=new Map(report.features.filter(allowed).map(x=>[x.id,x]))
  const out:ReasonClaim[]=[]
  const close=f.get('tag_closeup_ratio'),wide=f.get('tag_wide_ratio'); if(close&&wide&&close.z>=.6&&wide.z<=-.6)out.push(composition('feel:closeup-focus','visual framing','reason.feel.closeup_focus',[close,wide]))
  const onsets=f.get('audio_onsets_per_sec'),peak=f.get('audio_peak_energy_ratio'); if(onsets&&peak&&onsets.z>=.75&&peak.z>=.75)out.push(composition('feel:event-dense-audio','audio intensity','reason.feel.event_dense_audio',[onsets,peak],'high'))
  const hook=f.get('hook_cuts_first_15s'),first=f.get('sync_first_cut_s'); if(hook&&first&&hook.z>=.75&&first.percentile<=20)out.push(composition('feel:front-loaded-opening','opening hook','reason.feel.front_loaded',[hook,first],'high'))
  const cpm=f.get('scene_cuts_per_minute'),shot=f.get('scene_median_shot_len_s'); if(cpm&&shot&&cpm.z>=.5&&shot.z<=-.5)out.push(composition('feel:rapid-pacing','editing rhythm','reason.feel.rapid_pacing',[cpm,shot]))
  const sat=f.get('scene_avg_saturation'),bright=f.get('scene_avg_brightness'); if(sat&&bright&&sat.z>=.6&&bright.z>=.6)out.push(composition('feel:vivid-visuals','visual appearance','reason.feel.vivid_visuals',[sat,bright]))
  return out
}

export function deriveReasonDocument(report:AnalyzeReport):ReasonDocument{
  const d=distinctiveClaims(report),f=feelClaims(report)
  return {schema_version:1,kind:'mv-analyzer-reason',policy_id:REASON_POLICY_ID,generated_at:report.generated_at,video:{video_id:report.video.video_id,title:report.video.title,channel:report.video.channel},source_report:{schema_version:2,source_features_sha256:report.pipeline.source_features_sha256,corpus_sha256:report.benchmark.corpus_sha256,benchmark_domain:report.benchmark.domain},summary:{distinctive:d.slice(0,4).map(c=>c.id),feel:f.slice(0,4).map(c=>c.id),taste:[]},claims:[...d,...f],limits:['descriptive-reference-only','not-a-success-prediction']}
}

const label=(e:ReasonEvidence,locale:'ko'|'en')=>e.label?.[locale]||e.feature_id||'feature'
export function renderReasonClaim(claim:ReasonClaim,locale:'ko'|'en'){
  const first=claim.evidence.find(e=>e.kind==='feature')||claim.evidence[0],name=label(first,locale),key=claim.text_key
  if(key==='reason.feature.high'||key==='reason.feature.low'){const dir=key.endsWith('high');return locale==='ko'?`${name}은(는) 이 기준 코퍼스에서 상대적으로 ${dir?'높습니다':'낮습니다'} (기준 코퍼스 백분위 ${Number(first.reference_percentile).toFixed(1)}).`:`${name} is relatively ${dir?'high':'low'} in this reference corpus (reference percentile ${Number(first.reference_percentile).toFixed(1)}).`}
  const text:Record<string,{ko:string;en:string}>={
    'reason.feel.closeup_focus':{ko:'화면 구성은 와이드 샷보다 클로즈업 쪽으로 기울어 있습니다.',en:'The visual framing leans toward close-ups rather than wide shots.'},
    'reason.feel.event_dense_audio':{ko:'오디오는 사건 밀도가 높은 편입니다. 온셋 활동과 피크 에너지 집중도가 함께 높습니다.',en:'The audio feels event-dense: onset activity and peak-energy concentration are both elevated.'},
    'reason.feel.front_loaded':{ko:'도입부가 앞쪽에 집중되어 있습니다. 첫 15초 컷이 많고 첫 컷도 이르게 등장합니다.',en:'The opening is front-loaded: it cuts frequently in the first 15 seconds and the first cut arrives early.'},
    'reason.feel.rapid_pacing':{ko:'시각적 페이스가 빠릅니다. 컷이 잦고 일반적인 샷 길이가 짧습니다.',en:'The visual pacing is rapid: cuts are frequent and typical shots are short.'},
    'reason.feel.vivid_visuals':{ko:'채도와 밝기가 함께 높아 시각적으로 선명한 인상을 만듭니다.',en:'The visual presentation is vivid, with both saturation and brightness elevated.'}
  }
  return text[key]?.[locale]||key
}


export class ReasonDocumentValidationError extends Error {
  constructor(public readonly code:'schema'|'unsafe'|'inconsistent',detail:string){super(detail);this.name='ReasonDocumentValidationError'}
}
const unsafeReasonKeys=new Set(['lyrics','raw_lyrics','lyrics_lines','lyrics_ocr','thumb_text_content','local_path','cookies','headers','vlm_prompt','vlm_response','media_url','video_url','__proto__','constructor','prototype'])
function record(v:unknown):v is Record<string,unknown>{return typeof v==='object'&&v!==null&&!Array.isArray(v)}
function scanReason(v:unknown,depth=0):void{
 if(depth>16)throw new ReasonDocumentValidationError('unsafe','unsafe nesting depth')
 if(Array.isArray(v)){if(v.length>1000)throw new ReasonDocumentValidationError('unsafe','unsafe array size');v.forEach(x=>scanReason(x,depth+1));return}
 if(record(v)){for(const [k,x] of Object.entries(v)){if(unsafeReasonKeys.has(k))throw new ReasonDocumentValidationError('unsafe','unsafe reason key');scanReason(x,depth+1)};return}
 if(typeof v==='number'&&!Number.isFinite(v))throw new ReasonDocumentValidationError('schema','non-finite number')
 if(typeof v==='string'&&(/\b[A-Za-z]:[\\/]|\\\\|(?:^|\s)\/(?:home|Users|tmp|var|mnt|etc|root|private|opt)\//i.test(v)||/file:\/\/|https?:\/\/|localhost|googlevideo\.com/i.test(v)))throw new ReasonDocumentValidationError('unsafe','local path or URL in reason')
}
function exactKeys(v:Record<string,unknown>,allowed:string[],path:string){const a=new Set(allowed);for(const k of Object.keys(v))if(!a.has(k))throw new ReasonDocumentValidationError('schema',`unexpected ${path}.${k}`)}
export function parseReasonDocument(value:unknown):ReasonDocument{
 scanReason(value);if(!record(value))throw new ReasonDocumentValidationError('schema','reason must be object')
 exactKeys(value,['schema_version','kind','policy_id','generated_at','video','source_report','summary','claims','limits'],'reason')
 if(value.schema_version!==1||value.kind!=='mv-analyzer-reason'||value.policy_id!==REASON_POLICY_ID)throw new ReasonDocumentValidationError('schema','unsupported reason schema or policy')
 if(!record(value.video)||!record(value.source_report)||!record(value.summary)||!Array.isArray(value.claims)||!Array.isArray(value.limits))throw new ReasonDocumentValidationError('schema','invalid reason structure')
 const src=value.source_report as Record<string,unknown>; if(src.schema_version!==2||!['all','vocaloid','kpop'].includes(String(src.benchmark_domain)))throw new ReasonDocumentValidationError('schema','invalid source report identity')
 for(const h of [src.source_features_sha256,src.corpus_sha256])if(typeof h!=='string'||!/^[0-9a-f]{64}$/.test(h))throw new ReasonDocumentValidationError('schema','invalid source fingerprint')
 const claims=value.claims as unknown[];const ids=new Set<string>();for(const raw of claims){if(!record(raw)||typeof raw.id!=='string'||!['distinctive','feel','taste'].includes(String(raw.question))||!['supported','contradicted','insufficient'].includes(String(raw.support))||!Array.isArray(raw.evidence)||raw.evidence.length===0)throw new ReasonDocumentValidationError('schema','invalid claim');if(ids.has(raw.id))throw new ReasonDocumentValidationError('inconsistent','duplicate claim id');ids.add(raw.id)}
 for(const key of ['distinctive','feel','taste']){const arr=(value.summary as Record<string,unknown>)[key];if(!Array.isArray(arr)||arr.some(id=>typeof id!=='string'||!ids.has(id)))throw new ReasonDocumentValidationError('inconsistent','invalid summary claim reference')}
 return value as unknown as ReasonDocument
}
