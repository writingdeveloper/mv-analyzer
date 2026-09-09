import type { ExperimentsData,ManifestData,MethodologyData } from '../data/schema'
import { DataFreshness } from '../components/DataFreshness'
import { StatusBadge } from '../components/StatusBadge'
import { useLocale } from '../i18n/LocaleProvider'
import type { MessageKey } from '../i18n/messages'

export function MethodologyPage({methodology,experiments,manifest}:{methodology:MethodologyData;experiments:ExperimentsData;manifest:ManifestData}){
  const {locale,t,number}=useLocale()
  const rel=methodology.reliability_baseline
  const rho=rel?.num_characters.spearman_rho
  const caveatMessages: Record<string, MessageKey> = {
    extreme_group_effect_inflation: 'method.caveatExtreme',
    channel_production_confounding: 'method.caveatInvestment',
    kpop_expansion_shortfall: 'method.caveatKpop',
  } as const
  const legacyCaveatIds = ['extreme_group_effect_inflation','channel_production_confounding','kpop_expansion_shortfall'] as const
  const caveats=locale==='ko'?methodology.caveats:methodology.caveats.map((c,index)=>{
    const id=methodology.caveat_ids?.[index] ?? legacyCaveatIds[index]
    return id&&caveatMessages[id]?t(caveatMessages[id]):c
  })
  const experimentNote=locale==='ko'?experiments.note:t('method.validationNote')
  return <div className="page methodology-page">
    <header className="page-title"><span className="kicker">HOW THIS WAS MEASURED</span><h1>{t('method.hero1')}<br/><em>{t('method.hero2')}</em></h1><p>{t('method.sampling')}. {t('method.heroDesc',{window:methodology.study.window})}</p></header>
    <DataFreshness manifest={manifest}/>
    {methodology.reference_corpus&&<section className="panel reference-corpus-card"><div><span className="eyebrow">REFERENCE CORPUS</span><h2>{methodology.reference_corpus.label}</h2><p>{locale==='ko'?'시장 전체 표본이 아니라 조회수/구독자수 비율의 상·하위 극단을 비교하는 버전 고정 연구 reference입니다.':'A versioned extreme-group research reference, not a representative sample of the overall MV market.'}</p></div><div className="mini-metrics"><span><b>{methodology.reference_corpus.n}</b> MVs</span><span><b>{methodology.reference_corpus.sampling}</b> sampling</span><span><b>{methodology.reference_corpus.domains.join(' + ')}</b></span><span><b>{methodology.reference_corpus.collected_at}</b></span></div></section>}
    <section className="method-grid">
      <article className="panel"><span className="eyebrow">FEATURE POLICY</span><h2>{t('method.policyTitle')}</h2><div className="policy-row"><StatusBadge kind="formal"/><b>{methodology.feature_policy.formal_count}</b><span>{t('method.formalUse')}</span></div><div className="policy-row"><StatusBadge kind="experimental"/><b>{methodology.feature_policy.experimental_count}</b><span>{t('method.experimentalUse')}</span></div></article>
      <article className="panel"><span className="eyebrow">VLM RELIABILITY</span><h2>{t('method.blindBaseline',{count:rel?.n??0})}</h2>{rel?<><div className="reliability-big">ρ {rho==null?'–':number(rho,{minimumFractionDigits:3,maximumFractionDigits:3})}</div><p>{t('method.characterAccuracy',{exact:(rel.num_characters.exact*100).toFixed(1),within:(rel.num_characters.within1*100).toFixed(1)})}</p><div className="mini-metrics">{Object.entries(rel.categorical).map(([k,v])=><span key={k}><b>{k}</b> κ {v.kappa.toFixed(3)}</span>)}</div></>:<p>{t('method.noBaseline')}</p>}</article>
    </section>
    <section className="panel"><span className="eyebrow">PIPELINE</span><h2>Local-first measurement stack</h2><div className="pipeline-row">{methodology.pipeline.map((p,i)=><span key={p}>{i>0&&<i>→</i>}<b>{p}</b></span>)}</div><p className="muted">{t('method.pipelineDesc')}</p></section>
    <section className="panel"><span className="eyebrow">VALIDATION QUEUE</span><h2>{t('method.validationTitle')}</h2><div className="experiment-list">{experiments.items.map(item=><article key={item.id}><StatusBadge kind="pending"/><div><b>{item.label}</b><code>{item.id}</code></div><span>{t('method.validationDecision')}</span></article>)}</div><p className="muted">{experimentNote}</p></section>
    <section className="panel caveats"><span className="eyebrow">LIMITS & CONFOUNDS</span><h2>{t('method.limitsTitle')}</h2><ol>{caveats.map(c=><li key={c}>{c}</li>)}</ol></section>
    <section className="snapshot-card"><div><span className="eyebrow">REPRODUCIBILITY</span><h2>{manifest.snapshot_id}</h2></div><div><span>Git commit</span><code>{manifest.git_commit.slice(0,10)}</code></div><div><span>Source</span><code>{manifest.source}</code></div></section>
  </div>
}
