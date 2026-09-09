import { useCallback, useEffect, useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { Link } from 'react-router-dom'
import { AnalyzeFeatureProfile } from '../components/AnalyzeFeatureProfile'
import { AnalyzeNeighbors } from '../components/AnalyzeNeighbors'
import { AnalyzePcaCard } from '../components/AnalyzePcaCard'
import { ReasonSummary } from '../components/ReasonSummary'
import { MAX_ANALYZE_REPORT_BYTES, ReportValidationError, parseAnalyzeReport, type AnalyzeReport } from '../data/analyzeReport'
import { deriveReasonDocument, parseReasonDocument, ReasonDocumentValidationError, type ReasonDocument } from '../data/reasonDocument'
import { useLocale } from '../i18n/LocaleProvider'

export function AnalyzePage(){
  const {t,date,number}=useLocale()
  const [report,setReport]=useState<AnalyzeReport|null>(null)
  const [reasonDoc,setReasonDoc]=useState<ReasonDocument|null>(null)
  const [error,setError]=useState<Parameters<typeof t>[0]|null>(null)
  const [busy,setBusy]=useState(false)
  const [isDemo,setIsDemo]=useState(false)
  const epoch=useRef(0)
  const demoAbort=useRef<AbortController|null>(null)
  useEffect(()=>()=>{epoch.current++;demoAbort.current?.abort()},[])
  const [dragging,setDragging]=useState(false)

  const cancel=()=>{epoch.current++;demoAbort.current?.abort();setBusy(false);setReport(null);setReasonDoc(null);setError(null);setIsDemo(false)}
  const importFile=useCallback(async(file:File|undefined)=>{
    if(!file)return
    const current=++epoch.current
    demoAbort.current?.abort()
    setError(null);setReport(null);setBusy(true);setIsDemo(false)
    try{
      if(!/\.json$/i.test(file.name)){setError('analyze.errorType');return}
      if(file.size>MAX_ANALYZE_REPORT_BYTES){setError('analyze.fileTooLarge');return}
      const text=await file.text()
      if(current!==epoch.current)return
      const raw=JSON.parse(text.replace(/^\uFEFF/,''))
      if(raw?.kind==='mv-analyzer-reason'){const reason=parseReasonDocument(raw);setReasonDoc(reason);setReport(null)}
      else {const parsed=parseAnalyzeReport(raw);setReport(parsed);setReasonDoc(deriveReasonDocument(parsed))}
    }catch(reason){
      if(current!==epoch.current)return
      const keys={corpus:'analyze.errorCorpus',legacy:'analyze.errorLegacy',schema:'analyze.errorSchema',unsafe:'analyze.errorUnsafe',inconsistent:'analyze.errorInconsistent'} as const
      setError(reason instanceof ReportValidationError?keys[reason.code]:reason instanceof ReasonDocumentValidationError?keys[reason.code]:'analyze.errorRead')
    }finally{if(current===epoch.current)setBusy(false)}
  },[])
  const loadDemo=async()=>{
    const current=++epoch.current
    demoAbort.current?.abort()
    const controller=new AbortController();demoAbort.current=controller
    setError(null);setBusy(true)
    try{
      const response=await fetch(`${import.meta.env.BASE_URL}data/demo-report.json`,{signal:controller.signal})
      if(!response.ok)throw new Error('demo request failed')
      const parsed=parseAnalyzeReport(await response.json())
      if(current===epoch.current){setReport(parsed);setReasonDoc(deriveReasonDocument(parsed));setIsDemo(true)}
    }catch{if(current===epoch.current)setError('analyze.errorDemo')}
    finally{if(current===epoch.current)setBusy(false)}
  }
  const onChange=(event:ChangeEvent<HTMLInputElement>)=>{
    const file=event.currentTarget.files?.[0]
    event.currentTarget.value=''
    void importFile(file)
  }
  const onDrop=(event:DragEvent<HTMLDivElement>)=>{
    event.preventDefault();setDragging(false)
    if(event.dataTransfer.files.length!==1){cancel();setError('analyze.errorType');return}
    void importFile(event.dataTransfer.files[0])
  }
  const clear=cancel

  if(!report&&!reasonDoc)return <div className="page analyze-page">
    <header className="page-title analyze-hero"><span className="kicker">ANALYZE MY MV</span><h1>{t('analyze.hero1')}<br/><em>{t('analyze.hero2')}</em></h1><p>{t('analyze.desc')}</p></header>
    <section className="panel analyze-demo"><div><b>{t('analyze.demo')}</b><p>{t('analyze.privateAccess')}</p></div><button className="primary-link" type="button" onClick={()=>void loadDemo()} disabled={busy}>{t('analyze.demo')}</button></section>
    <section className="analyze-flow">
      <article className="panel analyze-command"><span className="eyebrow">01 · LOCAL ANALYSIS</span><h2>{t('analyze.localTitle')}</h2><p>{t('analyze.localDesc')}</p><code>mva analyze &lt;YouTube URL&gt; --web-report my-mv.json</code><small>{t('analyze.localNote')}</small><p>{t('analyze.offlineCommand')}</p><code>mva report-export data/VIDEO_ID/features.json --out my-mv.json</code></article>
      <article className="panel analyze-import-panel"><span className="eyebrow">02 · LOCAL IMPORT</span><h2>{t('analyze.importTitle')}</h2><p>{t('analyze.importDesc')}</p>
        <div className={`analyze-dropzone ${dragging?'is-dragging':''}`} onDragOver={event=>{event.preventDefault();setDragging(true)}} onDragLeave={()=>setDragging(false)} onDrop={onDrop}>
          <b>{t('analyze.drop')}</b><span>{t('analyze.or')}</span><label className="primary-link analyze-file-button">{t('analyze.choose')}<input aria-label={t('analyze.fileLabel')} type="file" accept="application/json,.json" onChange={onChange}/></label><small>{t('analyze.privacy')}</small>
        </div>
        {busy&&<div className="analyze-import-status" role="status"><span>{t('analyze.processing')}</span><button type="button" onClick={cancel}>{t('analyze.cancel')}</button></div>}
        {error&&<div className="analyze-error" role="alert"><b>{t('analyze.errorTitle')}</b><span>{t(error)}</span></div>}
      </article>
    </section>
    <section className="panel analyze-trust"><div><span className="eyebrow">PRIVACY BOUNDARY</span><h2>{t('analyze.trustTitle')}</h2></div><p>{t('analyze.trustBody')}</p><Link className="secondary-link" to="/methodology">{t('analyze.methodology')}</Link></section>
  </div>

  if(!report&&reasonDoc)return <div className="page analyze-page analyze-results reason-only-results">
    <header className="analyze-result-head panel"><div><span className="kicker">IMPORTED REASON DOCUMENT</span><h1>{reasonDoc.video.title}</h1><p>{reasonDoc.video.channel} · {reasonDoc.video.video_id}</p></div><button type="button" className="analyze-clear" onClick={clear}>{t('analyze.clear')}</button><div className="analyze-disclaimer">{t('analyze.disclaimer')}</div></header>
    <ReasonSummary reason={reasonDoc}/><section className="panel analyze-fingerprints"><p>{t('analyze.provenanceNote')}</p><dl><dt>{t('analyze.sourceFingerprint')}</dt><dd><code>{reasonDoc.source_report.source_features_sha256}</code></dd><dt>{t('analyze.corpusFingerprint')}</dt><dd><code>{reasonDoc.source_report.corpus_sha256}</code></dd></dl></section>
  </div>
  if(!report)return null
  const centroidText=report.centroids.closer_group==='top'?t('analyze.closerTop'):report.centroids.closer_group==='bottom'?t('analyze.closerBottom'):t('analyze.centroidUnavailable')
  const reason=reasonDoc??deriveReasonDocument(report)
  return <div className="page analyze-page analyze-results">
    <header className="analyze-result-head panel">
      <div><span className="kicker">IMPORTED LOCAL REPORT</span><h1>{report.video.title}</h1><p>{report.video.channel} · {report.video.video_id}</p></div>
      <button type="button" className="analyze-clear" onClick={clear}>{t('analyze.clear')}</button>
      {isDemo&&<p className="analyze-demo-notice" role="status">{t('analyze.demoNotice')}</p>}
      <div className="analyze-disclaimer">{t('analyze.disclaimer')}</div>
    </header>
    <ReasonSummary reason={reason}/>
    <section className="analyze-context-grid">
      <article className="panel"><span className="eyebrow">REFERENCE CORPUS</span><h2>{report.benchmark.label}</h2><dl className="analyze-context-list"><div><dt>{t('common.domain')}</dt><dd>{report.benchmark.domain}</dd></div><div><dt>n</dt><dd>{number(report.benchmark.n,{maximumFractionDigits:0})}</dd></div><div><dt>{t('analyze.collectionRange')}</dt><dd>{date(report.benchmark.collection_start)} – {date(report.benchmark.collection_end)}</dd></div><div><dt>{t('analyze.sampling')}</dt><dd>{report.benchmark.sampling}</dd></div></dl></article>
      <article className="panel"><span className="eyebrow">REPORT PROVENANCE</span><h2>{t('analyze.provenance')}</h2><dl className="analyze-context-list"><div><dt>{t('analyze.generated')}</dt><dd>{date(report.generated_at)}</dd></div><div><dt>{t('analyze.pipeline')}</dt><dd>{report.pipeline.version}</dd></div><div><dt>{t('analyze.exportCommit')}</dt><dd><code>{report.pipeline.git_commit.slice(0,10)}</code></dd></div><div><dt>{t('analyze.measurementCommit')}</dt><dd><code>{report.pipeline.measurement_git_commit?.slice(0,10)??'—'}</code></dd></div><div><dt>Schema</dt><dd><code>{report.pipeline.feature_schema}</code></dd></div></dl></article>
    </section>

    <section className="two-col analyze-two-col"><article className="panel"><span className="eyebrow">PCA POSITION</span><h2>{t('analyze.pcaTitle')}</h2><AnalyzePcaCard pca={report.pca} neighbors={report.neighbors} title={report.video.title}/></article><article className="panel analyze-centroid"><span className="eyebrow">GROUP CONTEXT</span><h2>{t('analyze.centroidTitle')}</h2><strong>{centroidText}</strong><p>{t('analyze.coverage',{value:number(report.centroids.coverage*100,{maximumFractionDigits:0})})}</p><div><span>TOP d={report.centroids.top_distance?.toFixed(3)??'–'}</span><span>BOTTOM d={report.centroids.bottom_distance?.toFixed(3)??'–'}</span></div><small>{t('analyze.centroidNote')}</small></article></section>
    <section className="panel"><div className="section-head"><div><span className="eyebrow">REFERENCE PROFILE</span><h2>{t('analyze.featuresTitle')}</h2><p>{t('analyze.featuresDesc')}</p></div><span className="status-pill analyze-neutral-pill">{t('analyze.referenceOnly')}</span></div><AnalyzeFeatureProfile features={report.features}/></section>
    <section className="panel"><div className="section-head"><div><span className="eyebrow">NEAREST REFERENCES</span><h2>{t('analyze.neighborsTitle')}</h2><p>{t('analyze.neighborsDesc')}</p></div></div><AnalyzeNeighbors neighbors={report.neighbors}/></section>
    <section className="panel analyze-fingerprints"><p>{t('analyze.provenanceNote')}</p>{report.pipeline.measurement_status==='unverified'&&<p>{t('analyze.measurementUnverified')}</p>}<dl><dt>{t('analyze.sourceFingerprint')}</dt><dd><code>{report.pipeline.source_features_sha256}</code></dd><dt>{t('analyze.corpusFingerprint')}</dt><dd><code>{report.benchmark.corpus_sha256}</code></dd></dl></section>
    <p className="analyze-session-note">{t('analyze.sessionNote')}</p>
  </div>
}
