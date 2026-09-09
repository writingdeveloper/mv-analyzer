import type {ReasonClaim,ReasonDocument,ReasonEvidence} from '../data/reasonDocument'
import {renderReasonClaim} from '../data/reasonDocument'
import {useLocale} from '../i18n/LocaleProvider'

const copy={
 en:{kicker:'SO WHY?',title:'What the measurements actually support',body:'The explanation comes first; charts below are the evidence layer. Each claim can be opened to inspect the measurements behind it.',why:'Why this claim?',supported:'Supported pattern',contradicted:'Not supported by taste evidence',insufficient:'Not enough evidence yet',taste:'Why might I like it?',noTaste:'No personal taste profile was attached to this report.'},
 ko:{kicker:'그래서 왜?',title:'측정값이 실제로 지지하는 이유',body:'먼저 이유를 설명하고, 아래 차트는 그 이유를 검증하는 근거 계층으로 둡니다. 각 문장을 열면 어떤 측정값으로 판단했는지 확인할 수 있습니다.',why:'왜 이렇게 판단했나요?',supported:'근거가 있는 패턴',contradicted:'취향 근거에서 지지되지 않음',insufficient:'아직 근거 부족',taste:'내가 왜 좋아할 수 있나?',noTaste:'이 리포트에는 개인 취향 프로파일이 연결되지 않았습니다.'}
} as const

function Evidence({e}:{e:ReasonEvidence}){
 const {locale,number}=useLocale()
 const label=e.label?.[locale]||e.feature_id||String(e.favorite_value||e.kind)
 if(e.kind==='feature') return <li><b>{label}</b><span>{number(Number(e.value),{maximumFractionDigits:3})}</span><small>z {number(Number(e.z),{maximumFractionDigits:2})} · pct {number(Number(e.reference_percentile),{maximumFractionDigits:1})}</small></li>
 if(e.kind.startsWith('taste_profile')) return <li><b>{label}</b><span>{String(e.profile_verdict||'')}</span><small>n={String(e.n_favorites??'–')}</small></li>
 return <li><b>{label}</b><span>{e.kind}</span></li>
}

function ClaimCard({claim}:{claim:ReasonClaim}){
 const {locale}=useLocale(); const c=copy[locale]
 const status=claim.support==='supported'?c.supported:claim.support==='contradicted'?c.contradicted:c.insufficient
 return <article className={`reason-claim reason-${claim.support}`} data-claim-id={claim.id}><div className="reason-claim-head"><span className="status-badge">{status}</span><small>{claim.confidence.toUpperCase()}</small></div><p>{renderReasonClaim(claim,locale)}</p><details><summary>{c.why}</summary><ul>{claim.evidence.map((e,i)=><Evidence e={e} key={`${claim.id}-${i}`}/>)}</ul></details></article>
}

export function ReasonSummary({reason}:{reason:ReasonDocument}){
 const {locale}=useLocale(); const c=copy[locale]; const byId=new Map(reason.claims.map(claim=>[claim.id,claim]))
 const primary=[...reason.summary.feel,...reason.summary.distinctive].filter((id,i,a)=>a.indexOf(id)===i).slice(0,4).map(id=>byId.get(id)).filter(Boolean) as ReasonClaim[]
 const taste=reason.summary.taste.map(id=>byId.get(id)).filter(Boolean) as ReasonClaim[]
 return <section className="panel reason-summary" aria-labelledby="reason-heading"><div className="reason-intro"><span className="kicker">{c.kicker}</span><h2 id="reason-heading">{c.title}</h2><p>{c.body}</p></div><div className="reason-grid">{primary.map(claim=><ClaimCard claim={claim} key={claim.id}/>)}</div>{taste.length>0&&<div className="reason-taste"><h3>{c.taste}</h3><div className="reason-grid">{taste.map(claim=><ClaimCard claim={claim} key={claim.id}/>)}</div></div>}{taste.length===0&&<p className="reason-no-taste">{c.noTaste}</p>}</section>
}
