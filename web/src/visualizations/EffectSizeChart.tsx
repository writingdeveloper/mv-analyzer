import type { NumericEffect } from '../data/schema'
import { useLocale } from '../i18n/LocaleProvider'

export function EffectSizeChart({items}:{items:NumericEffect[]}){
  const {locale,t,number}=useLocale()
  const shown=items.filter(x=>Math.abs(x.delta)>=0.147).slice(0,12)
  if(!shown.length) return <div className="empty-state">{t('chart.noEffect')}</div>
  const width=920,labelW=250,plotW=560,center=labelW+plotW/2,rowH=38,height=shown.length*rowH+50
  const x=(delta:number)=>center+delta*(plotW/2)
  const label=(r:NumericEffect)=>r.labels?.[locale]||r.label
  const fmt=(v:number)=>number(v,{maximumFractionDigits:3})
  return <div className="chart-scroll"><svg className="effect-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={t('chart.effectAria')}><line x1={center} x2={center} y1="8" y2={height-34} className="axis-zero"/>{shown.map((r,i)=>{const y=16+i*rowH; const positive=r.delta>=0; const end=x(r.delta); const bx=Math.min(center,end); const bw=Math.max(2,Math.abs(end-center)); const name=label(r); return <g key={r.id}><text x={labelW-14} y={y+14} textAnchor="end" className="chart-label">{name}</text><rect x={bx} y={y} width={bw} height="18" rx="5" className={positive?'bar-top':'bar-bottom'}><title>{`${name}: δ ${r.delta}, ${t('overview.topMedian')} ${fmt(r.median_top)}, ${t('overview.bottomMedian')} ${fmt(r.median_bottom)}, q=${r.q}`}</title></rect><text x={positive?end+8:end-8} y={y+14} textAnchor={positive?'start':'end'} className="chart-value">{r.delta>0?'+':''}{r.delta.toFixed(3)}{r.significant?' ✓':''}</text></g>})}<text x={center-14} y={height-10} textAnchor="end" className="axis-caption bottom-text">{t('chart.bottomLarger')}</text><text x={center+14} y={height-10} className="axis-caption top-text">{t('chart.topLarger')}</text></svg></div>
}
