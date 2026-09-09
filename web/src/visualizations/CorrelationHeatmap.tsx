import type { CorrelationDomain, FeatureMeta } from '../data/schema'
import { useLocale } from '../i18n/LocaleProvider'
import { featureLabelById } from '../i18n/research'

export function CorrelationHeatmap({data,features}:{data:CorrelationDomain|undefined;features:FeatureMeta[]}){
  const {locale,t}=useLocale()
  if(!data||!data.features.length)return <div className="empty-state">{t('chart.correlationEmpty')}</div>
  const label=(id:string)=>featureLabelById(id,locale,features)
  return <div className="heatmap-research-view"><div className="heatmap-key" aria-label={t('chart.correlationLegend')}><span><b>−1</b> {t('chart.opposite')}</span><i aria-hidden="true"/><span><b>0</b> {t('chart.weakMonotonic')}</span><i aria-hidden="true"/><span><b>+1</b> {t('chart.sameDirection')}</span><small>{t('chart.spearmanNote')}</small></div><div className="heatmap-wrap"><table className="heatmap-table"><thead><tr><th>ρ</th>{data.features.map(f=><th key={f} title={label(f)}><span>{label(f)}</span></th>)}</tr></thead><tbody>{data.features.map((f,i)=><tr key={f}><th title={label(f)}>{label(f)}</th>{data.matrix[i].map((value,j)=>{const mag=Math.abs(value??0);return <td key={data.features[j]} style={{background:`color-mix(in srgb, ${value!=null&&value<0?'var(--bottom)':'var(--top)'} ${Math.round(mag*55)}%, var(--surface))`}} title={`${label(f)} × ${label(data.features[j])}: ${value??'–'}`}>{value==null?'–':value.toFixed(2)}</td>})}</tr>)}</tbody></table></div></div>
}
