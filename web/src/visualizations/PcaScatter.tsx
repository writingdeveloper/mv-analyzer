import type { SpacePoint } from '../data/schema'
import { useLocale } from '../i18n/LocaleProvider'

export function PcaScatter({points,selectedId,onSelect}:{points:SpacePoint[];selectedId?:string;onSelect:(p:SpacePoint)=>void}){
  const {t}=useLocale();const sx=(v:number)=>50+(v+1)/2*800,sy=(v:number)=>300-(v+1)/2*250
  return <div className="chart-scroll"><svg viewBox="0 0 900 350" role="img" aria-label={t('space.pca2dAria')} className="pca-chart"><line x1="450" x2="450" y1="40" y2="310" className="grid-line"/><line x1="45" x2="855" y1="175" y2="175" className="grid-line"/>{points.map(p=><circle key={p.id} cx={sx(p.pca[0])} cy={sy(p.pca[1])} r={selectedId===p.id?9:6} className={`pca-point ${p.group} ${selectedId===p.id?'selected':''}`} role="button" tabIndex={0} aria-label={t('common.selectVideo',{title:p.title})} onClick={()=>onSelect(p)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect(p)}}}><title>{`${p.title} · PC1 ${p.pca[0]} · PC2 ${p.pca[1]}`}</title></circle>)}<text x="450" y="340" textAnchor="middle" className="axis-caption">PC1</text><text x="16" y="175" transform="rotate(-90 16 175)" textAnchor="middle" className="axis-caption">PC2</text></svg></div>
}
