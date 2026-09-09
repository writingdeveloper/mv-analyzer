import { lazy, Suspense, useMemo, useState } from 'react'
import type { SpaceData, SpacePoint } from '../data/schema'
import { nearestNeighbors } from '../data/neighbors'
import { useLocale } from '../i18n/LocaleProvider'
import { domainLabel } from '../i18n/research'
import { PcaScatter } from '../visualizations/PcaScatter'

const Pca3D = lazy(() => import('../visualizations/Pca3D'))

export function SpacePage({ data }: { data: SpaceData }) {
  const { locale, t, number } = useLocale()
  const [mode, setMode] = useState<'2d' | '3d'>('2d')
  const [domain, setDomain] = useState('all')
  const [group, setGroup] = useState('all')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<SpacePoint | null>(null)
  const [showNeighbors, setShowNeighbors] = useState(true)
  const [autoRotate, setAutoRotate] = useState(true)
  const [resetKey, setResetKey] = useState(0)

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    return data.points.filter((point) =>
      (domain === 'all' || point.domain === domain) &&
      (group === 'all' || point.group === group) &&
      (!q || `${point.title} ${point.channel}`.toLowerCase().includes(q)),
    )
  }, [data.points, domain, group, query])

  const neighbors = selected ? nearestNeighbors(data.points, selected.id, 5) : []
  const loadingLabel = (item: NonNullable<SpaceData['loadings']>[number]['items'][number]) => item.labels?.[locale] ?? item.label ?? item.feature
  const fmt = (value: number, digits = 2) => number(value, { maximumFractionDigits: digits })

  return <div className="page space-page">
    <header className="page-title">
      <span className="kicker">MULTIVARIATE MAP</span>
      <h1>{t('space.hero1')}<br/><em>{t('space.hero2')}</em></h1>
      <p>{t('space.desc')}</p>
    </header>

    <section className="panel">
      <div className="space-toolbar">
        <div className="filter-inline">
          <label>{t('common.domain')}<select aria-label={t('common.domain')} value={domain} onChange={e=>setDomain(e.target.value)}><option value="all">{t('common.all')}</option><option value="vocaloid">Vocaloid</option><option value="kpop">K-pop</option></select></label>
          <label>{t('common.group')}<select aria-label={t('common.group')} value={group} onChange={e=>setGroup(e.target.value)}><option value="all">{t('common.all')}</option><option value="top">{t('common.top')}</option><option value="bottom">{t('common.bottom')}</option></select></label>
          <label className="space-search">{t('space.mvSearch')}<input aria-label={t('space.mvSearch')} value={query} onChange={e=>setQuery(e.target.value)} placeholder={t('common.searchPlaceholder')}/></label>
        </div>
        <div className="segmented"><button type="button" className={mode==='2d'?'is-active':''} onClick={()=>setMode('2d')}>2D</button><button type="button" className={mode==='3d'?'is-active':''} onClick={()=>setMode('3d')}>3D</button></div>
      </div>

      <div className="space-meta"><span>PC1 {data.explained_variance_pct[0]}%</span><span>PC2 {data.explained_variance_pct[1]}%</span><span>PC3 {data.explained_variance_pct[2]}%</span><b>{t('common.videosShown',{count:shown.length})}</b></div>

      <div className="space-provenance" aria-label={t('space.provenanceAria')}>
        <div><span>Z-SCORED FEATURES</span><b>{t('space.numericFeatures',{count:data.features.length})}</b><small>{data.normalization?.imputation ?? 'median'} imputation · μ=0, σ=1</small></div>
        <i aria-hidden="true">→</i>
        <div><span>PCA SCORES</span><b>{t('space.pcaDistance')}</b><small>{t('space.rawScoreDesc')}</small></div>
        <i aria-hidden="true">→</i>
        <div><span>DISPLAY NORMALIZED</span><b>max |PC| = 1</b><small>{t('space.displayDesc')}</small></div>
      </div>

      {!!data.loadings?.length && <div className="pca-loading-grid" aria-label={t('space.loadingAria')}>{data.loadings.map((pc,index)=><article key={pc.component}><span>{pc.component} · {data.explained_variance_pct[index] ?? 0}% variance</span><b>{pc.component} · {pc.items.slice(0,3).map(loadingLabel).join(' / ')}</b><div>{pc.items.slice(0,4).map(item=><small key={item.feature}><em>{item.loading>=0?'+':'−'}</em>{loadingLabel(item)}<code>{Math.abs(item.loading).toFixed(2)}</code></small>)}</div></article>)}</div>}

      {mode==='3d'&&<div className="constellation-toolbar" aria-label="Data Constellation controls"><div><span className="eyebrow">3D RESEARCH VIEW</span><b>Data Constellation</b><small>{t('space.constellationDesc')}</small></div><div className="constellation-actions"><button type="button" onClick={()=>setShowNeighbors(v=>!v)}>{showNeighbors?t('space.hideNeighbors'):t('space.showNeighbors')}</button><button type="button" onClick={()=>setAutoRotate(v=>!v)}>{autoRotate?t('space.disableRotate'):t('space.enableRotate')}</button><button type="button" onClick={()=>setResetKey(v=>v+1)}>{t('space.resetView')}</button></div></div>}

      {mode==='2d'?<PcaScatter points={shown} selectedId={selected?.id} onSelect={setSelected}/>:<Suspense fallback={<div className="empty-state">{t('space.loading3d')}</div>}><Pca3D points={shown} selectedId={selected?.id} showNeighbors={showNeighbors} autoRotate={autoRotate} resetKey={resetKey} explainedVariance={data.explained_variance_pct} onSelect={setSelected}/></Suspense>}
      <p className="chart-note">{t('space.chartNote')}</p>
    </section>

    {selected&&<section className="space-detail panel"><div><span className={`group-tag ${selected.group}`}>{selected.group.toUpperCase()}</span><h2>{selected.title}</h2><p>{selected.channel} · {domainLabel(selected.domain)}</p><code>display PC {selected.pca.map(v=>v.toFixed(3)).join(' / ')}</code>{selected.score&&<code>raw score {selected.score.map(v=>v.toFixed(3)).join(' / ')}</code>}</div><div><span className="eyebrow">{t('space.neighbors')}</span><ol>{neighbors.map(n=><li key={n.id}><button type="button" onClick={()=>setSelected(n)}>{n.title}</button><small>d={fmt(n.distance,3)}</small></li>)}</ol></div></section>}
  </div>
}
