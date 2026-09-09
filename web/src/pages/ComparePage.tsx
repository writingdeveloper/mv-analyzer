import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { FeatureMeta,VideoRow } from '../data/schema'
import { PercentileBars } from '../visualizations/PercentileBars'
import { useLocale } from '../i18n/LocaleProvider'

export function ComparePage({videos,features}:{videos:VideoRow[];features:FeatureMeta[]}){
 const {t}=useLocale()
 const [params,setParams]=useSearchParams();const requested=(params.get('ids')??'').split(',').filter(Boolean).slice(0,4)
 const selected=useMemo(()=>requested.map(id=>videos.find(v=>v.video_id===id)).filter((v):v is VideoRow=>Boolean(v)),[requested.join(','),videos])
 const add=(id:string)=>{const ids=Array.from(new Set([...requested,id])).slice(0,4);setParams({ids:ids.join(',')})}
 const remove=(id:string)=>setParams({ids:requested.filter(x=>x!==id).join(',')})
 const candidates=videos.filter(v=>!requested.includes(v.video_id)).slice(0,100)
 return <div className="page compare-page"><header className="page-title"><span className="kicker">SIDE BY SIDE</span><h1>{t('compare.hero1')}<br/><em>{t('compare.hero2')}</em></h1><p>{t('compare.desc')}</p></header><section className="panel"><div className="compare-picker"><label>{t('compare.addVideo')}<select aria-label={t('compare.addVideo')} value="" onChange={e=>{if(e.target.value)add(e.target.value)}}><option value="">{t('common.select')}</option>{candidates.map(v=><option key={v.video_id} value={v.video_id}>{v.title} — {v.channel}</option>)}</select></label><span>{t('compare.selectedCount',{count:selected.length})}</span></div><div className="compare-cards">{selected.map(v=><article key={v.video_id} className={`compare-card ${v.group}`}><span className={`group-tag ${v.group}`}>{v.group.toUpperCase()}</span><h2>{v.title}</h2><p>{v.channel}</p><button type="button" onClick={()=>remove(v.video_id)}>{t('compare.remove')}</button></article>)}</div>{selected.length<2&&<div className="empty-state">{t('compare.needTwo')}</div>}</section>{selected.length>=2&&<section className="panel"><span className="eyebrow">PERCENTILE PROFILE</span><h2>{t('compare.profileTitle')}</h2><PercentileBars videos={selected} reference={videos} features={features}/></section>}</div>
}
