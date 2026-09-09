import type { FeatureMeta,VideoRow } from '../data/schema'
import { numericValue } from '../data/filters'
import { useLocale } from '../i18n/LocaleProvider'
import { domainLabel, featureLabel } from '../i18n/research'

export function VideoDetailPanel({video,features,onClose}:{video:VideoRow;features:FeatureMeta[];onClose?:()=>void}){
  const {locale,t,number}=useLocale()
  const numeric=features.filter(f=>f.kind==='numeric').map(f=>({f,v:numericValue(video,f.id)})).filter(x=>x.v!==null).slice(0,8)
  const format=(value:number|null|undefined,digits=2)=>value==null||!Number.isFinite(value)?'–':number(value,{maximumFractionDigits:digits})
  return <aside className="video-detail"><div className="detail-head"><span className={`group-tag ${video.group}`}>{video.group==='top'?'TOP':'BOTTOM'}</span>{onClose&&<button type="button" className="icon-button" onClick={onClose} aria-label={t('common.closeSelection')}>×</button>}</div><h2>{video.title}</h2><p>{video.channel} · {domainLabel(video.domain)}</p><div className="detail-metric"><span>{t('common.viewSubRatio')}</span><b>{format(video.view_per_sub,3)}</b></div><dl>{numeric.map(({f,v})=><div key={f.id}><dt>{featureLabel(f,locale)}</dt><dd>{format(v)}</dd></div>)}</dl><a className="primary-link" href={`https://www.youtube.com/watch?v=${video.video_id}`} target="_blank" rel="noreferrer">{t('common.watchYoutube')}</a></aside>
}
