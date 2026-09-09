import { useMemo,useState } from 'react'
import type { MethodologyData,VideoRow } from '../data/schema'
import { SampleTable } from '../components/SampleTable'
import { useLocale } from '../i18n/LocaleProvider'

export function SamplesPage({videos,methodology}:{videos:VideoRow[];methodology:MethodologyData}){
  const {t,integer}=useLocale()
  const [query,setQuery]=useState(''),[domain,setDomain]=useState('all'),[group,setGroup]=useState('all')
  const shown=useMemo(()=>{const q=query.trim().toLowerCase();return videos.filter(v=>(domain==='all'||v.domain===domain)&&(group==='all'||v.group===group)&&(!q||`${v.title} ${v.channel}`.toLowerCase().includes(q)))},[videos,query,domain,group])
  const exp=methodology.study.expansion
  return <div className="page samples-page">
    <header className="page-title"><span className="kicker">SAMPLE TRANSPARENCY</span><h1>{t('samples.hero1')}<br/><em>{t('samples.hero2')}</em></h1><p>{t('samples.desc')}</p></header>
    <section className="expansion-grid">{Object.entries(exp).map(([name,x])=><article key={name} className={`panel expansion-card ${x.feasible?'feasible':'shortfall'}`}><span className="eyebrow">{name==='vocaloid'?'VOCALOID':'K-POP'} EXPANSION</span><strong>{x.max_top} / {x.max_bottom}</strong><p>{t('samples.target',{top:x.target_per_group,bottom:x.target_per_group})} · {t('samples.eligible',{count:integer(x.eligible_population)})} · {t('samples.channelCap',{count:x.channel_cap})}</p><div className="expansion-meter"><i style={{width:`${Math.min(100,x.max_top/x.target_per_group*100)}%`}}/><i style={{width:`${Math.min(100,x.max_bottom/x.target_per_group*100)}%`}}/></div><small>{x.feasible?t('samples.feasible'):t('samples.shortfall')}</small></article>)}</section>
    <section className="panel"><div className="sample-controls"><label>{t('common.sampleSearch')}<input aria-label={t('common.sampleSearch')} value={query} onChange={e=>setQuery(e.target.value)} placeholder={t('common.searchPlaceholder')}/></label><label>{t('common.domain')}<select aria-label={t('common.domain')} value={domain} onChange={e=>setDomain(e.target.value)}><option value="all">{t('common.all')}</option><option value="vocaloid">Vocaloid</option><option value="kpop">K-pop</option></select></label><label>{t('common.group')}<select aria-label={t('common.group')} value={group} onChange={e=>setGroup(e.target.value)}><option value="all">{t('common.all')}</option><option value="top">{t('common.top')}</option><option value="bottom">{t('common.bottom')}</option></select></label><b>{t('common.videos',{count:shown.length})}</b></div><SampleTable videos={shown}/></section>
  </div>
}
