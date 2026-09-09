import { lazy, Suspense, useCallback, useMemo, useState } from 'react'
import type { AnalyzeReport } from '../data/analyzeReport'
import { useLocale } from '../i18n/LocaleProvider'

const AnalyzePca3D=lazy(()=>import('../visualizations/AnalyzePca3D'))
type Props={pca:AnalyzeReport['pca'];neighbors?:AnalyzeReport['neighbors'];title?:string}

export function AnalyzePcaCard({pca,neighbors=[],title='Your MV'}:Props){
  const {t}=useLocale()
  const [mode,setMode]=useState<'2d'|'3d'>('2d')
  const [selected,setSelected]=useState('')
  const [fallback,setFallback]=useState(false)
  const unavailable=useCallback(()=>{setMode('2d');setFallback(true)},[])
  const neighborIds=useMemo(()=>new Set(neighbors.map(row=>row.video_id)),[neighbors])
  const extent=Math.max(1,...pca.reference_points.flatMap(p=>p.score.slice(0,2).map(Math.abs)),...(pca.score?.slice(0,2).map(Math.abs)??[]))*1.15
  const coord=(x:number)=>240+x/extent*190
  if(pca.status!=='available'||!pca.score||!pca.display) return <div className="analyze-pca-card" role="status">
    <strong>{t('analyze.pcaInsufficient')}</strong>
    <p>{t('analyze.pcaObserved',{observed:pca.observed_count,total:pca.features.length})}</p>
    <p className="muted">{t('analyze.pcaThreshold')}</p>
  </div>
  const target=pca.score
  return <div className="analyze-pca-card">
    <div className="analyze-projection-toolbar"><div className="segmented" aria-label={t('analyze.projectionMode')}>
      <button type="button" aria-pressed={mode==='2d'} className={mode==='2d'?'is-active':''} onClick={()=>setMode('2d')}>2D</button>
      <button type="button" aria-pressed={mode==='3d'} className={mode==='3d'?'is-active':''} onClick={()=>setMode('3d')}>3D</button>
    </div><span>{t('analyze.pcaObserved',{observed:pca.observed_count,total:pca.features.length})}</span></div>
    {fallback&&<p role="status">{t('analyze.webglFallback')}</p>}
    {mode==='2d'?<svg className="analyze-projection" viewBox="0 0 480 480" role="img" aria-label={t('analyze.projectionLabel')}>
      <rect x="40" y="40" width="400" height="400" rx="12" className="plot-field"/>
      {[-1,-0.5,0,0.5,1].map(tick=><g key={tick}>
        <line x1={coord(tick*extent)} x2={coord(tick*extent)} y1="40" y2="440" className={tick===0?'zero-grid':'grid-line'}/>
        <line y1={coord(tick*extent)} y2={coord(tick*extent)} x1="40" x2="440" className={tick===0?'zero-grid':'grid-line'}/>
        <text x={coord(tick*extent)} y="457" textAnchor="middle" className="sigma-tick">{(tick*extent).toFixed(1)}</text>
        <text x="32" y={coord(-tick*extent)+3} textAnchor="end" className="sigma-tick">{(tick*extent).toFixed(1)}</text>
      </g>)}
      {pca.reference_points.filter(p=>neighborIds.has(p.video_id)).map(p=><line key={p.video_id} x1={coord(target[0])} y1={coord(-target[1])} x2={coord(p.score[0])} y2={coord(-p.score[1])} className="analyze-neighbor-line"/>)}
      {pca.reference_points.map(p=><circle key={p.video_id} cx={coord(p.score[0])} cy={coord(-p.score[1])} r={selected===p.video_id?7:4}
        className={`pca-point ${p.group}`} tabIndex={0} role="button" aria-label={p.title}
        onClick={()=>setSelected(p.video_id)} onFocus={()=>setSelected(p.video_id)} onKeyDown={e=>{if(e.key==='Enter')setSelected(p.video_id)}}>
        <title>{p.title} — PC1 {p.score[0].toFixed(3)}, PC2 {p.score[1].toFixed(3)}</title>
      </circle>)}
      <circle cx={coord(target[0])} cy={coord(-target[1])} r="11" className="analyze-target-halo"/>
      <circle cx={coord(target[0])} cy={coord(-target[1])} r="5" className="analyze-target-dot"><title>{title}</title></circle>
      <text x="240" y="477" textAnchor="middle" className="chart-label">PC1 · {pca.explained_variance_pct[0]}%</text>
      <text x="48" y="25" className="chart-label">PC2 · {pca.explained_variance_pct[1]}%</text>
    </svg>:<Suspense fallback={<p role="status">{t('space.loading3d')}</p>}><AnalyzePca3D pca={pca} neighborIds={[...neighborIds]} label={t('analyze.projectionLabel')} onUnavailable={unavailable}/></Suspense>}
    <p className="analyze-projection-legend"><span className="analyze-target-key">◉ {t('analyze.yourMv')}</span><span>● Top</span><span>● Bottom</span></p>
    {selected&&<p className="analyze-selected-reference" role="status">{pca.reference_points.find(p=>p.video_id===selected)?.title}</p>}
    <div className="analyze-pca-coords">{target.map((value,index)=><span key={index}><b>PC{index+1} {value.toFixed(3)}</b><small>{t('analyze.variance')} {pca.explained_variance_pct[index].toFixed(2)}%</small></span>)}</div>
    <p className="muted">{t('analyze.pcaNote')}</p>
    <p className="muted">{t('analyze.neighborProjectionNote')}</p>
    {!!pca.imputed_features.length&&<p>{t('analyze.imputed',{count:pca.imputed_features.length})}</p>}
    {!!pca.experimental_features.length&&<p className="analyze-experimental-note">{t('analyze.pcaExperimental')}</p>}
    <small className="analyze-basis-id">Basis {pca.basis_id}</small>
  </div>
}
