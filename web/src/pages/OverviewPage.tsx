import { useMemo, useState } from 'react'
import type { DomainsData, ManifestData, OverviewData } from '../data/schema'
import { StatCard } from '../components/StatCard'
import { DataFreshness } from '../components/DataFreshness'
import { EffectSizeChart } from '../visualizations/EffectSizeChart'
import { useLocale } from '../i18n/LocaleProvider'
import { domainLabel } from '../i18n/research'

export function OverviewPage({overview,domains,manifest}:{overview:OverviewData;domains:DomainsData;manifest:ManifestData}){
  const {locale,t,number}=useLocale()
  const initial=domains.vocaloid?'vocaloid':Object.keys(domains)[0]
  const [domain,setDomain]=useState(initial)
  const current=domains[domain]
  const significant=useMemo(()=>current?.numeric.filter(x=>x.significant).length??0,[current])
  const signal=current?.numeric[0]
  const signalLabel=signal?(signal.labels?.[locale]||signal.label):t('overview.keyFeature')
  const fmt=(v:number|undefined)=>v==null?'–':number(v,{maximumFractionDigits:3})
  return <div className="page overview-page">
    <section className="hero"><div><span className="kicker">VISUAL MUSIC VIDEO RESEARCH</span><h1>{t('overview.hero1')}<br/><em>{t('overview.hero2')}</em></h1><p>{t('overview.desc')}</p></div><div className="hero-orbit" aria-hidden="true"><span/><span/><span/><b>100</b><small>MVs</small></div></section>
    <DataFreshness manifest={manifest}/>
    <section className="stat-grid" aria-label={t('overview.summaryAria')}><StatCard label={t('overview.publicSample')} value={overview.video_count}/><StatCard label="Vocaloid" value={overview.domain_counts.vocaloid?.total??0} detail={`${overview.domain_counts.vocaloid?.top??0} top · ${overview.domain_counts.vocaloid?.bottom??0} bottom`}/><StatCard label="K-pop" value={overview.domain_counts.kpop?.total??0} detail={`${overview.domain_counts.kpop?.top??0} top · ${overview.domain_counts.kpop?.bottom??0} bottom`}/><StatCard label={t('overview.significantFeatures')} value={significant} detail="BH-FDR q < 0.05" accent="neutral"/></section>
    <section className="panel"><div className="section-head"><div><span className="eyebrow">EFFECT SIZE</span><h2>{t('overview.effectTitle')}</h2><p>{t('overview.effectDesc')}</p></div><div className="segmented" aria-label={t('overview.domainSelect')}>{Object.keys(domains).map(d=><button type="button" key={d} className={domain===d?'is-active':''} onClick={()=>setDomain(d)}>{domainLabel(d)}</button>)}</div></div><div className="legend-row"><span className="legend-item"><i className="legend-shape legend-top"/>{t('overview.topGroup')}</span><span className="legend-item"><i className="legend-shape legend-bottom"/>{t('overview.bottomGroup')}</span><span className="legend-note">✓ q &lt; 0.05 · {domainLabel(domain)} n={current?.n_top}+{current?.n_bottom}</span></div><EffectSizeChart items={current?.numeric??[]}/></section>
    <section className="two-col"><article className="panel insight-panel"><span className="eyebrow">READ THE SIGNAL</span><h2>{signalLabel}</h2><div className="signal-number">δ {signal?.delta?.toFixed(3)??'–'}</div><p>{t('overview.topMedian')} <b>{fmt(signal?.median_top)}</b> · {t('overview.bottomMedian')} <b>{fmt(signal?.median_bottom)}</b></p><p className="muted">{t('overview.signalCaveat')}</p></article><article className="panel caveat-panel"><span className="eyebrow">CAUSALITY WARNING</span><h2>{t('overview.causal1')}<br/>{t('overview.causal2')}</h2><p>{locale==='ko'?overview.causal_warning:t('overview.causalBody')}</p><p className="muted">{t('overview.confounds')}</p></article></section>
  </div>
}
