import type { FeatureMeta,VideoRow } from '../data/schema'
import { numericSeries,numericValue,percentileRank } from '../data/filters'
import { useLocale } from '../i18n/LocaleProvider'
import { featureLabel } from '../i18n/research'

export function PercentileBars({videos,reference,features}:{videos:VideoRow[];reference:VideoRow[];features:FeatureMeta[]}){
  const {locale,number}=useLocale()
  const chosen=features.filter(f=>f.kind==='numeric').map(f=>({f,values:videos.map(v=>numericValue(v,f.id))})).filter(x=>x.values.some(v=>v!==null)).slice(0,10)
  const fmt=(v:number|null)=>v==null?'–':number(v,{maximumFractionDigits:2})
  return <div className="percentile-list">{chosen.map(({f})=><div className="percentile-row" key={f.id}><div className="percentile-label"><b>{featureLabel(f,locale)}</b><code>{f.id}</code></div><div className="percentile-tracks">{videos.map(v=>{const raw=numericValue(v,f.id);const pct=raw==null?null:percentileRank(numericSeries(reference,f.id),raw);return <div className="percentile-item" key={v.video_id}><span>{v.title}</span><div className="percentile-track"><i className={v.group} style={{width:`${pct??0}%`}}/></div><small>{pct==null?'–':`${pct} percentile`} · {fmt(raw)}</small></div>})}</div></div>)}</div>
}
