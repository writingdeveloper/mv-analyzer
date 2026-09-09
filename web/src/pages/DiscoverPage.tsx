import { useMemo,useState } from 'react'
import { Link } from 'react-router-dom'
import type { CorrelationsData,FeatureMeta,VideoRow } from '../data/schema'
import { filterVideos } from '../data/filters'
import { FilterBar } from '../components/FilterBar'
import { VideoDetailPanel } from '../components/VideoDetailPanel'
import { FeatureDistribution } from '../visualizations/FeatureDistribution'
import { ScatterPlot } from '../visualizations/ScatterPlot'
import { CorrelationHeatmap } from '../visualizations/CorrelationHeatmap'
import { useLocale } from '../i18n/LocaleProvider'
import { featureLabel } from '../i18n/research'

export function DiscoverPage({videos,features,correlations}:{videos:VideoRow[];features:FeatureMeta[];correlations:CorrelationsData}){
 const {locale,t}=useLocale()
 const numeric=features.filter(f=>f.kind==='numeric')
 const [domain,setDomain]=useState('all'),[group,setGroup]=useState('all'),[query,setQuery]=useState('')
 const [xKey,setXKey]=useState(numeric[0]?.id??''),[yKey,setYKey]=useState(numeric[1]?.id??numeric[0]?.id??''),[selected,setSelected]=useState<VideoRow|null>(null)
 const shown=useMemo(()=>filterVideos(videos,{domain,group,query}),[videos,domain,group,query])
 const corrDomain=domain==='all'?'vocaloid':domain
 const xMeta=numeric.find(f=>f.id===xKey),yMeta=numeric.find(f=>f.id===yKey)
 const xName=xMeta?featureLabel(xMeta,locale):xKey,yName=yMeta?featureLabel(yMeta,locale):yKey
 return <div className="page discover-page">
   <header className="page-title"><span className="kicker">DISCOVER THE DATA</span><h1>{t('discover.hero1')}<br/><em>{t('discover.hero2')}</em></h1><p>{t('discover.desc')}</p></header>
   <FilterBar domain={domain} group={group} query={query} onDomain={setDomain} onGroup={setGroup} onQuery={setQuery}/><div className="result-count">{t('common.videosShown',{count:shown.length})}</div>
   <section className="panel"><div className="section-head"><div><span className="eyebrow">ONE FEATURE</span><h2>{t('discover.oneFeature')}</h2></div><label className="select-stack">Feature<select value={xKey} onChange={e=>setXKey(e.target.value)}>{numeric.map(f=><option value={f.id} key={f.id}>{featureLabel(f,locale)}</option>)}</select></label></div><FeatureDistribution videos={shown} reference={videos} feature={xKey} label={xName} onSelect={setSelected}/><div className="video-chip-list">{shown.slice(0,12).map(v=><button type="button" key={v.video_id} aria-label={t('common.selectVideo',{title:v.title})} onClick={()=>setSelected(v)} className={`video-chip ${v.group}`}><span>{v.title}</span><small>{v.channel}</small></button>)}</div></section>
   <section className="panel"><div className="section-head"><div><span className="eyebrow">TWO FEATURES</span><h2>{t('discover.twoFeatures')}</h2><p>{t('discover.twoFeaturesDesc')}</p></div><div className="axis-selects"><label>X feature<select aria-label="X feature" value={xKey} onChange={e=>setXKey(e.target.value)}>{numeric.map(f=><option value={f.id} key={f.id}>{featureLabel(f,locale)}</option>)}</select></label><label>Y feature<select aria-label="Y feature" value={yKey} onChange={e=>setYKey(e.target.value)}>{numeric.map(f=><option value={f.id} key={f.id}>{featureLabel(f,locale)}</option>)}</select></label></div></div><ScatterPlot videos={shown} reference={videos} xKey={xKey} yKey={yKey} xLabel={xName} yLabel={yName} onSelect={setSelected}/></section>
   <section className="panel"><span className="eyebrow">CORRELATION MAP</span><h2>{t('discover.correlationTitle')}</h2><p className="muted">{t('discover.correlationDesc')}</p><CorrelationHeatmap data={correlations.domains[corrDomain]} features={features}/></section>
   {selected&&<div className="detail-overlay"><VideoDetailPanel video={selected} features={features} onClose={()=>setSelected(null)}/><Link className="secondary-link" to={`/compare?ids=${selected.video_id}`}>{t('discover.addCompare')}</Link></div>}
 </div>
}
