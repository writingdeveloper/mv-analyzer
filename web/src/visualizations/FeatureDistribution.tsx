import type { VideoRow } from '../data/schema'
import { numericSeries, numericValue } from '../data/filters'
import { describeStandardizedValue, standardize } from '../data/normalization'
import { useLocale } from '../i18n/LocaleProvider'

const clampZ=(z:number)=>Math.max(-3,Math.min(3,z))
const signed=(value:number)=>`${value>=0?'+':''}${value.toFixed(2)}`
type Standardized = ReturnType<typeof describeStandardizedValue>
type DistributionPoint = {v:VideoRow;stats:Standardized}

export function FeatureDistribution({videos,reference,feature,label,onSelect}:{videos:VideoRow[];reference:VideoRow[];feature:string;label?:string;onSelect:(v:VideoRow)=>void}){
  const {t,number}=useLocale()
  const referenceValues=numericSeries(reference,feature)
  const ref=standardize(referenceValues,referenceValues[0]??0)
  const pts=videos.map(v=>{const raw=numericValue(v,feature);return raw===null?null:{v,stats:describeStandardizedValue(referenceValues,raw)}}).filter((p):p is DistributionPoint=>p!==null)
  const fmt=(v:number)=>number(v,{maximumFractionDigits:2})
  if(!pts.length)return <div className="empty-state">{t('chart.distributionEmpty')}</div>
  return <div className="distribution standardized-distribution" aria-label={`${label??feature} ${t('chart.standardizedZ')}`}>
    <div className="standardized-visual-head"><div><span className="eyebrow">{t('chart.standardizedZ')}</span><b>{label??feature}</b></div><small>{t('chart.reference100',{mean:fmt(ref.mean),sd:fmt(ref.sd),count:referenceValues.length})}</small></div>
    <div className="distribution-axis standardized-axis"><span>−3σ</span><span>−2σ</span><span>−1σ</span><span>0</span><span>+1σ</span><span>+2σ</span><span>+3σ</span></div>
    <div className="distribution-track standardized-track">{[-2,-1,0,1,2].map(z=><i key={z} className={`sigma-line ${z===0?'zero':''}`} style={{left:`${((z+3)/6)*100}%`}} aria-hidden="true"/>)}{pts.map((p,i)=><button type="button" key={p.v.video_id} aria-label={t('common.selectVideo',{title:p.v.title})} title={`${p.v.title} · raw ${fmt(p.stats.raw)} · z ${signed(p.stats.z)} · ${p.stats.percentile} percentile`} className={`distribution-point ${p.v.group}`} data-z={p.stats.z.toFixed(4)} style={{left:`${((clampZ(p.stats.z)+3)/6)*96+2}%`,top:`${20+(i%5)*13}%`}} onClick={()=>onSelect(p.v)}/>)}</div>
    <div className="research-footnote"><span>{t('chart.meanZero')}</span><span>{t('chart.oneSigma')}</span><span>{t('chart.clampSigma')}</span></div>
  </div>
}
