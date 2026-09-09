import type { AnalyzeFeature } from '../data/analyzeReport'
import { useLocale } from '../i18n/LocaleProvider'

const categoryOrder=['editing','hook','visual','audio','lyrics','packaging','synchronization','metadata'] as const

export function AnalyzeFeatureProfile({features}:{features:AnalyzeFeature[]}){
  const {locale,t,number}=useLocale()
  const groups=categoryOrder.map(category=>({category,items:features.filter(item=>item.category===category)})).filter(group=>group.items.length)
  if(!groups.length)return <div className="empty-state">{t('analyze.noFeatures')}</div>
  return <div className="analyze-feature-groups">{groups.map(group=><section className="analyze-feature-group" key={group.category}>
    <div className="analyze-group-title"><span className="eyebrow">{t(`analyze.category.${group.category}` as Parameters<typeof t>[0])}</span><b>{group.items.length}</b></div>
    <div className="analyze-feature-list">{group.items.map(item=>{
      const z=`${item.z>=0?'+':''}${item.z.toFixed(2)}`
      return <article className="analyze-feature-row" key={item.id}>
        <div><b>{item.labels[locale]}</b><code>{item.id}</code></div>
        <dl>
          <div><dt>{t('analyze.raw')}</dt><dd>{number(item.value,{maximumFractionDigits:3})}</dd></div>
          <div><dt>z</dt><dd>{z}</dd></div>
          <div><dt>{t('analyze.percentile')}</dt><dd>{number(item.percentile,{maximumFractionDigits:1})}</dd></div>
          <div><dt>{t('analyze.referenceMedian')}</dt><dd>{number(item.reference_median,{maximumFractionDigits:3})}</dd></div>
          <div><dt>n</dt><dd>{number(item.reference_n,{maximumFractionDigits:0})}</dd></div>
        </dl>
      </article>
    })}</div>
  </section>)}</div>
}
