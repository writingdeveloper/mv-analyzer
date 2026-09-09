import type { VideoRow } from '../data/schema'
import { numericSeries, numericValue } from '../data/filters'
import { describeStandardizedValue } from '../data/normalization'
import { useLocale } from '../i18n/LocaleProvider'

const clampZ=(z:number)=>Math.max(-3,Math.min(3,z))
const signed=(value:number)=>`${value>=0?'+':''}${value.toFixed(2)}`
const sx=(z:number)=>70+((clampZ(z)+3)/6)*750
const sy=(z:number)=>300-((clampZ(z)+3)/6)*250
type Standardized = ReturnType<typeof describeStandardizedValue>
type ScatterPoint = {v:VideoRow;x:Standardized;y:Standardized}

export function ScatterPlot({videos,reference,xKey,yKey,xLabel,yLabel,onSelect}:{videos:VideoRow[];reference:VideoRow[];xKey:string;yKey:string;xLabel?:string;yLabel?:string;onSelect:(v:VideoRow)=>void}){
  const {t,number}=useLocale()
  const xReference=numericSeries(reference,xKey),yReference=numericSeries(reference,yKey)
  const pts=videos.map(v=>{const x=numericValue(v,xKey),y=numericValue(v,yKey);return x===null||y===null?null:{v,x:describeStandardizedValue(xReference,x),y:describeStandardizedValue(yReference,y)}}).filter((p):p is ScatterPoint=>p!==null)
  if(!pts.length)return <div className="empty-state">{t('chart.scatterEmpty')}</div>
  const xName=xLabel??xKey,yName=yLabel??yKey,ticks=[-2,-1,0,1,2]
  const fmt=(v:number)=>number(v,{maximumFractionDigits:2})
  const pointTitle=(p:ScatterPoint)=>`${p.v.title}\n${xName}: raw ${fmt(p.x.raw)} · z ${signed(p.x.z)} · ${p.x.percentile} percentile\n${yName}: raw ${fmt(p.y.raw)} · z ${signed(p.y.z)} · ${p.y.percentile} percentile`
  return <div className="standardized-scatter"><div className="standardized-visual-head"><div><span className="eyebrow">STANDARDIZED FEATURE SPACE</span><b>{xName} × {yName}</b></div><small>{t('chart.scatterDesc')}</small></div><div className="chart-scroll"><svg viewBox="0 0 880 350" className="scatter-chart research-scatter" role="img" aria-label={t('chart.scatterAria',{x:xName,y:yName})}><rect x="70" y="50" width="750" height="250" rx="10" className="plot-field"/>{ticks.map(z=><g key={`x${z}`}><line x1={sx(z)} x2={sx(z)} y1="50" y2="300" className={z===0?'grid-line zero-grid':'grid-line'}/><text x={sx(z)} y="319" textAnchor="middle" className="sigma-tick">{z>0?`+${z}`:z}</text></g>)}{ticks.map(z=><g key={`y${z}`}><line x1="70" x2="820" y1={sy(z)} y2={sy(z)} className={z===0?'grid-line zero-grid':'grid-line'}/><text x="58" y={sy(z)+3} textAnchor="end" className="sigma-tick">{z>0?`+${z}`:z}</text></g>)}{pts.map(p=><circle key={p.v.video_id} cx={sx(p.x.z)} cy={sy(p.y.z)} r="6" tabIndex={0} role="button" aria-label={t('common.selectVideo',{title:p.v.title})} className={`scatter-point ${p.v.group}`} data-x-z={p.x.z.toFixed(4)} data-y-z={p.y.z.toFixed(4)} onClick={()=>onSelect(p.v)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(p.v)}}}><title>{pointTitle(p)}</title></circle>)}<text x="445" y="344" textAnchor="middle" className="axis-caption">{xName} · z-score</text><text x="18" y="175" transform="rotate(-90 18 175)" textAnchor="middle" className="axis-caption">{yName} · z-score</text></svg></div><div className="research-footnote"><span>{t('chart.pointOneMv')}</span><span>{t('chart.originMean')}</span><span>{t('chart.colorGroups')}</span></div></div>
}
