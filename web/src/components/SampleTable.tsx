import type { VideoRow } from '../data/schema'
import { useLocale } from '../i18n/LocaleProvider'
import { domainLabel } from '../i18n/research'

export function SampleTable({videos}:{videos:VideoRow[]}){
  const {t,number,date}=useLocale()
  const format=(value:number|null|undefined,digits=2)=>value==null||!Number.isFinite(value)?'–':number(value,{maximumFractionDigits:digits})
  return <div className="sample-table-wrap"><table className="sample-table"><thead><tr><th>{t('samples.tableGroup')}</th><th>{t('samples.tableVideo')}</th><th>{t('samples.tableDomain')}</th><th>{t('samples.tableRatio')}</th><th>{t('samples.tableViews')}</th><th>{t('samples.tableUpload')}</th></tr></thead><tbody>{videos.map(v=><tr key={v.video_id}><td><span className={`group-tag ${v.group}`}>{v.group==='top'?'TOP':'BOTTOM'}</span></td><td><a href={`https://www.youtube.com/watch?v=${v.video_id}`} target="_blank" rel="noreferrer"><b>{v.title}</b><small>{v.channel}</small></a></td><td>{domainLabel(v.domain)}</td><td>{format(v.view_per_sub,3)}</td><td>{format(v.view_count,0)}</td><td>{date(v.upload_date)}</td></tr>)}</tbody></table></div>
}
